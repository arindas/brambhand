"""Reduced-order leak-jet dynamics baseline."""

from __future__ import annotations

import math
from dataclasses import dataclass

from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class LeakJetPath:
    area_m2: float
    discharge_coefficient: float
    fluid_density_kgpm3: float
    external_pressure_pa: float
    jet_direction_body: Vector3
    lever_arm_body_m: Vector3 = Vector3(0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        if self.area_m2 <= 0.0:
            raise ValueError("area_m2 must be positive.")
        if self.discharge_coefficient <= 0.0:
            raise ValueError("discharge_coefficient must be positive.")
        if self.fluid_density_kgpm3 <= 0.0:
            raise ValueError("fluid_density_kgpm3 must be positive.")
        if self.external_pressure_pa < 0.0:
            raise ValueError("external_pressure_pa cannot be negative.")
        if self.jet_direction_body.norm() == 0.0:
            raise ValueError("jet_direction_body cannot be zero.")


@dataclass(frozen=True)
class LeakJetState:
    mass_flow_kgps: float
    exit_velocity_mps: float
    jet_temperature_k: float
    reaction_force_body_n: Vector3
    reaction_torque_body_nm: Vector3


def evaluate_leak_jet(
    path: LeakJetPath,
    compartment_pressure_pa: float,
    compartment_temperature_k: float,
    ambient_temperature_k: float,
) -> LeakJetState:
    if compartment_pressure_pa < 0.0:
        raise ValueError("compartment_pressure_pa cannot be negative.")
    if compartment_temperature_k <= 0.0:
        raise ValueError("compartment_temperature_k must be positive.")
    if ambient_temperature_k <= 0.0:
        raise ValueError("ambient_temperature_k must be positive.")

    delta_p = max(compartment_pressure_pa - path.external_pressure_pa, 0.0)
    if delta_p == 0.0:
        return LeakJetState(
            mass_flow_kgps=0.0,
            exit_velocity_mps=0.0,
            jet_temperature_k=ambient_temperature_k,
            reaction_force_body_n=Vector3(0.0, 0.0, 0.0),
            reaction_torque_body_nm=Vector3(0.0, 0.0, 0.0),
        )

    exit_velocity_mps = math.sqrt(2.0 * delta_p / path.fluid_density_kgpm3)
    mass_flow_kgps = (
        path.discharge_coefficient
        * path.area_m2
        * path.fluid_density_kgpm3
        * exit_velocity_mps
    )

    thrust_n = mass_flow_kgps * exit_velocity_mps + delta_p * path.area_m2
    reaction_force = path.jet_direction_body.normalized() * (-thrust_n)
    reaction_torque = path.lever_arm_body_m.cross(reaction_force)

    cooling_ratio = min(0.2, delta_p / max(compartment_pressure_pa, 1e-9) * 0.2)
    jet_temperature_k = max(
        ambient_temperature_k,
        compartment_temperature_k * (1.0 - cooling_ratio),
    )

    return LeakJetState(
        mass_flow_kgps=mass_flow_kgps,
        exit_velocity_mps=exit_velocity_mps,
        jet_temperature_k=jet_temperature_k,
        reaction_force_body_n=reaction_force,
        reaction_torque_body_nm=reaction_torque,
    )
