"""Deterministic current-vs-planned trajectory overlay helpers."""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.visualization.quicklook_contracts import TrajectorySample


@dataclass(frozen=True)
class CurrentPlannedOverlaySample:
    """Aligned overlay sample pairing current and planned trajectory points."""

    sequence: int
    sim_time_s: float
    current_position_m: tuple[float, float, float]
    planned_position_m: tuple[float, float, float] | None


def build_current_planned_overlay(
    current: tuple[TrajectorySample, ...],
    planned: tuple[TrajectorySample, ...],
) -> tuple[CurrentPlannedOverlaySample, ...]:
    """Align current and planned traces by sequence for deterministic overlays."""
    planned_by_sequence = {sample.sequence: sample for sample in planned}

    return tuple(
        CurrentPlannedOverlaySample(
            sequence=sample.sequence,
            sim_time_s=sample.sim_time_s,
            current_position_m=sample.position_m,
            planned_position_m=(
                None
                if planned_by_sequence.get(sample.sequence) is None
                else planned_by_sequence[sample.sequence].position_m
            ),
        )
        for sample in current
    )
