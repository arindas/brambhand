"""Reduced-order injector-to-throat chamber-flow baseline.

Why this module exists:
- Add a deterministic internal chamber-flow state model between feed delivery and
  thrust estimation.
- Expose pressure/temperature/mixing diagnostics needed for R2.2 coupling and V&V.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ChamberFlowParams:
    """Configuration for reduced-order chamber-flow dynamics."""

    volume_m3: float
    gas_constant_jpkgk: float
    stoichiometric_of_ratio: float
    min_temperature_k: float
    max_temperature_k: float
    thermal_relaxation_time_constant_s: float

    def __post_init__(self) -> None:
        if self.volume_m3 <= 0.0:
            raise ValueError("volume_m3 must be positive.")
        if self.gas_constant_jpkgk <= 0.0:
            raise ValueError("gas_constant_jpkgk must be positive.")
        if self.stoichiometric_of_ratio <= 0.0:
            raise ValueError("stoichiometric_of_ratio must be positive.")
        if self.min_temperature_k <= 0.0:
            raise ValueError("min_temperature_k must be positive.")
        if self.max_temperature_k < self.min_temperature_k:
            raise ValueError("max_temperature_k must be >= min_temperature_k.")
        if self.thermal_relaxation_time_constant_s <= 0.0:
            raise ValueError("thermal_relaxation_time_constant_s must be positive.")


@dataclass(frozen=True)
class ChamberFlowState:
    """Internal chamber-flow state."""

    gas_mass_kg: float
    pressure_pa: float
    temperature_k: float
    fuel_mass_fraction: float

    def __post_init__(self) -> None:
        if self.gas_mass_kg < 0.0:
            raise ValueError("gas_mass_kg cannot be negative.")
        if self.pressure_pa < 0.0:
            raise ValueError("pressure_pa cannot be negative.")
        if self.temperature_k <= 0.0:
            raise ValueError("temperature_k must be positive.")
        if not 0.0 <= self.fuel_mass_fraction <= 1.0:
            raise ValueError("fuel_mass_fraction must be in [0, 1].")


@dataclass(frozen=True)
class ChamberFlowDiagnostics:
    """Per-step diagnostic proxies for chamber internal behavior."""

    injector_mass_flow_kgps: float
    throat_mass_flow_kgps: float
    chamber_pressure_pa: float
    chamber_temperature_k: float
    chamber_of_ratio: float
    stoichiometric_error: float
    mixing_quality: float


@dataclass(frozen=True)
class ChamberFlowStepResult:
    """Result bundle for one chamber-flow update."""

    state: ChamberFlowState
    diagnostics: ChamberFlowDiagnostics


def _mixing_quality_from_fuel_fraction(
    fuel_mass_fraction: float,
    stoich_fuel_mass_fraction: float,
) -> tuple[float, float]:
    """Return `(stoich_error, quality)` from current composition."""
    denom = max(stoich_fuel_mass_fraction, 1.0 - stoich_fuel_mass_fraction, 1e-12)
    stoich_error = abs(fuel_mass_fraction - stoich_fuel_mass_fraction) / denom
    quality = max(0.0, 1.0 - stoich_error)
    return stoich_error, quality


def step_chamber_flow(
    state: ChamberFlowState,
    params: ChamberFlowParams,
    inflow_fuel_kgps: float,
    inflow_oxidizer_kgps: float,
    throat_outflow_kgps: float,
    dt_s: float,
) -> ChamberFlowStepResult:
    """Advance chamber internal state with reduced-order mass/composition dynamics."""
    if dt_s <= 0.0:
        raise ValueError("dt_s must be positive.")
    if inflow_fuel_kgps < 0.0 or inflow_oxidizer_kgps < 0.0 or throat_outflow_kgps < 0.0:
        raise ValueError(
            "inflow_fuel_kgps, inflow_oxidizer_kgps, and "
            "throat_outflow_kgps must be non-negative."
        )

    injector_mass_flow = inflow_fuel_kgps + inflow_oxidizer_kgps

    next_mass = max(0.0, state.gas_mass_kg + (injector_mass_flow - throat_outflow_kgps) * dt_s)

    prev_fuel_mass = state.gas_mass_kg * state.fuel_mass_fraction
    outflow_fuel_mass = throat_outflow_kgps * dt_s * state.fuel_mass_fraction
    next_fuel_mass = max(0.0, prev_fuel_mass + inflow_fuel_kgps * dt_s - outflow_fuel_mass)
    next_fuel_mass = min(next_fuel_mass, next_mass)
    next_fuel_mass_fraction = 0.0 if next_mass == 0.0 else next_fuel_mass / next_mass

    stoich_fuel_mass_fraction = 1.0 / (1.0 + params.stoichiometric_of_ratio)
    stoich_error, mixing_quality = _mixing_quality_from_fuel_fraction(
        fuel_mass_fraction=next_fuel_mass_fraction,
        stoich_fuel_mass_fraction=stoich_fuel_mass_fraction,
    )

    target_temperature = params.min_temperature_k + (
        params.max_temperature_k - params.min_temperature_k
    ) * mixing_quality
    alpha = 1.0 - math.exp(-dt_s / params.thermal_relaxation_time_constant_s)
    next_temperature = state.temperature_k + (target_temperature - state.temperature_k) * alpha

    next_pressure = (
        next_mass * params.gas_constant_jpkgk * next_temperature / params.volume_m3
        if next_mass > 0.0
        else 0.0
    )

    if next_fuel_mass_fraction == 0.0:
        chamber_of_ratio = math.inf
    else:
        chamber_of_ratio = (1.0 - next_fuel_mass_fraction) / next_fuel_mass_fraction

    next_state = ChamberFlowState(
        gas_mass_kg=next_mass,
        pressure_pa=next_pressure,
        temperature_k=next_temperature,
        fuel_mass_fraction=next_fuel_mass_fraction,
    )
    diagnostics = ChamberFlowDiagnostics(
        injector_mass_flow_kgps=injector_mass_flow,
        throat_mass_flow_kgps=throat_outflow_kgps,
        chamber_pressure_pa=next_pressure,
        chamber_temperature_k=next_temperature,
        chamber_of_ratio=chamber_of_ratio,
        stoichiometric_error=stoich_error,
        mixing_quality=mixing_quality,
    )
    return ChamberFlowStepResult(state=next_state, diagnostics=diagnostics)
