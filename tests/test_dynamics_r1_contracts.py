import math

from brambhand.dynamics.contact_docking import (
    DockingContactOutcome,
    DockingContactParams,
    evaluate_docking_contact,
)
from brambhand.dynamics.mechanisms import JointLimits, JointState, JointType, apply_joint_command
from brambhand.dynamics.rigid_body_6dof import (
    RigidBody6DoFState,
    RigidBodyProperties,
    UnitQuaternion,
    Wrench,
    WrenchFrame,
    integrate_rigid_body_euler,
)
from brambhand.physics.vector import Vector3


def test_rigid_body_contract_integrator_advances_state_and_attitude() -> None:
    state = RigidBody6DoFState(
        position_m=Vector3(0.0, 0.0, 0.0),
        velocity_mps=Vector3(0.0, 0.0, 0.0),
        attitude=UnitQuaternion(1.0, 0.0, 0.0, 0.0),
        angular_velocity_radps=Vector3(0.0, 0.0, 0.0),
    )
    props = RigidBodyProperties(mass_kg=100.0, inertia_diag_kgm2=(10.0, 10.0, 10.0))
    wrench = Wrench(force_n=Vector3(100.0, 0.0, 0.0), torque_nm=Vector3(0.0, 0.0, 10.0))

    next_state = integrate_rigid_body_euler(state, props, wrench, dt_s=1.0)

    assert next_state.velocity_mps.x > 0.0
    assert next_state.position_m.x > 0.0
    assert next_state.angular_velocity_radps.z > 0.0
    assert next_state.attitude != state.attitude


def test_joint_command_clamps_to_limits() -> None:
    state = JointState(
        joint_type=JointType.REVOLUTE,
        position=0.9,
        rate=0.0,
        limits=JointLimits(lower=-1.0, upper=1.0),
    )

    next_state = apply_joint_command(state, commanded_rate=1.0, dt_s=1.0)
    assert next_state.position == 1.0


def test_frame_aware_body_wrench_rotation_is_applied() -> None:
    # 90 deg rotation about z: body +x maps to inertial +y.
    q = UnitQuaternion.normalized(math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5))
    state = RigidBody6DoFState(
        position_m=Vector3(0.0, 0.0, 0.0),
        velocity_mps=Vector3(0.0, 0.0, 0.0),
        attitude=q,
        angular_velocity_radps=Vector3(0.0, 0.0, 0.0),
    )
    props = RigidBodyProperties(mass_kg=1.0, inertia_diag_kgm2=(1.0, 1.0, 1.0))
    wrench_body = Wrench(force_n=Vector3(1.0, 0.0, 0.0), torque_nm=Vector3(0.0, 0.0, 0.0))

    next_state = integrate_rigid_body_euler(
        state,
        props,
        wrench_body,
        dt_s=1.0,
        wrench_frame=WrenchFrame.BODY,
    )

    assert abs(next_state.velocity_mps.x) < 1e-9
    assert next_state.velocity_mps.y > 0.9


def test_angular_velocity_conserved_without_torque_for_spherical_inertia() -> None:
    state = RigidBody6DoFState(
        position_m=Vector3(0.0, 0.0, 0.0),
        velocity_mps=Vector3(1.0, 2.0, 3.0),
        attitude=UnitQuaternion(1.0, 0.0, 0.0, 0.0),
        angular_velocity_radps=Vector3(0.1, -0.2, 0.3),
    )
    props = RigidBodyProperties(mass_kg=100.0, inertia_diag_kgm2=(5.0, 5.0, 5.0))
    wrench = Wrench(force_n=Vector3(0.0, 0.0, 0.0), torque_nm=Vector3(0.0, 0.0, 0.0))

    next_state = integrate_rigid_body_euler(state, props, wrench, dt_s=0.5)

    assert next_state.angular_velocity_radps == state.angular_velocity_radps
    assert next_state.velocity_mps == state.velocity_mps


def test_docking_contact_contract_screening_and_impulse() -> None:
    params = DockingContactParams(
        capture_distance_m=0.2,
        max_capture_speed_mps=0.1,
        contact_distance_m=1.0,
    )

    no_contact = evaluate_docking_contact(2.0, 0.0, params)
    assert no_contact.outcome == DockingContactOutcome.NO_CONTACT

    captured = evaluate_docking_contact(0.1, 0.05, params)
    assert captured.outcome == DockingContactOutcome.CAPTURED
    assert captured.post_contact_relative_speed_mps == 0.0

    rejected = evaluate_docking_contact(0.1, 0.2, params)
    assert rejected.outcome == DockingContactOutcome.REJECTED

    contact = evaluate_docking_contact(0.5, 0.4, params)
    assert contact.outcome == DockingContactOutcome.CONTACT
    assert contact.impulse_ns > 0.0
    assert contact.post_contact_relative_speed_mps < 0.0


def test_rigid_body_gyroscopic_coupling_updates_non_spherical_body() -> None:
    state = RigidBody6DoFState(
        position_m=Vector3(0.0, 0.0, 0.0),
        velocity_mps=Vector3(0.0, 0.0, 0.0),
        attitude=UnitQuaternion(1.0, 0.0, 0.0, 0.0),
        angular_velocity_radps=Vector3(0.0, 1.0, 1.0),
    )
    props = RigidBodyProperties(mass_kg=100.0, inertia_diag_kgm2=(2.0, 3.0, 4.0))
    wrench = Wrench(force_n=Vector3(0.0, 0.0, 0.0), torque_nm=Vector3(0.0, 0.0, 0.0))

    dt_s = 0.01
    next_state = integrate_rigid_body_euler(state, props, wrench, dt_s=dt_s)

    # With tau=0 and w=(0,1,1), gyro = w x (Iw) = (1,0,0),
    # so w_dot = -I^{-1}*gyro = (-0.5, 0, 0).
    assert math.isclose(
        next_state.angular_velocity_radps.x,
        -0.5 * dt_s,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
    assert math.isclose(next_state.angular_velocity_radps.y, 1.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(next_state.angular_velocity_radps.z, 1.0, rel_tol=0.0, abs_tol=1e-12)


def test_docking_contact_threshold_boundaries() -> None:
    params = DockingContactParams(
        capture_distance_m=0.2,
        max_capture_speed_mps=0.1,
        contact_distance_m=1.0,
        restitution=0.4,
        effective_mass_kg=50.0,
        hard_impact_speed_mps=0.8,
    )

    at_contact_boundary = evaluate_docking_contact(
        relative_distance_m=params.contact_distance_m,
        relative_speed_mps=0.2,
        params=params,
    )
    assert at_contact_boundary.outcome == DockingContactOutcome.CONTACT

    outside_contact_boundary = evaluate_docking_contact(
        relative_distance_m=params.contact_distance_m + 1e-9,
        relative_speed_mps=0.2,
        params=params,
    )
    assert outside_contact_boundary.outcome == DockingContactOutcome.NO_CONTACT

    at_capture_boundary = evaluate_docking_contact(
        relative_distance_m=params.capture_distance_m,
        relative_speed_mps=params.max_capture_speed_mps,
        params=params,
    )
    assert at_capture_boundary.outcome == DockingContactOutcome.CAPTURED

    at_hard_impact_boundary = evaluate_docking_contact(
        relative_distance_m=0.5,
        relative_speed_mps=params.hard_impact_speed_mps,
        params=params,
    )
    assert at_hard_impact_boundary.outcome == DockingContactOutcome.CONTACT
