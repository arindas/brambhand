"""Reduced-order propellant slosh contracts (baseline scaffolding)."""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class SloshLoad:
    """Equivalent slosh load contribution in body frame."""

    force_body_n: Vector3
    torque_body_nm: Vector3
    com_offset_body_m: Vector3
