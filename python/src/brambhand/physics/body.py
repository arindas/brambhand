"""Basic inertial body state primitives.

Why this module exists:
- Shared canonical state container across physics, guidance, and operations modules.
"""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class InertialState:
    """Translational position/velocity in inertial frame."""

    position: Vector3
    velocity: Vector3


@dataclass(frozen=True)
class PhysicalBody:
    """Point-mass body represented by name, mass, and inertial state."""

    name: str
    mass: float
    state: InertialState

    def __post_init__(self) -> None:
        if self.mass <= 0.0:
            raise ValueError("Body mass must be positive.")
