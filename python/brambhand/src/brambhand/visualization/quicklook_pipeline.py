"""Headless quicklook pipeline for replay-derived 2D/3D trajectory outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from brambhand.scenario.replay_log import ReplayLog
from brambhand.visualization.quicklook_contracts import (
    QUICKLOOK_STYLE_SCHEMA_VERSION,
    QuicklookEvent,
    QuicklookSeverity,
    QuicklookTelemetryContract,
    extract_quicklook_telemetry,
    severity_to_color_hex,
)
from brambhand.visualization.trajectory_overlay import (
    CurrentPlannedOverlaySample,
    build_current_planned_overlay,
)


@dataclass(frozen=True)
class Quicklook2DPoint:
    """2D quicklook trajectory sample (x-y plane)."""

    sim_time_s: float
    x_m: float
    y_m: float


@dataclass(frozen=True)
class Quicklook3DPoint:
    """3D quicklook trajectory sample."""

    sim_time_s: float
    x_m: float
    y_m: float
    z_m: float


@dataclass(frozen=True)
class QuicklookEventMarker:
    """Deterministic quicklook event marker with optional trajectory anchor."""

    sequence: int
    sim_time_s: float
    kind: str
    severity: QuicklookSeverity
    color_hex: str
    x_m: float | None
    y_m: float | None
    z_m: float | None


@dataclass(frozen=True)
class HeadlessQuicklookOutput:
    """Headless quicklook artifacts derived from replay telemetry."""

    telemetry: QuicklookTelemetryContract
    style_schema_version: int
    trajectory_2d: tuple[Quicklook2DPoint, ...]
    trajectory_3d: tuple[Quicklook3DPoint, ...]
    planned_trajectory_2d: tuple[Quicklook2DPoint, ...]
    planned_trajectory_3d: tuple[Quicklook3DPoint, ...]
    current_planned_overlay: tuple[CurrentPlannedOverlaySample, ...]
    event_markers: tuple[QuicklookEventMarker, ...]


def _build_event_markers(
    events: tuple[QuicklookEvent, ...],
    telemetry: QuicklookTelemetryContract,
) -> tuple[QuicklookEventMarker, ...]:
    trajectory_iter = iter(telemetry.trajectory)
    next_sample = next(trajectory_iter, None)
    latest_position: tuple[float, float, float] | None = None
    markers: list[QuicklookEventMarker] = []

    for event in events:
        while next_sample is not None and next_sample.sequence <= event.sequence:
            latest_position = next_sample.position_m
            next_sample = next(trajectory_iter, None)

        markers.append(
            QuicklookEventMarker(
                sequence=event.sequence,
                sim_time_s=event.sim_time_s,
                kind=event.kind,
                severity=event.severity,
                color_hex=severity_to_color_hex(event.severity),
                x_m=None if latest_position is None else latest_position[0],
                y_m=None if latest_position is None else latest_position[1],
                z_m=None if latest_position is None else latest_position[2],
            )
        )

    return tuple(markers)


def build_headless_quicklook_output(replay_log: ReplayLog) -> HeadlessQuicklookOutput:
    """Build deterministic 2D/3D quicklook trajectories from replay records."""
    telemetry = extract_quicklook_telemetry(replay_log)
    trajectory_2d = tuple(
        Quicklook2DPoint(
            sim_time_s=sample.sim_time_s,
            x_m=sample.position_m[0],
            y_m=sample.position_m[1],
        )
        for sample in telemetry.trajectory
    )
    trajectory_3d = tuple(
        Quicklook3DPoint(
            sim_time_s=sample.sim_time_s,
            x_m=sample.position_m[0],
            y_m=sample.position_m[1],
            z_m=sample.position_m[2],
        )
        for sample in telemetry.trajectory
    )
    planned_trajectory_2d = tuple(
        Quicklook2DPoint(
            sim_time_s=sample.sim_time_s,
            x_m=sample.position_m[0],
            y_m=sample.position_m[1],
        )
        for sample in telemetry.planned_trajectory
    )
    planned_trajectory_3d = tuple(
        Quicklook3DPoint(
            sim_time_s=sample.sim_time_s,
            x_m=sample.position_m[0],
            y_m=sample.position_m[1],
            z_m=sample.position_m[2],
        )
        for sample in telemetry.planned_trajectory
    )
    return HeadlessQuicklookOutput(
        telemetry=telemetry,
        style_schema_version=QUICKLOOK_STYLE_SCHEMA_VERSION,
        trajectory_2d=trajectory_2d,
        trajectory_3d=trajectory_3d,
        planned_trajectory_2d=planned_trajectory_2d,
        planned_trajectory_3d=planned_trajectory_3d,
        current_planned_overlay=build_current_planned_overlay(
            telemetry.trajectory,
            telemetry.planned_trajectory,
        ),
        event_markers=_build_event_markers(telemetry.events, telemetry),
    )


def load_headless_quicklook_output(path: str | Path) -> HeadlessQuicklookOutput:
    """Load replay JSONL and build headless quicklook trajectories."""
    return build_headless_quicklook_output(ReplayLog.load_jsonl(path))
