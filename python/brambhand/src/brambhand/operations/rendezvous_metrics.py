"""Relative motion metrics used by rendezvous and docking logic.

Why this module exists:
- Centralize relative kinematic calculations to avoid duplicated formulas.
"""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.physics.body import PhysicalBody
from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class RendezvousMetrics:
    """Computed relative geometry and motion quantities."""

    relative_position_m: Vector3
    relative_velocity_mps: Vector3
    range_m: float
    closing_rate_mps: float


def compute_rendezvous_metrics(chaser: PhysicalBody, target: PhysicalBody) -> RendezvousMetrics:
    """Compute relative position/velocity, range, and scalar closing rate."""
    relative_position = chaser.state.position - target.state.position
    relative_velocity = chaser.state.velocity - target.state.velocity
    separation = relative_position.norm()

    if separation == 0.0:
        closing_rate = 0.0
    else:
        closing_rate = -(relative_position.dot(relative_velocity) / separation)

    return RendezvousMetrics(
        relative_position_m=relative_position,
        relative_velocity_mps=relative_velocity,
        range_m=separation,
        closing_rate_mps=closing_rate,
    )
