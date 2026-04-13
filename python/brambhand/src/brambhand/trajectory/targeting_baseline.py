"""Deterministic baseline targeting helpers for maneuver-capable mission flows."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from brambhand.physics.vector import Vector3

TARGETING_PROVIDER_CONTRACT_VERSION = 1


@dataclass(frozen=True)
class LambertInitialGuess:
    departure_velocity_mps: Vector3
    arrival_velocity_mps: Vector3
    transfer_angle_rad: float


@dataclass(frozen=True)
class LambertTargetingRequest:
    departure_position_m: Vector3
    arrival_position_m: Vector3
    tof_s: float
    mu_m3_s2: float
    prograde: bool = True


@dataclass(frozen=True)
class SingleShootCorrectionResult:
    corrected_departure_velocity_mps: Vector3
    initial_miss_distance_m: float
    final_miss_distance_m: float
    iterations: int
    converged: bool


@dataclass(frozen=True)
class SingleShootCorrectionRequest:
    departure_position_m: Vector3
    initial_departure_velocity_mps: Vector3
    target_position_m: Vector3
    tof_s: float
    mu_m3_s2: float
    max_iterations: int = 8
    tolerance_m: float = 5.0e4
    perturbation_mps: float = 1.0
    max_step_mps: float = 1_500.0


@dataclass(frozen=True)
class CaptureInsertionConstraints:
    target_periapsis_radius_m: float
    target_apoapsis_radius_m: float
    periapsis_tolerance_m: float = 0.0
    max_eccentricity: float | None = None


@dataclass(frozen=True)
class CaptureTargetingSolution:
    target_velocity_mps: Vector3
    required_delta_v_mps: Vector3
    target_speed_mps: float
    target_eccentricity: float
    predicted_periapsis_radius_m: float
    predicted_apoapsis_radius_m: float


@dataclass(frozen=True)
class CaptureTargetingRequest:
    chaser_position_m: Vector3
    chaser_velocity_mps: Vector3
    primary_position_m: Vector3
    primary_velocity_mps: Vector3
    mu_primary_m3_s2: float
    constraints: CaptureInsertionConstraints


@dataclass(frozen=True)
class CaptureConstraintEvaluation:
    periapsis_within_tolerance: bool
    apoapsis_within_limit: bool
    eccentricity_within_limit: bool

    @property
    def satisfied(self) -> bool:
        return (
            self.periapsis_within_tolerance
            and self.apoapsis_within_limit
            and self.eccentricity_within_limit
        )


class TrajectoryTargetingProvider(Protocol):
    """General targeting interface for baseline and future optimizer-backed providers."""

    def solve_lambert_initial_guess(
        self,
        request: LambertTargetingRequest,
    ) -> LambertInitialGuess: ...

    def solve_single_shoot_correction(
        self,
        request: SingleShootCorrectionRequest,
    ) -> SingleShootCorrectionResult: ...

    def solve_capture_targeting(
        self,
        request: CaptureTargetingRequest,
    ) -> CaptureTargetingSolution: ...


class TargetingOptimizationBackend(Protocol):
    """Backend contract for R11 optimizer integrations.

    Concrete adapters in R11 can implement this protocol and be wrapped by
    `OptimizerBackedTargetingProvider` without changing upstream callers.
    """

    def solve_lambert(
        self,
        request: LambertTargetingRequest,
    ) -> LambertInitialGuess: ...

    def solve_single_shoot(
        self,
        request: SingleShootCorrectionRequest,
    ) -> SingleShootCorrectionResult: ...

    def solve_capture(
        self,
        request: CaptureTargetingRequest,
    ) -> CaptureTargetingSolution: ...


@dataclass(frozen=True)
class OptimizerBackedTargetingProvider:
    """General-provider wrapper around an optimizer backend contract."""

    backend: TargetingOptimizationBackend

    def solve_lambert_initial_guess(
        self,
        request: LambertTargetingRequest,
    ) -> LambertInitialGuess:
        return self.backend.solve_lambert(request)

    def solve_single_shoot_correction(
        self,
        request: SingleShootCorrectionRequest,
    ) -> SingleShootCorrectionResult:
        return self.backend.solve_single_shoot(request)

    def solve_capture_targeting(
        self,
        request: CaptureTargetingRequest,
    ) -> CaptureTargetingSolution:
        return self.backend.solve_capture(request)


@dataclass(frozen=True)
class TwoBodyBaselineTargetingProvider:
    """Concrete non-optimizer implementation of the general targeting interface."""

    contract_version: int = TARGETING_PROVIDER_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != TARGETING_PROVIDER_CONTRACT_VERSION:
            raise ValueError("Unsupported targeting provider contract_version")

    def solve_lambert_initial_guess(
        self,
        request: LambertTargetingRequest,
    ) -> LambertInitialGuess:
        return lambert_initial_guess_two_body(
            departure_position_m=request.departure_position_m,
            arrival_position_m=request.arrival_position_m,
            tof_s=request.tof_s,
            mu_m3_s2=request.mu_m3_s2,
            prograde=request.prograde,
        )

    def solve_single_shoot_correction(
        self,
        request: SingleShootCorrectionRequest,
    ) -> SingleShootCorrectionResult:
        return single_shoot_velocity_correction(
            departure_position_m=request.departure_position_m,
            initial_departure_velocity_mps=request.initial_departure_velocity_mps,
            target_position_m=request.target_position_m,
            tof_s=request.tof_s,
            mu_m3_s2=request.mu_m3_s2,
            max_iterations=request.max_iterations,
            tolerance_m=request.tolerance_m,
            perturbation_mps=request.perturbation_mps,
            max_step_mps=request.max_step_mps,
        )

    def solve_capture_targeting(
        self,
        request: CaptureTargetingRequest,
    ) -> CaptureTargetingSolution:
        return build_capture_targeting_solution(
            chaser_position_m=request.chaser_position_m,
            chaser_velocity_mps=request.chaser_velocity_mps,
            primary_position_m=request.primary_position_m,
            primary_velocity_mps=request.primary_velocity_mps,
            mu_primary_m3_s2=request.mu_primary_m3_s2,
            constraints=request.constraints,
        )


def _stumpff_c(z: float) -> float:
    if z > 1e-8:
        sz = math.sqrt(z)
        return (1.0 - math.cos(sz)) / z
    if z < -1e-8:
        sz = math.sqrt(-z)
        return (math.cosh(sz) - 1.0) / (-z)
    return 0.5 - z / 24.0 + (z * z) / 720.0


def _stumpff_s(z: float) -> float:
    if z > 1e-8:
        sz = math.sqrt(z)
        return (sz - math.sin(sz)) / (sz * sz * sz)
    if z < -1e-8:
        sz = math.sqrt(-z)
        return (math.sinh(sz) - sz) / (sz * sz * sz)
    return (1.0 / 6.0) - z / 120.0 + (z * z) / 5040.0


def lambert_initial_guess_two_body(
    departure_position_m: Vector3,
    arrival_position_m: Vector3,
    tof_s: float,
    mu_m3_s2: float,
    prograde: bool = True,
) -> LambertInitialGuess:
    if tof_s <= 0.0:
        raise ValueError("tof_s must be positive")
    if mu_m3_s2 <= 0.0:
        raise ValueError("mu_m3_s2 must be positive")

    r1 = departure_position_m
    r2 = arrival_position_m
    r1_norm = r1.norm()
    r2_norm = r2.norm()
    if r1_norm <= 0.0 or r2_norm <= 0.0:
        raise ValueError("departure/arrival position norms must be positive")

    cos_dnu = max(-1.0, min(1.0, r1.dot(r2) / (r1_norm * r2_norm)))
    cross_z = r1.cross(r2).z
    sin_dnu_mag = math.sqrt(max(0.0, 1.0 - cos_dnu * cos_dnu))
    sin_dnu = sin_dnu_mag if (cross_z >= 0.0) == prograde else -sin_dnu_mag
    transfer_angle = math.atan2(sin_dnu, cos_dnu)
    if transfer_angle < 0.0:
        transfer_angle += 2.0 * math.pi

    if abs(1.0 - cos_dnu) < 1e-12 or abs(sin_dnu) < 1e-12:
        raise ValueError("Lambert seed is undefined for near-collinear departure/arrival geometry")

    a_term = sin_dnu * math.sqrt((r1_norm * r2_norm) / (1.0 - cos_dnu))

    def tof_for_z(z: float) -> float:
        c = _stumpff_c(z)
        s = _stumpff_s(z)
        if c <= 1e-15:
            raise ValueError("invalid Stumpff C(z)")
        y = r1_norm + r2_norm + a_term * ((z * s - 1.0) / math.sqrt(c))
        if y <= 0.0:
            raise ValueError("invalid Lambert y(z)")
        x = math.sqrt(y / c)
        return (x * x * x * s + a_term * math.sqrt(y)) / math.sqrt(mu_m3_s2)

    z = 0.0
    for _ in range(50):
        current_tof = tof_for_z(z)
        error = current_tof - tof_s
        if abs(error) < 1e-6:
            break
        dz = 1e-5
        tof_plus = tof_for_z(z + dz)
        dtdz = (tof_plus - current_tof) / dz
        if abs(dtdz) < 1e-12:
            break
        z -= error / dtdz
        z = max(-4.0 * math.pi * math.pi, min(4.0 * math.pi * math.pi, z))

    c = _stumpff_c(z)
    s = _stumpff_s(z)
    y = r1_norm + r2_norm + a_term * ((z * s - 1.0) / math.sqrt(c))
    if y <= 0.0:
        raise ValueError("Lambert solve failed to produce positive transfer parameter")

    f = 1.0 - y / r1_norm
    g = a_term * math.sqrt(y / mu_m3_s2)
    g_dot = 1.0 - y / r2_norm

    if abs(g) < 1e-12:
        raise ValueError("Lambert solve produced near-zero g parameter")

    departure_velocity = (r2 - (r1 * f)) / g
    arrival_velocity = ((r2 * g_dot) - r1) / g

    return LambertInitialGuess(
        departure_velocity_mps=departure_velocity,
        arrival_velocity_mps=arrival_velocity,
        transfer_angle_rad=transfer_angle,
    )


def propagate_two_body_state(
    position_m: Vector3,
    velocity_mps: Vector3,
    tof_s: float,
    mu_m3_s2: float,
    steps: int = 512,
) -> tuple[Vector3, Vector3]:
    if tof_s <= 0.0:
        raise ValueError("tof_s must be positive")
    if mu_m3_s2 <= 0.0:
        raise ValueError("mu_m3_s2 must be positive")
    if steps <= 0:
        raise ValueError("steps must be positive")

    dt = tof_s / float(steps)
    pos = position_m
    vel = velocity_mps

    for _ in range(steps):
        r = max(pos.norm(), 1.0)
        acc0 = pos * (-mu_m3_s2 / (r * r * r))
        v_half = vel + (acc0 * (0.5 * dt))
        pos = pos + (v_half * dt)
        r_next = max(pos.norm(), 1.0)
        acc1 = pos * (-mu_m3_s2 / (r_next * r_next * r_next))
        vel = v_half + (acc1 * (0.5 * dt))

    return pos, vel


def _solve_linear_3x3(a: list[list[float]], b: list[float]) -> Vector3 | None:
    m = [row[:] for row in a]
    rhs = b[:]

    for i in range(3):
        pivot = i
        for j in range(i + 1, 3):
            if abs(m[j][i]) > abs(m[pivot][i]):
                pivot = j
        if abs(m[pivot][i]) < 1e-12:
            return None
        if pivot != i:
            m[i], m[pivot] = m[pivot], m[i]
            rhs[i], rhs[pivot] = rhs[pivot], rhs[i]

        scale = m[i][i]
        for k in range(i, 3):
            m[i][k] /= scale
        rhs[i] /= scale

        for j in range(i + 1, 3):
            factor = m[j][i]
            for k in range(i, 3):
                m[j][k] -= factor * m[i][k]
            rhs[j] -= factor * rhs[i]

    x = [0.0, 0.0, 0.0]
    for i in range(2, -1, -1):
        x[i] = rhs[i] - sum(m[i][k] * x[k] for k in range(i + 1, 3))

    return Vector3(x[0], x[1], x[2])


def single_shoot_velocity_correction(
    departure_position_m: Vector3,
    initial_departure_velocity_mps: Vector3,
    target_position_m: Vector3,
    tof_s: float,
    mu_m3_s2: float,
    max_iterations: int = 8,
    tolerance_m: float = 5.0e4,
    perturbation_mps: float = 1.0,
    max_step_mps: float = 1_500.0,
) -> SingleShootCorrectionResult:
    if max_iterations <= 0:
        raise ValueError("max_iterations must be positive")
    if tolerance_m <= 0.0:
        raise ValueError("tolerance_m must be positive")
    if perturbation_mps <= 0.0:
        raise ValueError("perturbation_mps must be positive")
    if max_step_mps <= 0.0:
        raise ValueError("max_step_mps must be positive")

    vel = initial_departure_velocity_mps

    final_position, _ = propagate_two_body_state(
        position_m=departure_position_m,
        velocity_mps=vel,
        tof_s=tof_s,
        mu_m3_s2=mu_m3_s2,
    )
    miss = final_position - target_position_m
    initial_miss = miss.norm()

    iterations = 0
    converged = initial_miss <= tolerance_m
    for iteration in range(1, max_iterations + 1):
        if miss.norm() <= tolerance_m:
            converged = True
            break

        columns: list[Vector3] = []
        for axis in (
            Vector3(perturbation_mps, 0.0, 0.0),
            Vector3(0.0, perturbation_mps, 0.0),
            Vector3(0.0, 0.0, perturbation_mps),
        ):
            perturbed_pos, _ = propagate_two_body_state(
                position_m=departure_position_m,
                velocity_mps=vel + axis,
                tof_s=tof_s,
                mu_m3_s2=mu_m3_s2,
            )
            columns.append((perturbed_pos - final_position) / perturbation_mps)

        jacobian = [
            [columns[0].x, columns[1].x, columns[2].x],
            [columns[0].y, columns[1].y, columns[2].y],
            [columns[0].z, columns[1].z, columns[2].z],
        ]
        rhs = [-miss.x, -miss.y, -miss.z]
        delta_v = _solve_linear_3x3(jacobian, rhs)

        if delta_v is None:
            delta_v = miss * (-1.0 / max(tof_s, 1.0))

        dv_norm = delta_v.norm()
        if dv_norm > max_step_mps:
            delta_v = delta_v * (max_step_mps / dv_norm)

        vel = vel + delta_v
        final_position, _ = propagate_two_body_state(
            position_m=departure_position_m,
            velocity_mps=vel,
            tof_s=tof_s,
            mu_m3_s2=mu_m3_s2,
        )
        miss = final_position - target_position_m
        iterations = iteration

    return SingleShootCorrectionResult(
        corrected_departure_velocity_mps=vel,
        initial_miss_distance_m=initial_miss,
        final_miss_distance_m=miss.norm(),
        iterations=iterations,
        converged=converged or miss.norm() <= tolerance_m,
    )


def build_capture_targeting_solution(
    chaser_position_m: Vector3,
    chaser_velocity_mps: Vector3,
    primary_position_m: Vector3,
    primary_velocity_mps: Vector3,
    mu_primary_m3_s2: float,
    constraints: CaptureInsertionConstraints,
) -> CaptureTargetingSolution:
    if mu_primary_m3_s2 <= 0.0:
        raise ValueError("mu_primary_m3_s2 must be positive")
    if constraints.target_periapsis_radius_m <= 0.0:
        raise ValueError("target_periapsis_radius_m must be positive")
    if constraints.target_apoapsis_radius_m < constraints.target_periapsis_radius_m:
        raise ValueError("target_apoapsis_radius_m must be >= target_periapsis_radius_m")
    if constraints.periapsis_tolerance_m < 0.0:
        raise ValueError("periapsis_tolerance_m must be >= 0")
    if constraints.max_eccentricity is not None and constraints.max_eccentricity < 0.0:
        raise ValueError("max_eccentricity must be >= 0")

    rel_r = chaser_position_m - primary_position_m
    rel_v = chaser_velocity_mps - primary_velocity_mps
    radius = rel_r.norm()
    if radius <= 0.0:
        raise ValueError("relative radius must be positive")

    radial_hat = rel_r / radius
    tangential_hat = Vector3(-radial_hat.y, radial_hat.x, 0.0)
    if tangential_hat.norm() <= 1e-12:
        tangential_hat = Vector3(0.0, 1.0, 0.0)
    else:
        tangential_hat = tangential_hat.normalized()

    angular_momentum_z = rel_r.cross(rel_v).z
    if angular_momentum_z < 0.0:
        tangential_hat = tangential_hat * -1.0

    rp = constraints.target_periapsis_radius_m
    ra = constraints.target_apoapsis_radius_m
    if not (rp <= radius <= ra):
        raise ValueError(
            "current encounter radius must lie inside target insertion orbit [periapsis, apoapsis]"
        )

    semi_major_axis = 0.5 * (rp + ra)
    target_speed = math.sqrt(
        mu_primary_m3_s2 * ((2.0 / radius) - (1.0 / semi_major_axis))
    )
    target_rel_velocity = tangential_hat * target_speed
    target_velocity = primary_velocity_mps + target_rel_velocity

    eccentricity = (ra - rp) / max(ra + rp, 1.0)

    return CaptureTargetingSolution(
        target_velocity_mps=target_velocity,
        required_delta_v_mps=target_velocity - chaser_velocity_mps,
        target_speed_mps=target_speed,
        target_eccentricity=eccentricity,
        predicted_periapsis_radius_m=rp,
        predicted_apoapsis_radius_m=ra,
    )


def evaluate_capture_insertion_constraints(
    solution: CaptureTargetingSolution,
    constraints: CaptureInsertionConstraints,
) -> CaptureConstraintEvaluation:
    periapsis_ok = (
        abs(solution.predicted_periapsis_radius_m - constraints.target_periapsis_radius_m)
        <= constraints.periapsis_tolerance_m
    )
    apoapsis_ok = solution.predicted_apoapsis_radius_m <= constraints.target_apoapsis_radius_m

    if constraints.max_eccentricity is None:
        eccentricity_ok = True
    else:
        eccentricity_ok = solution.target_eccentricity <= constraints.max_eccentricity

    return CaptureConstraintEvaluation(
        periapsis_within_tolerance=periapsis_ok,
        apoapsis_within_limit=apoapsis_ok,
        eccentricity_within_limit=eccentricity_ok,
    )
