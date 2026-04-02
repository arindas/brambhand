"""Leakage model baseline for propulsion and chassis compartments.

Why this module exists:
- Represent pressure-driven mass loss faults that feed mission fault behavior.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class LeakagePath:
    """Leak path parameters for pressure-driven outflow."""

    area_m2: float
    discharge_coefficient: float
    fluid_density_kgpm3: float
    external_pressure_pa: float

    def __post_init__(self) -> None:
        if self.area_m2 <= 0.0:
            raise ValueError("area_m2 must be positive.")
        if self.discharge_coefficient <= 0.0:
            raise ValueError("discharge_coefficient must be positive.")
        if self.fluid_density_kgpm3 <= 0.0:
            raise ValueError("fluid_density_kgpm3 must be positive.")
        if self.external_pressure_pa < 0.0:
            raise ValueError("external_pressure_pa cannot be negative.")


@dataclass(frozen=True)
class CompartmentState:
    """Compartment mass/pressure state using ideal gas pressure update."""

    mass_kg: float
    pressure_pa: float
    volume_m3: float
    gas_constant_jpkgk: float
    temperature_k: float

    def __post_init__(self) -> None:
        if self.mass_kg < 0.0:
            raise ValueError("mass_kg cannot be negative.")
        if self.pressure_pa < 0.0:
            raise ValueError("pressure_pa cannot be negative.")
        if self.volume_m3 <= 0.0:
            raise ValueError("volume_m3 must be positive.")
        if self.gas_constant_jpkgk <= 0.0:
            raise ValueError("gas_constant_jpkgk must be positive.")
        if self.temperature_k <= 0.0:
            raise ValueError("temperature_k must be positive.")


def apply_leakage(
    state: CompartmentState,
    leak: LeakagePath,
    dt_s: float,
) -> tuple[CompartmentState, float]:
    """Apply pressure-driven leakage and return `(next_state, leaked_mass_kg)`."""
    if dt_s <= 0.0:
        raise ValueError("dt_s must be positive.")

    delta_p = max(state.pressure_pa - leak.external_pressure_pa, 0.0)
    if delta_p == 0.0 or state.mass_kg == 0.0:
        return state, 0.0

    mass_flow = leak.discharge_coefficient * leak.area_m2 * math.sqrt(
        2.0 * leak.fluid_density_kgpm3 * delta_p
    )
    leaked_mass = min(state.mass_kg, mass_flow * dt_s)
    next_mass = state.mass_kg - leaked_mass
    next_pressure = next_mass * state.gas_constant_jpkgk * state.temperature_k / state.volume_m3

    next_state = CompartmentState(
        mass_kg=next_mass,
        pressure_pa=next_pressure,
        volume_m3=state.volume_m3,
        gas_constant_jpkgk=state.gas_constant_jpkgk,
        temperature_k=state.temperature_k,
    )
    return next_state, leaked_mass
