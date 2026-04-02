"""Snapshot structures for exposing simulation state to users and tests.

Why this module exists:
- Normalize output shape for logging/replay/regression validation.
"""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.core.event_bus import Event
from brambhand.physics.body import PhysicalBody


@dataclass(frozen=True)
class BodySnapshot:
    """Serializable body state at one simulation timestamp."""

    name: str
    mass: float
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]


@dataclass(frozen=True)
class StateSnapshot:
    """Serializable simulation snapshot with body states and related events."""

    sim_time_s: float
    bodies: tuple[BodySnapshot, ...]
    events: tuple[Event, ...]


def build_state_snapshot(
    sim_time_s: float,
    bodies: list[PhysicalBody],
    events: list[Event],
) -> StateSnapshot:
    """Build stable snapshot; body ordering is name-sorted for determinism."""
    sorted_bodies = sorted(bodies, key=lambda b: b.name)
    body_snapshots = tuple(
        BodySnapshot(
            name=body.name,
            mass=body.mass,
            position_m=(
                body.state.position.x,
                body.state.position.y,
                body.state.position.z,
            ),
            velocity_mps=(
                body.state.velocity.x,
                body.state.velocity.y,
                body.state.velocity.z,
            ),
        )
        for body in sorted_bodies
    )
    return StateSnapshot(sim_time_s=sim_time_s, bodies=body_snapshots, events=tuple(events))
