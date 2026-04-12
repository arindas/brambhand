from brambhand.coupling.exchange_contracts import (
    FSI_BOUNDARY_EXCHANGE_SCHEMA_VERSION,
    FSIBoundaryExchangeContract,
    build_fsi_boundary_exchange_contract,
)
from brambhand.fluid.contracts import (
    LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
    SLOSH_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
    TOPOLOGY_TRANSITION_SCHEMA_VERSION,
    LeakJetBoundaryPayload,
    SloshBoundaryPayload,
    TopologyTransitionKind,
)
from brambhand.mission.assembly_topology import (
    AssemblyTopologyState,
    AttachmentInterface,
    build_topology_transition_payload,
)
from brambhand.physics.vector import Vector3


def test_fsi_exchange_contract_integrates_topology_leak_and_slosh_payloads() -> None:
    before = AssemblyTopologyState(
        body_ids=("bus", "module"),
        interfaces=(
            AttachmentInterface(
                interface_id="dock_1",
                body_a_id="bus",
                body_b_id="module",
                interface_kind="docking_latch",
            ),
        ),
        revision=1,
    )
    after = AssemblyTopologyState(body_ids=("bus", "module"), interfaces=(), revision=2)
    topology = build_topology_transition_payload(
        transition_id="tx-1",
        transition_kind=TopologyTransitionKind.DETACH,
        before_state=before,
        after_state=after,
        provenance={"source": "test"},
    )

    leak = LeakJetBoundaryPayload(
        interface_id="tank_A",
        schema_version=LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
        reaction_force_body_n=Vector3(10.0, 0.0, 0.0),
        reaction_torque_body_nm=Vector3(1.0, 0.0, 0.0),
        mass_flow_kgps=0.2,
        jet_temperature_k=400.0,
    )
    slosh = SloshBoundaryPayload(
        interface_id="tank_A",
        schema_version=SLOSH_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
        slosh_force_body_n=Vector3(-2.0, 3.0, 0.0),
        slosh_torque_body_nm=Vector3(0.0, 0.5, 0.0),
        com_offset_body_m=Vector3(0.1, 0.0, 0.0),
        reference_temperature_k=300.0,
    )

    contract = build_fsi_boundary_exchange_contract(
        topology_transition=topology,
        leak_jet_payloads=(leak,),
        slosh_payloads=(slosh,),
    )

    assert contract.schema_version == FSI_BOUNDARY_EXCHANGE_SCHEMA_VERSION
    assert contract.topology_transition is not None
    assert contract.topology_transition.schema_version == TOPOLOGY_TRANSITION_SCHEMA_VERSION
    assert tuple(item.interface_id for item in contract.leak_jet_payloads) == ("tank_A",)
    assert tuple(item.interface_id for item in contract.slosh_payloads) == ("tank_A",)

    assert len(contract.fluid_boundary_loads) == 1
    aggregated = contract.fluid_boundary_loads[0]
    assert aggregated.interface_id == "tank_A"
    assert aggregated.force_body_n == Vector3(8.0, 3.0, 0.0)
    assert aggregated.torque_body_nm == Vector3(1.0, 0.5, 0.0)
    assert aggregated.mass_flow_kgps == 0.2
    assert aggregated.temperature_k == 400.0


def test_fsi_exchange_contract_load_aggregation_is_deterministic_by_interface_id() -> None:
    leak_b = LeakJetBoundaryPayload(
        interface_id="b_iface",
        schema_version=LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
        reaction_force_body_n=Vector3(1.0, 0.0, 0.0),
        reaction_torque_body_nm=Vector3(0.0, 0.0, 0.0),
        mass_flow_kgps=0.1,
        jet_temperature_k=330.0,
    )
    leak_a = LeakJetBoundaryPayload(
        interface_id="a_iface",
        schema_version=LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
        reaction_force_body_n=Vector3(2.0, 0.0, 0.0),
        reaction_torque_body_nm=Vector3(0.0, 0.0, 0.0),
        mass_flow_kgps=0.1,
        jet_temperature_k=350.0,
    )

    contract = build_fsi_boundary_exchange_contract(
        topology_transition=None,
        leak_jet_payloads=(leak_b, leak_a),
        slosh_payloads=(),
    )

    assert tuple(load.interface_id for load in contract.fluid_boundary_loads) == (
        "a_iface",
        "b_iface",
    )


def test_fsi_exchange_contract_rejects_unsupported_schema_version() -> None:
    try:
        FSIBoundaryExchangeContract(
            schema_version=999,
            topology_transition=None,
            leak_jet_payloads=(),
            slosh_payloads=(),
            fluid_boundary_loads=(),
        )
    except ValueError as exc:
        assert "schema_version" in str(exc)
    else:
        raise AssertionError("Expected FSI exchange schema-version validation failure")
