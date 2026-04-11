"""Leak-jet to 6-DOF rigid-body coupling helpers."""

from __future__ import annotations

from brambhand.dynamics.rigid_body_6dof import (
    RigidBody6DoFState,
    RigidBodyProperties,
    Wrench,
    WrenchFrame,
    integrate_rigid_body_euler,
)
from brambhand.fluid.contracts import (
    LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
    LeakJetBoundaryPayload,
)
from brambhand.fluid.reduced.leak_jet_dynamics import LeakJetState


def build_leak_jet_boundary_payload(
    leak_jet: LeakJetState,
    interface_id: str,
) -> LeakJetBoundaryPayload:
    """Build versioned leak-jet boundary payload for FSI exchange contracts."""
    return LeakJetBoundaryPayload(
        interface_id=interface_id,
        schema_version=LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
        reaction_force_body_n=leak_jet.reaction_force_body_n,
        reaction_torque_body_nm=leak_jet.reaction_torque_body_nm,
        mass_flow_kgps=leak_jet.mass_flow_kgps,
        jet_temperature_k=leak_jet.jet_temperature_k,
    )


def propagate_leak_jet_to_rigid_body(
    state: RigidBody6DoFState,
    props: RigidBodyProperties,
    leak_jet: LeakJetState,
    dt_s: float,
) -> RigidBody6DoFState:
    """Advance rigid-body state using leak-jet reaction force/torque in body frame."""
    wrench = Wrench(
        force_n=leak_jet.reaction_force_body_n,
        torque_nm=leak_jet.reaction_torque_body_nm,
    )
    return integrate_rigid_body_euler(
        state=state,
        props=props,
        wrench=wrench,
        dt_s=dt_s,
        wrench_frame=WrenchFrame.BODY,
    )
