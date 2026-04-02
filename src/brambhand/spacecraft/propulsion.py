"""Propulsion and burn execution model.

Why this module exists:
- Encapsulate thrust, mass flow, and delta-v computation in one tested module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.constants import g

from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.vector import Vector3
from brambhand.spacecraft.mass_model import MassModel


@dataclass(frozen=True)
class BurnResult:
    """Outputs of a burn application step."""

    body: PhysicalBody
    mass_model: MassModel
    delta_v_mps: Vector3
    burned_duration_s: float
    consumed_propellant_kg: float


@dataclass(frozen=True)
class PropulsionSystem:
    """Constant-Isp propulsion model with throttle control."""

    max_thrust_n: float
    specific_impulse_s: float
    g0_mps2: float = g

    def __post_init__(self) -> None:
        if self.max_thrust_n <= 0.0:
            raise ValueError("max_thrust_n must be positive.")
        if self.specific_impulse_s <= 0.0:
            raise ValueError("specific_impulse_s must be positive.")
        if self.g0_mps2 <= 0.0:
            raise ValueError("g0_mps2 must be positive.")

    @property
    def exhaust_velocity_mps(self) -> float:
        """Return effective exhaust velocity (`Isp * g0`)."""
        return self.specific_impulse_s * self.g0_mps2

    def thrust_n(self, throttle: float) -> float:
        """Return thrust at throttle fraction in [0, 1]."""
        if not 0.0 <= throttle <= 1.0:
            raise ValueError("throttle must be in [0, 1].")
        return self.max_thrust_n * throttle

    def mass_flow_rate_kgps(self, throttle: float) -> float:
        """Return propellant mass flow rate at given throttle."""
        return self.thrust_n(throttle) / self.exhaust_velocity_mps

    def apply_burn(
        self,
        body: PhysicalBody,
        mass_model: MassModel,
        direction: Vector3,
        throttle: float,
        duration_s: float,
    ) -> BurnResult:
        """Apply finite burn and return updated body/mass and delta-v outputs.

        Why: single-source implementation of burn physics for direct use and
        command-window execution.
        """
        if duration_s < 0.0:
            raise ValueError("duration_s cannot be negative.")
        if duration_s == 0.0 or throttle == 0.0:
            return BurnResult(
                body=body,
                mass_model=mass_model,
                delta_v_mps=Vector3(0.0, 0.0, 0.0),
                burned_duration_s=0.0,
                consumed_propellant_kg=0.0,
            )

        unit_dir = direction.normalized()

        m0 = mass_model.total_mass_kg
        mdot = self.mass_flow_rate_kgps(throttle)
        requested_propellant = mdot * duration_s

        new_mass_model, consumed_kg = mass_model.consume(requested_propellant)
        effective_duration_s = consumed_kg / mdot if mdot > 0.0 else 0.0

        m1 = new_mass_model.total_mass_kg
        if m1 <= 0.0 or m1 > m0:
            raise RuntimeError("Invalid mass state during burn.")

        if math.isclose(m0, m1):
            delta_v_mag = 0.0
        else:
            delta_v_mag = self.exhaust_velocity_mps * math.log(m0 / m1)

        delta_v = unit_dir * delta_v_mag
        new_velocity = body.state.velocity + delta_v

        updated_body = PhysicalBody(
            name=body.name,
            mass=new_mass_model.total_mass_kg,
            state=InertialState(position=body.state.position, velocity=new_velocity),
        )

        return BurnResult(
            body=updated_body,
            mass_model=new_mass_model,
            delta_v_mps=delta_v,
            burned_duration_s=effective_duration_s,
            consumed_propellant_kg=consumed_kg,
        )
