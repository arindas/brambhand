"""Shared fluid-domain contracts consumed by propulsion and FSI.

Why this module exists:
- Define backend-neutral boundary/load payloads so reduced-order and CFD providers
  can plug into the same downstream coupling interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.physics.vector import Vector3

LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION = 1


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


@dataclass(frozen=True)
class LeakJetBoundaryPayload:
    """Versioned leak-jet boundary payload consumed by FSI exchange contracts."""

    interface_id: str
    schema_version: int
    reaction_force_body_n: Vector3
    reaction_torque_body_nm: Vector3
    mass_flow_kgps: float
    jet_temperature_k: float

    def __post_init__(self) -> None:
        if not self.interface_id:
            raise ValueError("interface_id must be non-empty.")
        if self.schema_version != LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION:
            raise ValueError("Unsupported leak-jet boundary payload schema_version.")
        if self.mass_flow_kgps < 0.0:
            raise ValueError("mass_flow_kgps cannot be negative.")
        if self.jet_temperature_k <= 0.0:
            raise ValueError("jet_temperature_k must be positive.")

    def to_fluid_boundary_load(self) -> FluidBoundaryLoad:
        """Convert leak-jet payload into backend-neutral FSI boundary-load contract."""
        return FluidBoundaryLoad(
            interface_id=self.interface_id,
            force_body_n=self.reaction_force_body_n,
            torque_body_nm=self.reaction_torque_body_nm,
            mass_flow_kgps=self.mass_flow_kgps,
            temperature_k=self.jet_temperature_k,
        )
