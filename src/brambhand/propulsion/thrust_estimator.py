"""Nozzle thrust estimation baseline.

Why this module exists:
- Provide deterministic thrust force estimates from chamber/flow state.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NozzleParams:
    """Nozzle/ambient parameters for static thrust estimate."""

    exit_area_m2: float
    ambient_pressure_pa: float
    exhaust_velocity_mps: float

    def __post_init__(self) -> None:
        if self.exit_area_m2 <= 0.0:
            raise ValueError("exit_area_m2 must be positive.")
        if self.ambient_pressure_pa < 0.0:
            raise ValueError("ambient_pressure_pa cannot be negative.")
        if self.exhaust_velocity_mps <= 0.0:
            raise ValueError("exhaust_velocity_mps must be positive.")


@dataclass(frozen=True)
class ThrustEstimate:
    """Static thrust decomposition outputs."""

    thrust_n: float
    momentum_thrust_n: float
    pressure_thrust_n: float


def estimate_nozzle_thrust(
    chamber_pressure_pa: float,
    mass_flow_kgps: float,
    nozzle: NozzleParams,
) -> ThrustEstimate:
    """Estimate thrust as momentum + pressure terms."""
    if chamber_pressure_pa < 0.0:
        raise ValueError("chamber_pressure_pa cannot be negative.")
    if mass_flow_kgps < 0.0:
        raise ValueError("mass_flow_kgps cannot be negative.")

    momentum = mass_flow_kgps * nozzle.exhaust_velocity_mps
    pressure = (chamber_pressure_pa - nozzle.ambient_pressure_pa) * nozzle.exit_area_m2
    total = momentum + pressure
    return ThrustEstimate(thrust_n=total, momentum_thrust_n=momentum, pressure_thrust_n=pressure)
