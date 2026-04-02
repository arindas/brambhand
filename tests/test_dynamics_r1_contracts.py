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
