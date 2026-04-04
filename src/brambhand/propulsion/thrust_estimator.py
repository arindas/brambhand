"""Nozzle thrust estimation baseline.

Why this module exists:
- Provide deterministic thrust force estimates from chamber/flow state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from brambhand.propulsion.chamber_flow import ChamberFlowState


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


@dataclass(frozen=True)
class NozzleGeometryCorrection:
    """Geometry-aware correction inputs for baseline thrust estimation.

    The correction model approximates first-order geometry effects:
    - throat/exit area ratio impact on expansion performance
    - contour losses from non-ideal nozzle shaping
    """

    throat_area_m2: float
    contour_loss_factor: float = 1.0

    def __post_init__(self) -> None:
        if self.throat_area_m2 <= 0.0:
            raise ValueError("throat_area_m2 must be positive.")
        if not 0.0 < self.contour_loss_factor <= 1.0:
            raise ValueError("contour_loss_factor must be in (0, 1].")


@dataclass(frozen=True)
class ChamberThrustCouplingParams:
    """Contract for coupling chamber-flow state into thrust estimation."""

    gas_constant_jpkgk: float
    throat_area_m2: float
    throat_discharge_coefficient: float = 1.0

    def __post_init__(self) -> None:
        if self.gas_constant_jpkgk <= 0.0:
            raise ValueError("gas_constant_jpkgk must be positive.")
        if self.throat_area_m2 <= 0.0:
            raise ValueError("throat_area_m2 must be positive.")
        if self.throat_discharge_coefficient <= 0.0:
            raise ValueError("throat_discharge_coefficient must be positive.")


def _expansion_efficiency(area_ratio: float) -> float:
    """Return bounded expansion efficiency from nozzle area ratio."""
    if area_ratio < 1.0:
        raise ValueError("Nozzle area ratio must be >= 1.0.")
    # Slow logarithmic gain with clipping for reduced-order stability.
    return min(1.15, max(0.85, 0.9 + 0.08 * math.log(area_ratio)))


def estimate_nozzle_thrust(
    chamber_pressure_pa: float,
    mass_flow_kgps: float,
    nozzle: NozzleParams,
    geometry: NozzleGeometryCorrection | None = None,
) -> ThrustEstimate:
    """Estimate thrust as momentum + pressure terms.

    When `geometry` is provided, apply reduced-order corrections for
    nozzle area-ratio expansion behavior and contour losses.
    """
    if chamber_pressure_pa < 0.0:
        raise ValueError("chamber_pressure_pa cannot be negative.")
    if mass_flow_kgps < 0.0:
        raise ValueError("mass_flow_kgps cannot be negative.")

    geometry_factor = 1.0
    if geometry is not None:
        area_ratio = nozzle.exit_area_m2 / geometry.throat_area_m2
        geometry_factor = _expansion_efficiency(area_ratio) * geometry.contour_loss_factor

    momentum = mass_flow_kgps * nozzle.exhaust_velocity_mps * geometry_factor
    pressure = (
        (chamber_pressure_pa - nozzle.ambient_pressure_pa)
        * nozzle.exit_area_m2
        * geometry_factor
    )
    total = momentum + pressure
    return ThrustEstimate(
        thrust_n=total,
        momentum_thrust_n=momentum,
        pressure_thrust_n=pressure,
    )


def estimate_nozzle_thrust_from_chamber_flow(
    chamber_state: ChamberFlowState,
    nozzle: NozzleParams,
    coupling: ChamberThrustCouplingParams,
    geometry: NozzleGeometryCorrection | None = None,
) -> ThrustEstimate:
    """Estimate nozzle thrust by deriving throat flow from chamber-flow state.

    Reduced-order throat flow proxy:
    `m_dot = Cd * A_t * p_c / sqrt(R * T)`.
    """
    if chamber_state.pressure_pa == 0.0:
        return estimate_nozzle_thrust(
            chamber_pressure_pa=0.0,
            mass_flow_kgps=0.0,
            nozzle=nozzle,
            geometry=geometry,
        )

    temperature = max(chamber_state.temperature_k, 1e-9)
    mass_flow_kgps = (
        coupling.throat_discharge_coefficient
        * coupling.throat_area_m2
        * chamber_state.pressure_pa
        / math.sqrt(coupling.gas_constant_jpkgk * temperature)
    )

    return estimate_nozzle_thrust(
        chamber_pressure_pa=chamber_state.pressure_pa,
        mass_flow_kgps=mass_flow_kgps,
        nozzle=nozzle,
        geometry=geometry,
    )
