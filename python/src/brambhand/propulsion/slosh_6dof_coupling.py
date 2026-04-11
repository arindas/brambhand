"""Slosh-load to 6-DOF rigid-body coupling helpers."""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.dynamics.rigid_body_6dof import (
    RigidBody6DoFState,
    RigidBodyProperties,
    Wrench,
    WrenchFrame,
    integrate_rigid_body_euler,
)
from brambhand.fluid.reduced.slosh_model import SloshLoad
from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class SloshRigidBodyCouplingResult:
    """Result bundle for one slosh-coupled rigid-body step."""

    state: RigidBody6DoFState
    effective_com_body_m: Vector3
    effective_com_inertial_m: Vector3


def propagate_slosh_to_rigid_body(
    state: RigidBody6DoFState,
    props: RigidBodyProperties,
    slosh_load: SloshLoad,
    dt_s: float,
    nominal_com_body_m: Vector3 | None = None,
) -> SloshRigidBodyCouplingResult:
    """Advance 6-DOF state with slosh wrench and CoM-offset propagation."""
    if nominal_com_body_m is None:
        nominal_com_body_m = Vector3(0.0, 0.0, 0.0)

    wrench = Wrench(
        force_n=slosh_load.force_body_n,
        torque_nm=slosh_load.torque_body_nm,
    )
    next_state = integrate_rigid_body_euler(
        state=state,
        props=props,
        wrench=wrench,
        dt_s=dt_s,
        wrench_frame=WrenchFrame.BODY,
    )

    effective_com_body = nominal_com_body_m + slosh_load.com_offset_body_m
    effective_com_inertial = (
        next_state.position_m + next_state.attitude.rotate_vector(effective_com_body)
    )

    return SloshRigidBodyCouplingResult(
        state=next_state,
        effective_com_body_m=effective_com_body,
        effective_com_inertial_m=effective_com_inertial,
    )
