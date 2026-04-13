import math

import pytest

from brambhand.physics.vector import Vector3
from brambhand.trajectory.targeting_baseline import (
    CaptureInsertionConstraints,
    CaptureTargetingRequest,
    CaptureTargetingSolution,
    LambertInitialGuess,
    LambertTargetingRequest,
    OptimizerBackedTargetingProvider,
    SingleShootCorrectionRequest,
    SingleShootCorrectionResult,
    TwoBodyBaselineTargetingProvider,
    build_capture_targeting_solution,
    evaluate_capture_insertion_constraints,
    lambert_initial_guess_two_body,
    propagate_two_body_state,
    single_shoot_velocity_correction,
)


def test_lambert_initial_guess_is_deterministic_and_hits_transfer_envelope() -> None:
    mu_earth = 3.986004418e14
    departure = Vector3(7_000_000.0, 0.0, 0.0)
    truth_velocity = Vector3(0.0, 7_550.0, 0.0)
    tof_s = 1_200.0

    arrival, _ = propagate_two_body_state(
        position_m=departure,
        velocity_mps=truth_velocity,
        tof_s=tof_s,
        mu_m3_s2=mu_earth,
    )

    guess_a = lambert_initial_guess_two_body(departure, arrival, tof_s, mu_earth)
    guess_b = lambert_initial_guess_two_body(departure, arrival, tof_s, mu_earth)

    assert guess_a == guess_b
    assert 0.0 < guess_a.transfer_angle_rad < math.pi

    propagated_arrival, _ = propagate_two_body_state(
        position_m=departure,
        velocity_mps=guess_a.departure_velocity_mps,
        tof_s=tof_s,
        mu_m3_s2=mu_earth,
    )
    miss = (propagated_arrival - arrival).norm()
    assert miss < 150_000.0


def test_single_shoot_correction_reduces_miss_distance() -> None:
    mu_earth = 3.986004418e14
    departure = Vector3(7_000_000.0, 0.0, 0.0)
    truth_velocity = Vector3(0.0, 7_550.0, 0.0)
    tof_s = 1_200.0

    arrival, _ = propagate_two_body_state(
        position_m=departure,
        velocity_mps=truth_velocity,
        tof_s=tof_s,
        mu_m3_s2=mu_earth,
    )

    seed_result = lambert_initial_guess_two_body(departure, arrival, tof_s, mu_earth)
    seed = seed_result.departure_velocity_mps
    biased_seed = seed + Vector3(250.0, -200.0, 25.0)

    result = single_shoot_velocity_correction(
        departure_position_m=departure,
        initial_departure_velocity_mps=biased_seed,
        target_position_m=arrival,
        tof_s=tof_s,
        mu_m3_s2=mu_earth,
        max_iterations=6,
        tolerance_m=80_000.0,
    )

    assert result.final_miss_distance_m < result.initial_miss_distance_m
    assert result.final_miss_distance_m < 200_000.0


def test_capture_targeting_solution_and_constraints_for_mars_insertion() -> None:
    mu_mars = 4.282837e13
    mars_position = Vector3(0.0, 0.0, 0.0)
    mars_velocity = Vector3(0.0, 0.0, 0.0)

    chaser_position = Vector3(9_500_000.0, 0.0, 0.0)
    chaser_velocity = Vector3(0.0, 1_500.0, 0.0)

    constraints = CaptureInsertionConstraints(
        target_periapsis_radius_m=8_000_000.0,
        target_apoapsis_radius_m=12_000_000.0,
        periapsis_tolerance_m=1.0,
        max_eccentricity=0.25,
    )

    solution_a = build_capture_targeting_solution(
        chaser_position_m=chaser_position,
        chaser_velocity_mps=chaser_velocity,
        primary_position_m=mars_position,
        primary_velocity_mps=mars_velocity,
        mu_primary_m3_s2=mu_mars,
        constraints=constraints,
    )
    solution_b = build_capture_targeting_solution(
        chaser_position_m=chaser_position,
        chaser_velocity_mps=chaser_velocity,
        primary_position_m=mars_position,
        primary_velocity_mps=mars_velocity,
        mu_primary_m3_s2=mu_mars,
        constraints=constraints,
    )

    assert solution_a == solution_b
    assert solution_a.target_speed_mps > 0.0

    evaluation = evaluate_capture_insertion_constraints(solution_a, constraints)
    assert evaluation.satisfied


def test_capture_targeting_rejects_out_of_orbit_radius_bounds() -> None:
    constraints = CaptureInsertionConstraints(
        target_periapsis_radius_m=8_000_000.0,
        target_apoapsis_radius_m=12_000_000.0,
    )

    with pytest.raises(ValueError, match="encounter radius"):
        build_capture_targeting_solution(
            chaser_position_m=Vector3(13_500_000.0, 0.0, 0.0),
            chaser_velocity_mps=Vector3(0.0, 1_500.0, 0.0),
            primary_position_m=Vector3(0.0, 0.0, 0.0),
            primary_velocity_mps=Vector3(0.0, 0.0, 0.0),
            mu_primary_m3_s2=4.282837e13,
            constraints=constraints,
        )


def test_baseline_provider_implements_general_targeting_interface() -> None:
    provider = TwoBodyBaselineTargetingProvider()

    mu_earth = 3.986004418e14
    departure = Vector3(7_000_000.0, 0.0, 0.0)
    truth_velocity = Vector3(0.0, 7_550.0, 0.0)
    tof_s = 1_200.0
    arrival, _ = propagate_two_body_state(
        position_m=departure,
        velocity_mps=truth_velocity,
        tof_s=tof_s,
        mu_m3_s2=mu_earth,
    )

    lambert = provider.solve_lambert_initial_guess(
        LambertTargetingRequest(
            departure_position_m=departure,
            arrival_position_m=arrival,
            tof_s=tof_s,
            mu_m3_s2=mu_earth,
        )
    )

    correction = provider.solve_single_shoot_correction(
        SingleShootCorrectionRequest(
            departure_position_m=departure,
            initial_departure_velocity_mps=(
                lambert.departure_velocity_mps + Vector3(50.0, -40.0, 2.0)
            ),
            target_position_m=arrival,
            tof_s=tof_s,
            mu_m3_s2=mu_earth,
        )
    )

    assert correction.final_miss_distance_m < correction.initial_miss_distance_m

    capture = provider.solve_capture_targeting(
        CaptureTargetingRequest(
            chaser_position_m=Vector3(9_500_000.0, 0.0, 0.0),
            chaser_velocity_mps=Vector3(0.0, 1_500.0, 0.0),
            primary_position_m=Vector3(0.0, 0.0, 0.0),
            primary_velocity_mps=Vector3(0.0, 0.0, 0.0),
            mu_primary_m3_s2=4.282837e13,
            constraints=CaptureInsertionConstraints(
                target_periapsis_radius_m=8_000_000.0,
                target_apoapsis_radius_m=12_000_000.0,
            ),
        )
    )

    assert capture.target_speed_mps > 0.0


class _FakeOptimizerBackend:
    def solve_lambert(self, request: LambertTargetingRequest) -> LambertInitialGuess:
        _ = request
        return LambertInitialGuess(
            departure_velocity_mps=Vector3(1.0, 0.0, 0.0),
            arrival_velocity_mps=Vector3(0.0, 1.0, 0.0),
            transfer_angle_rad=0.5,
        )

    def solve_single_shoot(
        self,
        request: SingleShootCorrectionRequest,
    ) -> SingleShootCorrectionResult:
        _ = request
        return SingleShootCorrectionResult(
            corrected_departure_velocity_mps=Vector3(2.0, 0.0, 0.0),
            initial_miss_distance_m=1000.0,
            final_miss_distance_m=100.0,
            iterations=2,
            converged=True,
        )

    def solve_capture(
        self,
        request: CaptureTargetingRequest,
    ) -> CaptureTargetingSolution:
        _ = request
        return CaptureTargetingSolution(
            target_velocity_mps=Vector3(0.0, 3.0, 0.0),
            required_delta_v_mps=Vector3(0.0, 1.0, 0.0),
            target_speed_mps=3.0,
            target_eccentricity=0.1,
            predicted_periapsis_radius_m=8_000_000.0,
            predicted_apoapsis_radius_m=12_000_000.0,
        )


def test_optimizer_backed_provider_uses_general_backend_contract() -> None:
    provider = OptimizerBackedTargetingProvider(backend=_FakeOptimizerBackend())

    lambert = provider.solve_lambert_initial_guess(
        LambertTargetingRequest(
            departure_position_m=Vector3(1.0, 0.0, 0.0),
            arrival_position_m=Vector3(0.0, 1.0, 0.0),
            tof_s=10.0,
            mu_m3_s2=1.0,
        )
    )
    correction = provider.solve_single_shoot_correction(
        SingleShootCorrectionRequest(
            departure_position_m=Vector3(1.0, 0.0, 0.0),
            initial_departure_velocity_mps=Vector3(0.0, 1.0, 0.0),
            target_position_m=Vector3(0.5, 0.5, 0.0),
            tof_s=10.0,
            mu_m3_s2=1.0,
        )
    )
    capture = provider.solve_capture_targeting(
        CaptureTargetingRequest(
            chaser_position_m=Vector3(9_000_000.0, 0.0, 0.0),
            chaser_velocity_mps=Vector3(0.0, 1200.0, 0.0),
            primary_position_m=Vector3(0.0, 0.0, 0.0),
            primary_velocity_mps=Vector3(0.0, 0.0, 0.0),
            mu_primary_m3_s2=4.282837e13,
            constraints=CaptureInsertionConstraints(
                target_periapsis_radius_m=8_000_000.0,
                target_apoapsis_radius_m=12_000_000.0,
            ),
        )
    )

    assert lambert.transfer_angle_rad == 0.5
    assert correction.converged
    assert capture.target_speed_mps == 3.0
