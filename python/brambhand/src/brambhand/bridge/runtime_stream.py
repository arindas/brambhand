"""Live runtime-stream frame shaping with replay-parity body-id lifecycle metadata."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

RUNTIME_STREAM_SCHEMA_VERSION = 1
BODY_ID_CATALOG_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class BodyIdCatalogDelta:
    """Body lifecycle metadata emitted per stream frame."""

    schema_version: int
    created_body_ids: tuple[str, ...]
    destroyed_body_ids: tuple[str, ...]
    initial_body_ids: tuple[str, ...] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "created_body_ids": list(self.created_body_ids),
            "destroyed_body_ids": list(self.destroyed_body_ids),
        }
        if self.initial_body_ids is not None:
            payload["initial_body_ids"] = list(self.initial_body_ids)
        return payload


class RuntimeStreamPublisher:
    """Build stream payloads with canonical `body_id_catalog` parity."""

    def __init__(
        self,
        *,
        stream_schema_version: int = RUNTIME_STREAM_SCHEMA_VERSION,
        body_catalog_schema_version: int = BODY_ID_CATALOG_SCHEMA_VERSION,
    ) -> None:
        self._stream_schema_version = stream_schema_version
        self._body_catalog_schema_version = body_catalog_schema_version

    def publish_frames(
        self,
        frames: Iterable[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        emitted: list[dict[str, Any]] = []
        active_body_ids: set[str] | None = None

        for index, frame in enumerate(frames):
            body_catalog_payload = frame.get("body_id_catalog")
            if isinstance(body_catalog_payload, Mapping):
                catalog = self._validated_catalog(
                    body_catalog_payload,
                    is_first_frame=(index == 0),
                )
            else:
                current_body_ids = self._extract_body_ids(frame)
                catalog = self._derived_catalog(
                    active_body_ids=active_body_ids,
                    current_body_ids=current_body_ids,
                )

            active_body_ids = self._apply_catalog(
                active_body_ids=active_body_ids,
                catalog=catalog,
            )

            emitted.append(
                {
                    "schema_version": self._stream_schema_version,
                    "run_id": frame["run_id"],
                    "tick_id": frame["tick_id"],
                    "sim_time_s": frame["sim_time_s"],
                    "sequence": frame["sequence"],
                    "bodies": list(frame.get("bodies", [])),
                    "events": list(frame.get("events", [])),
                    "topology": frame.get("topology"),
                    "body_id_catalog": catalog.to_payload(),
                }
            )

        return emitted

    def _derived_catalog(
        self,
        *,
        active_body_ids: set[str] | None,
        current_body_ids: set[str],
    ) -> BodyIdCatalogDelta:
        if active_body_ids is None:
            return BodyIdCatalogDelta(
                schema_version=self._body_catalog_schema_version,
                initial_body_ids=tuple(sorted(current_body_ids)),
                created_body_ids=(),
                destroyed_body_ids=(),
            )

        created = tuple(sorted(current_body_ids.difference(active_body_ids)))
        destroyed = tuple(sorted(active_body_ids.difference(current_body_ids)))
        return BodyIdCatalogDelta(
            schema_version=self._body_catalog_schema_version,
            initial_body_ids=None,
            created_body_ids=created,
            destroyed_body_ids=destroyed,
        )

    def _validated_catalog(
        self,
        payload: Mapping[str, Any],
        *,
        is_first_frame: bool,
    ) -> BodyIdCatalogDelta:
        schema_version = int(payload.get("schema_version", self._body_catalog_schema_version))
        if schema_version != self._body_catalog_schema_version:
            raise ValueError(
                f"Unsupported body_id_catalog schema_version={schema_version}"
            )

        initial_raw = payload.get("initial_body_ids")
        if is_first_frame and initial_raw is None:
            raise ValueError("body_id_catalog.initial_body_ids must be present on first frame")
        if (not is_first_frame) and initial_raw is not None:
            raise ValueError("body_id_catalog.initial_body_ids is only allowed on first frame")

        created_raw = payload.get("created_body_ids", ())
        destroyed_raw = payload.get("destroyed_body_ids", ())

        initial = None if initial_raw is None else tuple(sorted(str(v) for v in initial_raw))
        created = tuple(sorted(str(v) for v in created_raw))
        destroyed = tuple(sorted(str(v) for v in destroyed_raw))

        return BodyIdCatalogDelta(
            schema_version=schema_version,
            initial_body_ids=initial,
            created_body_ids=created,
            destroyed_body_ids=destroyed,
        )

    @staticmethod
    def _extract_body_ids(frame: Mapping[str, Any]) -> set[str]:
        body_ids: set[str] = set()
        for body in frame.get("bodies", []):
            if isinstance(body, Mapping) and "body_id" in body:
                body_ids.add(str(body["body_id"]))
        return body_ids

    @staticmethod
    def _apply_catalog(
        *,
        active_body_ids: set[str] | None,
        catalog: BodyIdCatalogDelta,
    ) -> set[str]:
        if active_body_ids is None:
            return set(catalog.initial_body_ids or ())

        updated = set(active_body_ids)
        updated.update(catalog.created_body_ids)
        for body_id in catalog.destroyed_body_ids:
            updated.discard(body_id)
        return updated
