"""Shared fluid-domain contracts consumed by propulsion and FSI.

Why this module exists:
- Define backend-neutral boundary/load payloads so reduced-order and CFD providers
  can plug into the same downstream coupling interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class FluidBoundaryLoad:
    """Backend-neutral fluid-side load contribution at an interface."""

    interface_id: str
    force_body_n: Vector3
    torque_body_nm: Vector3
    mass_flow_kgps: float
    temperature_k: float

    def __post_init__(self) -> None:
        if not self.interface_id:
            raise ValueError("interface_id must be non-empty.")
        if self.mass_flow_kgps < 0.0:
            raise ValueError("mass_flow_kgps cannot be negative.")
        if self.temperature_k <= 0.0:
            raise ValueError("temperature_k must be positive.")
