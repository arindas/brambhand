"""Reduced-order combustion chamber dynamics baseline.

Why this module exists:
- Convert feed mass flow into chamber pressure evolution for thrust estimation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CombustionChamberParams:
    """Idealized chamber thermodynamic parameters."""

    volume_m3: float
    gas_constant_jpkgk: float
    temperature_k: float

    def __post_init__(self) -> None:
        if self.volume_m3 <= 0.0:
            raise ValueError("volume_m3 must be positive.")
        if self.gas_constant_jpkgk <= 0.0:
            raise ValueError("gas_constant_jpkgk must be positive.")
        if self.temperature_k <= 0.0:
            raise ValueError("temperature_k must be positive.")


@dataclass(frozen=True)
class CombustionChamberState:
    """Combustion chamber state based on gas mass and pressure."""

    gas_mass_kg: float
    pressure_pa: float

    def __post_init__(self) -> None:
        if self.gas_mass_kg < 0.0:
            raise ValueError("gas_mass_kg cannot be negative.")
        if self.pressure_pa < 0.0:
            raise ValueError("pressure_pa cannot be negative.")


def step_combustion_chamber(
    state: CombustionChamberState,
    params: CombustionChamberParams,
    inflow_kgps: float,
    outflow_kgps: float,
    dt_s: float,
) -> CombustionChamberState:
    """Advance chamber gas state using mass balance + ideal gas pressure."""
    if dt_s <= 0.0:
        raise ValueError("dt_s must be positive.")
    if inflow_kgps < 0.0 or outflow_kgps < 0.0:
        raise ValueError("inflow_kgps and outflow_kgps must be non-negative.")

    next_mass = max(0.0, state.gas_mass_kg + (inflow_kgps - outflow_kgps) * dt_s)
    next_pressure = next_mass * params.gas_constant_jpkgk * params.temperature_k / params.volume_m3

    return CombustionChamberState(gas_mass_kg=next_mass, pressure_pa=next_pressure)
