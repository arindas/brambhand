"""Replay trajectory consistency validators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class TrajectoryDiscontinuity:
    tick: int
    step_distance_m: float
    reference_distance_m: float


def detect_uncommanded_discontinuities(
    positions: list[Vector3],
    commanded_ticks: set[int],
    jump_factor: float = 6.0,
) -> list[TrajectoryDiscontinuity]:
    if jump_factor <= 1.0:
        raise ValueError("jump_factor must be > 1.0")
    if len(positions) < 3:
        return []

    discontinuities: list[TrajectoryDiscontinuity] = []
    prev_step = (positions[1] - positions[0]).norm()

    for tick in range(2, len(positions)):
        step = (positions[tick] - positions[tick - 1]).norm()
        reference = max(prev_step, 1.0)
        if tick not in commanded_ticks and step > jump_factor * reference:
            discontinuities.append(
                TrajectoryDiscontinuity(
                    tick=tick,
                    step_distance_m=step,
                    reference_distance_m=reference,
                )
            )
        prev_step = step

    return discontinuities


def validate_replay_probe_continuity(
    frames: list[dict[str, Any]],
    probe_body_id: str = "mars_probe",
    jump_factor: float = 6.0,
) -> list[TrajectoryDiscontinuity]:
    positions: list[Vector3] = []
    commanded_ticks: set[int] = set()

    for frame in frames:
        tick = int(frame.get("tick_id", len(positions)))
        bodies_raw = frame.get("bodies", [])
        if not isinstance(bodies_raw, list):
            continue

        probe_position: Vector3 | None = None
        for body in bodies_raw:
            if not isinstance(body, dict):
                continue
            if body.get("body_id") != probe_body_id:
                continue
            position = body.get("position_m", {})
            if not isinstance(position, dict):
                continue
            probe_position = Vector3(
                float(position.get("x", 0.0)),
                float(position.get("y", 0.0)),
                float(position.get("z", 0.0)),
            )
            break

        if probe_position is None:
            continue
        positions.append(probe_position)

        records_raw = frame.get("maneuver_records", [])
        if not isinstance(records_raw, list):
            continue
        for record in records_raw:
            if not isinstance(record, dict):
                continue
            if record.get("body_id") != probe_body_id:
                continue
            if float(record.get("delta_v_applied_mps", 0.0)) > 0.0:
                commanded_ticks.add(tick)

    return detect_uncommanded_discontinuities(
        positions=positions,
        commanded_ticks=commanded_ticks,
        jump_factor=jump_factor,
    )
