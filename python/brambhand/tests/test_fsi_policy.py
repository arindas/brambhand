from brambhand.coupling.controller import FSICouplingControllerResult
from brambhand.coupling.exchange_contracts import build_fsi_boundary_exchange_contract
from brambhand.coupling.fsi_coupler import (
    FSICouplingIterationTelemetry,
    FSICouplingResult,
)
from brambhand.coupling.policy import (
    FSICouplingPolicyThresholds,
    decide_fsi_coupling_strategy,
)
from brambhand.fluid.contracts import (
    LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
    TOPOLOGY_TRANSITION_PAYLOAD_SCHEMA_VERSION,
    LeakJetBoundaryPayload,
    TopologyTransitionPayload,
)
from brambhand.physics.vector import Vector3


def _controller_result(
    *,
    converged: bool,
    iterations_used: int,
    residual: float,
) -> FSICouplingControllerResult:
    result = FSICouplingResult(
        converged=converged,
        termination_reason="converged" if converged else "max_iterations",
        iterations_used=iterations_used,
        residual_history=(
            FSICouplingIterationTelemetry(
                iteration=iterations_used,
                residual=residual,
                interface_count=1,
            ),
        ),
        fluid_loads=(),
        interface_displacements=(),
    )
    return FSICouplingControllerResult(
        mode="nominal" if converged else "failed",
        converged=converged,
        termination_reason="nominal_converged" if converged else "fallback_not_converged",
        total_iterations_used=iterations_used,
        active_result=result,
        nominal_result=result,
        fallback_result=None,
    )


def test_fsi_policy_keeps_partitioned_strategy_within_thresholds() -> None:
    controller_result = _controller_result(converged=True, iterations_used=4, residual=1e-5)
    exchange = build_fsi_boundary_exchange_contract(
        topology_transition=None,
        leak_jet_payloads=(),
        slosh_payloads=(),
    )

    decision = decide_fsi_coupling_strategy(
        controller_result=controller_result,
        exchange=exchange,
        thresholds=FSICouplingPolicyThresholds(
            max_partitioned_iterations=10,
            max_partitioned_final_residual=1e-4,
            max_partitioned_total_mass_flow_kgps=1.0,
        ),
    )

    assert decision.strategy == "partitioned"
    assert decision.reason == "partitioned_within_thresholds"


def test_fsi_policy_escalates_on_split_topology_transition() -> None:
    controller_result = _controller_result(converged=True, iterations_used=3, residual=1e-6)
    topology = TopologyTransitionPayload(
        transition_id="tx-10",
        schema_version=TOPOLOGY_TRANSITION_PAYLOAD_SCHEMA_VERSION,
        transition_kind="split",
        revision=1,
        body_ids_before=("a",),
        body_ids_after=("a_1", "a_2"),
        interface_ids_after=(),
        interface_endpoints_after=(),
        provenance={"source": "test"},
    )
    exchange = build_fsi_boundary_exchange_contract(
        topology_transition=topology,
        leak_jet_payloads=(),
        slosh_payloads=(),
    )

    decision = decide_fsi_coupling_strategy(
        controller_result=controller_result,
        exchange=exchange,
        thresholds=FSICouplingPolicyThresholds(
            max_partitioned_iterations=10,
            max_partitioned_final_residual=1e-4,
            max_partitioned_total_mass_flow_kgps=1.0,
        ),
    )

    assert decision.strategy == "monolithic"
    assert decision.reason == "topology_transition_requires_monolithic"


def test_fsi_policy_escalates_when_partitioned_not_converged() -> None:
    controller_result = _controller_result(converged=False, iterations_used=8, residual=1e-2)
    exchange = build_fsi_boundary_exchange_contract(
        topology_transition=None,
        leak_jet_payloads=(),
        slosh_payloads=(),
    )

    decision = decide_fsi_coupling_strategy(
        controller_result=controller_result,
        exchange=exchange,
        thresholds=FSICouplingPolicyThresholds(
            max_partitioned_iterations=10,
            max_partitioned_final_residual=1e-3,
            max_partitioned_total_mass_flow_kgps=1.0,
        ),
    )

    assert decision.strategy == "monolithic"
    assert decision.reason == "partitioned_not_converged"


def test_fsi_policy_escalates_when_mass_flow_exceeds_threshold() -> None:
    controller_result = _controller_result(converged=True, iterations_used=3, residual=1e-6)
    leak = LeakJetBoundaryPayload(
        interface_id="leak_A",
        schema_version=LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION,
        reaction_force_body_n=Vector3(1.0, 0.0, 0.0),
        reaction_torque_body_nm=Vector3(0.0, 0.0, 0.0),
        mass_flow_kgps=0.5,
        jet_temperature_k=350.0,
    )
    exchange = build_fsi_boundary_exchange_contract(
        topology_transition=None,
        leak_jet_payloads=(leak,),
        slosh_payloads=(),
    )

    decision = decide_fsi_coupling_strategy(
        controller_result=controller_result,
        exchange=exchange,
        thresholds=FSICouplingPolicyThresholds(
            max_partitioned_iterations=10,
            max_partitioned_final_residual=1e-4,
            max_partitioned_total_mass_flow_kgps=0.1,
        ),
    )

    assert decision.strategy == "monolithic"
    assert decision.reason == "mass_flow_exceeds_partitioned_threshold"


def test_fsi_policy_threshold_validation_guards() -> None:
    for kwargs in (
        dict(
            max_partitioned_iterations=0,
            max_partitioned_final_residual=1e-4,
            max_partitioned_total_mass_flow_kgps=1.0,
        ),
        dict(
            max_partitioned_iterations=1,
            max_partitioned_final_residual=-1.0,
            max_partitioned_total_mass_flow_kgps=1.0,
        ),
        dict(
            max_partitioned_iterations=1,
            max_partitioned_final_residual=1e-4,
            max_partitioned_total_mass_flow_kgps=-1.0,
        ),
        dict(
            max_partitioned_iterations=1,
            max_partitioned_final_residual=1e-4,
            max_partitioned_total_mass_flow_kgps=1.0,
            monolithic_transition_kinds=("",),
        ),
    ):
        try:
            FSICouplingPolicyThresholds(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected FSICouplingPolicyThresholds validation failure")
