"""R8.0 quicklook telemetry contract and replay extraction baseline."""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.scenario.replay_log import ReplayLog

QUICKLOOK_TELEMETRY_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TrajectorySample:
    """Minimal trajectory sample extracted from replay records."""

    sequence: int
    sim_time_s: float
    position_m: tuple[float, float, float]


@dataclass(frozen=True)
class QuicklookEvent:
    """Minimal event marker extracted from replay timeline."""

    sequence: int
    sim_time_s: float
    kind: str


@dataclass(frozen=True)
class QuicklookTelemetryContract:
    """Versioned minimal quicklook telemetry contract."""

    schema_version: int
    trajectory: tuple[TrajectorySample, ...]
    events: tuple[QuicklookEvent, ...]

    def __post_init__(self) -> None:
        if self.schema_version != QUICKLOOK_TELEMETRY_SCHEMA_VERSION:
            raise ValueError("Unsupported quicklook telemetry schema_version.")


def _position_tuple_from_payload(payload: dict[str, object]) -> tuple[float, float, float] | None:
    raw = payload.get("position_m")
    if isinstance(raw, dict):
        try:
            return (float(raw["x"]), float(raw["y"]), float(raw["z"]))
        except (KeyError, TypeError, ValueError):
            return None
    if isinstance(raw, (list, tuple)) and len(raw) == 3:
        try:
            return (float(raw[0]), float(raw[1]), float(raw[2]))
        except (TypeError, ValueError):
            return None
    return None


def extract_quicklook_telemetry(replay_log: ReplayLog) -> QuicklookTelemetryContract:
    """Extract minimal trajectory/event quicklook contract from replay log."""
    trajectory: list[TrajectorySample] = []
    events: list[QuicklookEvent] = []

    for record in replay_log.records:
        events.append(
            QuicklookEvent(
                sequence=record.sequence,
                sim_time_s=record.sim_time_s,
                kind=record.kind,
            )
        )
        position = _position_tuple_from_payload(record.payload)
        if position is None:
            continue
        trajectory.append(
            TrajectorySample(
                sequence=record.sequence,
                sim_time_s=record.sim_time_s,
                position_m=position,
            )
        )

    trajectory.sort(key=lambda sample: sample.sequence)
    events.sort(key=lambda marker: marker.sequence)

    return QuicklookTelemetryContract(
        schema_version=QUICKLOOK_TELEMETRY_SCHEMA_VERSION,
        trajectory=tuple(trajectory),
        events=tuple(events),
    )
