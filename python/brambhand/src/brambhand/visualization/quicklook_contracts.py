"""R8.0 quicklook telemetry contract and replay extraction baseline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from brambhand.scenario.replay_log import ReplayLog

QUICKLOOK_TELEMETRY_SCHEMA_VERSION = 1
QUICKLOOK_SEVERITY_SCHEMA_VERSION = 1
QUICKLOOK_STYLE_SCHEMA_VERSION = 1
QuicklookSeverity = Literal["info", "warning", "critical"]

QUICKLOOK_EVENT_SEVERITY_MAP: Final[dict[str, QuicklookSeverity]] = {
    "simulation_started": "info",
    "step_started": "info",
    "step_completed": "info",
    "step": "info",
    "status": "info",
    "warning": "warning",
    "alarm": "warning",
    "error": "critical",
    "fault": "critical",
    "abort": "critical",
}

QUICKLOOK_SEVERITY_COLOR_MAP: Final[dict[QuicklookSeverity, str]] = {
    "info": "#4DA3FF",
    "warning": "#FFB020",
    "critical": "#FF4D4F",
}


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
    severity: QuicklookSeverity


@dataclass(frozen=True)
class QuicklookTelemetryContract:
    """Versioned minimal quicklook telemetry contract."""

    schema_version: int
    severity_schema_version: int
    trajectory: tuple[TrajectorySample, ...]
    planned_trajectory: tuple[TrajectorySample, ...]
    events: tuple[QuicklookEvent, ...]

    def __post_init__(self) -> None:
        if self.schema_version != QUICKLOOK_TELEMETRY_SCHEMA_VERSION:
            raise ValueError("Unsupported quicklook telemetry schema_version.")
        if self.severity_schema_version != QUICKLOOK_SEVERITY_SCHEMA_VERSION:
            raise ValueError("Unsupported quicklook severity_schema_version.")


def _position_tuple_from_payload(
    payload: dict[str, object],
    key: str = "position_m",
) -> tuple[float, float, float] | None:
    raw = payload.get(key)
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


def event_kind_to_severity(kind: str) -> QuicklookSeverity:
    """Map replay event kind to deterministic quicklook severity tier."""
    return QUICKLOOK_EVENT_SEVERITY_MAP.get(kind, "info")


def severity_to_color_hex(severity: QuicklookSeverity) -> str:
    """Map quicklook severity to baseline deterministic marker color."""
    return QUICKLOOK_SEVERITY_COLOR_MAP[severity]


def extract_quicklook_telemetry(replay_log: ReplayLog) -> QuicklookTelemetryContract:
    """Extract minimal trajectory/event quicklook contract from replay log."""
    trajectory: list[TrajectorySample] = []
    planned_trajectory: list[TrajectorySample] = []
    events: list[QuicklookEvent] = []

    for record in replay_log.records:
        events.append(
            QuicklookEvent(
                sequence=record.sequence,
                sim_time_s=record.sim_time_s,
                kind=record.kind,
                severity=event_kind_to_severity(record.kind),
            )
        )
        position = _position_tuple_from_payload(record.payload)
        if position is not None:
            trajectory.append(
                TrajectorySample(
                    sequence=record.sequence,
                    sim_time_s=record.sim_time_s,
                    position_m=position,
                )
            )

        planned_position = _position_tuple_from_payload(record.payload, key="planned_position_m")
        if planned_position is not None:
            planned_trajectory.append(
                TrajectorySample(
                    sequence=record.sequence,
                    sim_time_s=record.sim_time_s,
                    position_m=planned_position,
                )
            )

    trajectory.sort(key=lambda sample: sample.sequence)
    planned_trajectory.sort(key=lambda sample: sample.sequence)
    events.sort(key=lambda marker: marker.sequence)

    return QuicklookTelemetryContract(
        schema_version=QUICKLOOK_TELEMETRY_SCHEMA_VERSION,
        severity_schema_version=QUICKLOOK_SEVERITY_SCHEMA_VERSION,
        trajectory=tuple(trajectory),
        planned_trajectory=tuple(planned_trajectory),
        events=tuple(events),
    )
