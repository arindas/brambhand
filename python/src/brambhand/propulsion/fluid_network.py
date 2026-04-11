"""Reduced-order propulsion feed fluid network baseline.

Why this module exists:
- Provide deterministic tank->valve->line mass flow estimates for early R2 work.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TankState:
    """Simplified tank state with pressure tied to remaining mass."""

    mass_kg: float
    nominal_mass_kg: float
    nominal_pressure_pa: float
    temperature_k: float

    def __post_init__(self) -> None:
        if self.mass_kg < 0.0:
            raise ValueError("mass_kg cannot be negative.")
        if self.nominal_mass_kg <= 0.0:
            raise ValueError("nominal_mass_kg must be positive.")
        if self.nominal_pressure_pa <= 0.0:
            raise ValueError("nominal_pressure_pa must be positive.")
        if self.temperature_k <= 0.0:
            raise ValueError("temperature_k must be positive.")

    @property
    def pressure_pa(self) -> float:
        """Approximate pressure based on remaining mass fraction."""
        return self.nominal_pressure_pa * (self.mass_kg / self.nominal_mass_kg)


@dataclass(frozen=True)
class ValveState:
    """Valve opening and flow coefficient."""

    opening: float
    flow_coefficient: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.opening <= 1.0:
            raise ValueError("opening must be in [0, 1].")
        if self.flow_coefficient <= 0.0:
            raise ValueError("flow_coefficient must be positive.")


@dataclass(frozen=True)
class LineState:
    """Line flow capacity limit."""

    max_flow_kgps: float

    def __post_init__(self) -> None:
        if self.max_flow_kgps <= 0.0:
            raise ValueError("max_flow_kgps must be positive.")


@dataclass(frozen=True)
class FluidNetworkState:
    """Tank/valve/line aggregate state for propulsion feed network."""

    tank: TankState
    valve: ValveState
    line: LineState
    downstream_pressure_pa: float
    delivered_mass_flow_kgps: float = 0.0

    def __post_init__(self) -> None:
        if self.downstream_pressure_pa < 0.0:
            raise ValueError("downstream_pressure_pa cannot be negative.")
        if self.delivered_mass_flow_kgps < 0.0:
            raise ValueError("delivered_mass_flow_kgps cannot be negative.")


def step_fluid_network(state: FluidNetworkState, dt_s: float) -> FluidNetworkState:
    """Advance fluid network by one step and return updated state."""
    if dt_s <= 0.0:
        raise ValueError("dt_s must be positive.")

    if state.valve.opening == 0.0 or state.tank.mass_kg == 0.0:
        return FluidNetworkState(
            tank=state.tank,
            valve=state.valve,
            line=state.line,
            downstream_pressure_pa=state.downstream_pressure_pa,
            delivered_mass_flow_kgps=0.0,
        )

    delta_p = max(state.tank.pressure_pa - state.downstream_pressure_pa, 0.0)
    raw_flow = state.valve.flow_coefficient * state.valve.opening * math.sqrt(delta_p)
    candidate_flow = min(raw_flow, state.line.max_flow_kgps)

    transferable_mass = min(candidate_flow * dt_s, state.tank.mass_kg)
    delivered_flow = transferable_mass / dt_s

    next_tank = TankState(
        mass_kg=state.tank.mass_kg - transferable_mass,
        nominal_mass_kg=state.tank.nominal_mass_kg,
        nominal_pressure_pa=state.tank.nominal_pressure_pa,
        temperature_k=state.tank.temperature_k,
    )

    return FluidNetworkState(
        tank=next_tank,
        valve=state.valve,
        line=state.line,
        downstream_pressure_pa=state.downstream_pressure_pa,
        delivered_mass_flow_kgps=delivered_flow,
    )
