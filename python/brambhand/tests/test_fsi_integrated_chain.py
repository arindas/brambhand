from brambhand.coupling.controller import (
    FSICouplingControllerPolicy,
    run_fsi_coupling_with_controller,
)
from brambhand.coupling.exchange_contracts import build_fsi_boundary_exchange_contract
from brambhand.coupling.fsi_coupler import InterfaceDisplacement, StructuralBoundaryProvider
from brambhand.dynamics.rigid_body_6dof import (
    RigidBody6DoFState,
    RigidBodyProperties,
    UnitQuaternion,
    Wrench,
    WrenchFrame,
    integrate_rigid_body_euler,
)
from brambhand.fluid.contracts import FaultTransitionKind, FluidBoundaryLoad
from brambhand.fluid.reduced.leak_jet_dynamics import LeakJetState
from brambhand.fluid.reduced.slosh_model import SloshLoad
from brambhand.mission.assembly_topology import (
    apply_docking_attach_transition,
    apply_fracture_split_transition,
    build_topology_transition_payload,
    create_assembly_topology_state,
)
from brambhand.physics.vector import Vector3
from brambhand.propulsion.leak_jet_coupling import build_leak_jet_boundary_payload
from brambhand.propulsion.slosh_coupling import build_slosh_boundary_payload
from brambhand.structures.fracture import (
    FractureInitiationParams,
    evaluate_fracture_initiation,
    propagate_damage_effects,
)


class _ExchangeDrivenFluidProvider:
    def __init__(self, base_loads: tuple[FluidBoundaryLoad, ...], stiffness_npm: float) -> None:
        self._base_by_id = {load.interface_id: load for load in base_loads}
        self._stiffness_npm = stiffness_npm

    def evaluate(
        self,
        interface_displacements: tuple[InterfaceDisplacement, ...],
    ) -> tuple[FluidBoundaryLoad, ...]:
        displacement_x_by_id = {
            item.interface_id: item.displacement_body_m.x for item in interface_displacements
        }
        return tuple(
            FluidBoundaryLoad(
                interface_id=interface_id,
                force_body_n=Vector3(
                    base.force_body_n.x
                    - self._stiffness_npm * displacement_x_by_id.get(interface_id, 0.0),
                    base.force_body_n.y,
                    base.force_body_n.z,
                ),
                torque_body_nm=base.torque_body_nm,
                mass_flow_kgps=base.mass_flow_kgps,
                temperature_k=base.temperature_k,
            )
            for interface_id, base in sorted(self._base_by_id.items())
        )


class _LinearStructuralProvider(StructuralBoundaryProvider):
    def __init__(self, compliance_mpn: float) -> None:
        self._compliance_mpn = compliance_mpn

    def evaluate(
        self,
        fluid_loads: tuple[FluidBoundaryLoad, ...],
    ) -> tuple[InterfaceDisplacement, ...]:
        return tuple(
            InterfaceDisplacement(
                interface_id=load.interface_id,
                displacement_body_m=Vector3(self._compliance_mpn * load.force_body_n.x, 0.0, 0.0),
            )
            for load in fluid_loads
        )


def test_integrated_chain_fracture_to_fsi_to_6dof_response() -> None:
    # fracture / damage progression
    damage_states = evaluate_fracture_initiation(
        von_mises_pa_by_element=(120.0, 260.0),
        params=FractureInitiationParams(yield_von_mises_pa=100.0, ultimate_von_mises_pa=200.0),
    )
    damage = propagate_damage_effects(damage_states, leak_path_damage_threshold=0.8)
    assert damage.leak_path_created is True

    # topology update from fracture split
    before = create_assembly_topology_state(("booster", "payload"))
    attached, _ = apply_docking_attach_transition(
        before,
        interface_id="dock_if",
        body_a_id="booster",
        body_b_id="payload",
    )
    after, _ = apply_fracture_split_transition(
        attached,
        parent_body_id="booster",
        child_labels=("frag_a", "frag_b"),
    )
    topology = build_topology_transition_payload(
        transition_id="tx-frac-001",
        transition_kind=FaultTransitionKind.FRACTURE_SPLIT,
        before_state=attached,
        after_state=after,
        provenance={"source": "integrated_chain_test"},
    )

    # leak + slosh boundary updates
    leak_payload = build_leak_jet_boundary_payload(
        leak_jet=LeakJetState(
            mass_flow_kgps=0.25,
            exit_velocity_mps=120.0,
            jet_temperature_k=350.0,
            reaction_force_body_n=Vector3(80.0, 0.0, 0.0),
            reaction_torque_body_nm=Vector3(0.0, 5.0, 0.0),
        ),
        interface_id="tank_A",
    )
    slosh_payload = build_slosh_boundary_payload(
        SloshLoad(
            force_body_n=Vector3(20.0, 10.0, 0.0),
            torque_body_nm=Vector3(0.0, 2.0, 0.0),
            com_offset_body_m=Vector3(0.05, 0.0, 0.0),
        ),
        interface_id="tank_A",
    )

    exchange = build_fsi_boundary_exchange_contract(
        topology_transition=topology,
        leak_jet_payloads=(leak_payload,),
        slosh_payloads=(slosh_payload,),
    )
    assert len(exchange.fluid_boundary_loads) == 1

    # FSI residual convergence with fallback policy
    controller_result = run_fsi_coupling_with_controller(
        fluid_provider=_ExchangeDrivenFluidProvider(
            base_loads=exchange.fluid_boundary_loads,
            stiffness_npm=0.6,
        ),
        structural_provider=_LinearStructuralProvider(compliance_mpn=0.01),
        policy=FSICouplingControllerPolicy(
            nominal_iteration_budget=1,
            nominal_residual_threshold=1e-12,
            fallback_enabled=True,
            fallback_iteration_budget=20,
            fallback_residual_threshold=1e-5,
            fallback_relaxation_factor=0.8,
        ),
    )
    assert controller_result.converged is True
    assert controller_result.mode in ("nominal", "fallback")

    total_force = Vector3(0.0, 0.0, 0.0)
    total_torque = Vector3(0.0, 0.0, 0.0)
    for load in controller_result.active_result.fluid_loads:
        total_force = total_force + load.force_body_n
        total_torque = total_torque + load.torque_body_nm

    # 6-DOF response
    next_state = integrate_rigid_body_euler(
        state=RigidBody6DoFState(
            position_m=Vector3(0.0, 0.0, 0.0),
            velocity_mps=Vector3(0.0, 0.0, 0.0),
            attitude=UnitQuaternion(1.0, 0.0, 0.0, 0.0),
            angular_velocity_radps=Vector3(0.0, 0.0, 0.0),
        ),
        props=RigidBodyProperties(mass_kg=100.0, inertia_diag_kgm2=(50.0, 50.0, 50.0)),
        wrench=Wrench(force_n=total_force, torque_nm=total_torque),
        dt_s=0.1,
        wrench_frame=WrenchFrame.BODY,
    )

    assert next_state.velocity_mps.norm() > 0.0
    assert next_state.angular_velocity_radps.norm() > 0.0
