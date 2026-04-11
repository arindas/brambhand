"""Headless quicklook pipeline for replay-derived 2D/3D trajectory outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from brambhand.scenario.replay_log import ReplayLog
from brambhand.visualization.quicklook_contracts import (
    QuicklookTelemetryContract,
    extract_quicklook_telemetry,
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
class HeadlessQuicklookOutput:
    """Headless quicklook artifacts derived from replay telemetry."""

    telemetry: QuicklookTelemetryContract
    trajectory_2d: tuple[Quicklook2DPoint, ...]
    trajectory_3d: tuple[Quicklook3DPoint, ...]


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
    return HeadlessQuicklookOutput(
        telemetry=telemetry,
        trajectory_2d=trajectory_2d,
        trajectory_3d=trajectory_3d,
    )


def load_headless_quicklook_output(path: str | Path) -> HeadlessQuicklookOutput:
    """Load replay JSONL and build headless quicklook trajectories."""
    return build_headless_quicklook_output(ReplayLog.load_jsonl(path))
