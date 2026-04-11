"""Reduced-order propellant slosh model baseline.

Why this module exists:
- Provide deterministic lumped spring-mass slosh dynamics for R2.3.
- Export equivalent body-frame force/torque and CoM-offset load terms.
- Provide geometry-aware parameter hooks for STL-derived tank descriptors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class SloshModelParams:
    """Configuration for lumped spring-mass slosh equivalent."""

    slosh_mass_kg: float
    spring_constant_npm: float
    damping_nspm: float
    max_displacement_m: float
    lever_arm_body_m: Vector3 = Vector3(0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        if self.slosh_mass_kg <= 0.0:
            raise ValueError("slosh_mass_kg must be positive.")
        if self.spring_constant_npm <= 0.0:
            raise ValueError("spring_constant_npm must be positive.")
        if self.damping_nspm < 0.0:
            raise ValueError("damping_nspm cannot be negative.")
        if self.max_displacement_m <= 0.0:
            raise ValueError("max_displacement_m must be positive.")


@dataclass(frozen=True)
class SloshGeometryDescriptor:
    """Geometry descriptor hook for slosh tuning (STL-derived or manual).

    `source` is intentionally stringly-typed to avoid hard-coupling with an STL
    importer module while still carrying provenance (`"stl"`, `"manual"`, etc.).
    """

    source: str
    characteristic_length_m: float
    equivalent_radius_m: float
    fill_fraction: float
    baffle_count: int = 0

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("source must be non-empty.")
        if self.characteristic_length_m <= 0.0:
            raise ValueError("characteristic_length_m must be positive.")
        if self.equivalent_radius_m <= 0.0:
            raise ValueError("equivalent_radius_m must be positive.")
        if not 0.0 <= self.fill_fraction <= 1.0:
            raise ValueError("fill_fraction must be in [0, 1].")
        if self.baffle_count < 0:
            raise ValueError("baffle_count cannot be negative.")


@dataclass(frozen=True)
class SloshFallbackParams:
    """Fallback slosh tuning when geometry descriptor is unavailable."""

    natural_frequency_hz: float
    damping_ratio: float
    max_displacement_m: float

    def __post_init__(self) -> None:
        if self.natural_frequency_hz <= 0.0:
            raise ValueError("natural_frequency_hz must be positive.")
        if self.damping_ratio < 0.0:
            raise ValueError("damping_ratio cannot be negative.")
        if self.max_displacement_m <= 0.0:
            raise ValueError("max_displacement_m must be positive.")


@dataclass(frozen=True)
class SloshState:
    """Reduced-order internal slosh state in body frame."""

    displacement_body_m: Vector3
    velocity_body_mps: Vector3


@dataclass(frozen=True)
class SloshLoad:
    """Equivalent slosh load contribution in body frame."""

    force_body_n: Vector3
    torque_body_nm: Vector3
    com_offset_body_m: Vector3


@dataclass(frozen=True)
class SloshStepResult:
    """Result bundle for one deterministic slosh integration step."""

    state: SloshState
    load: SloshLoad


def derive_slosh_model_params(
    slosh_mass_kg: float,
    fallback: SloshFallbackParams,
    geometry: SloshGeometryDescriptor | None = None,
    lever_arm_body_m: Vector3 | None = None,
) -> SloshModelParams:
    """Derive slosh parameters with geometry-aware hooks and fallback policy."""
    if slosh_mass_kg <= 0.0:
        raise ValueError("slosh_mass_kg must be positive.")

    if lever_arm_body_m is None:
        lever_arm_body_m = Vector3(0.0, 0.0, 0.0)

    omega_fallback = 2.0 * math.pi * fallback.natural_frequency_hz
    spring_constant = slosh_mass_kg * omega_fallback * omega_fallback
    damping = 2.0 * fallback.damping_ratio * math.sqrt(spring_constant * slosh_mass_kg)
    max_displacement = fallback.max_displacement_m

    if geometry is not None:
        aspect_ratio = geometry.characteristic_length_m / (2.0 * geometry.equivalent_radius_m)
        aspect_factor = min(1.5, max(0.6, 1.0 + 0.15 * (aspect_ratio - 1.0)))
        baffle_factor = 1.0 + 0.15 * geometry.baffle_count
        fill_factor = min(1.25, max(0.7, 1.0 - 0.3 * (geometry.fill_fraction - 0.5)))

        spring_constant *= aspect_factor * fill_factor
        damping *= baffle_factor
        max_displacement = min(
            fallback.max_displacement_m,
            geometry.equivalent_radius_m * max(0.05, 1.0 - geometry.fill_fraction * 0.5),
        )

    return SloshModelParams(
        slosh_mass_kg=slosh_mass_kg,
        spring_constant_npm=spring_constant,
        damping_nspm=damping,
        max_displacement_m=max_displacement,
        lever_arm_body_m=lever_arm_body_m,
    )


def _clamp_displacement(displacement_body_m: Vector3, max_displacement_m: float) -> Vector3:
    norm = displacement_body_m.norm()
    if norm <= max_displacement_m or norm == 0.0:
        return displacement_body_m
    return displacement_body_m * (max_displacement_m / norm)


def step_slosh_state(
    state: SloshState,
    params: SloshModelParams,
    body_linear_accel_body_mps2: Vector3,
    dt_s: float,
) -> SloshStepResult:
    """Advance lumped slosh state and return equivalent load terms.

    Model form per axis (body frame):
        m*x_ddot + c*x_dot + k*x = -m*a_body
    where `x` is slosh relative displacement from the nominal tank centerline.
    """
    if dt_s <= 0.0:
        raise ValueError("dt_s must be positive.")

    spring_force = state.displacement_body_m * (-params.spring_constant_npm)
    damping_force = state.velocity_body_mps * (-params.damping_nspm)
    restoring_force = spring_force + damping_force

    relative_accel = restoring_force / params.slosh_mass_kg - body_linear_accel_body_mps2

    next_velocity = state.velocity_body_mps + relative_accel * dt_s
    next_displacement = _clamp_displacement(
        state.displacement_body_m + next_velocity * dt_s,
        params.max_displacement_m,
    )

    reaction_force = (
        next_displacement * params.spring_constant_npm
        + next_velocity * params.damping_nspm
    )
    reaction_torque = params.lever_arm_body_m.cross(reaction_force)

    next_state = SloshState(
        displacement_body_m=next_displacement,
        velocity_body_mps=next_velocity,
    )
    return SloshStepResult(
        state=next_state,
        load=SloshLoad(
            force_body_n=reaction_force,
            torque_body_nm=reaction_torque,
            com_offset_body_m=next_displacement,
        ),
    )
