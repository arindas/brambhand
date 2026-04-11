"""R2 propulsion domain primitives (fluids, combustion, thrust, leakage)."""

from brambhand.fluid.reduced.chamber_flow import (
    ChamberFlowDiagnostics,
    ChamberFlowParams,
    ChamberFlowState,
    ChamberFlowStepResult,
    step_chamber_flow,
)
from brambhand.fluid.reduced.leak_jet_dynamics import (
    LeakJetPath,
    LeakJetState,
    evaluate_leak_jet,
)
from brambhand.fluid.reduced.slosh_model import (
    SloshFallbackParams,
    SloshGeometryDescriptor,
    SloshLoad,
    SloshModelParams,
    SloshState,
    SloshStepResult,
    derive_slosh_model_params,
    step_slosh_state,
)
from brambhand.propulsion.combustion_model import (
    CombustionChamberParams,
    CombustionChamberState,
    step_combustion_chamber,
)
from brambhand.propulsion.fluid_network import (
    FluidNetworkState,
    LineState,
    TankState,
    ValveState,
    step_fluid_network,
)
from brambhand.propulsion.leak_jet_coupling import (
    build_leak_jet_boundary_payload,
    propagate_leak_jet_to_rigid_body,
)
from brambhand.propulsion.leakage_model import (
    CompartmentState,
    LeakagePath,
    apply_leakage,
)
from brambhand.propulsion.performance import (
    PropulsionLatencyBenchmarkResult,
    ReducedOrderFallbackMode,
    SloshLatencyBenchmarkResult,
    apply_slosh_degraded_mode,
    benchmark_reduced_order_propulsion_latency,
    benchmark_reduced_order_slosh_latency,
    cadence_guard_mode,
)
from brambhand.propulsion.slosh_6dof_coupling import (
    SloshRigidBodyCouplingResult,
    propagate_slosh_to_rigid_body,
)
from brambhand.propulsion.slosh_coupling import build_slosh_boundary_payload
from brambhand.propulsion.thrust_estimator import (
    ChamberThrustCouplingParams,
    NozzleGeometryCorrection,
    NozzleParams,
    ThrustEstimate,
    estimate_nozzle_thrust,
    estimate_nozzle_thrust_from_chamber_flow,
)

__all__ = [
    "ChamberFlowDiagnostics",
    "ChamberFlowParams",
    "ChamberFlowState",
    "ChamberFlowStepResult",
    "CombustionChamberParams",
    "CombustionChamberState",
    "CompartmentState",
    "FluidNetworkState",
    "LeakagePath",
    "LeakJetPath",
    "LeakJetState",
    "build_leak_jet_boundary_payload",
    "build_slosh_boundary_payload",
    "propagate_leak_jet_to_rigid_body",
    "LineState",
    "ChamberThrustCouplingParams",
    "NozzleGeometryCorrection",
    "PropulsionLatencyBenchmarkResult",
    "ReducedOrderFallbackMode",
    "SloshLatencyBenchmarkResult",
    "SloshRigidBodyCouplingResult",
    "NozzleParams",
    "SloshFallbackParams",
    "SloshGeometryDescriptor",
    "SloshLoad",
    "SloshModelParams",
    "SloshState",
    "SloshStepResult",
    "TankState",
    "ThrustEstimate",
    "ValveState",
    "apply_leakage",
    "apply_slosh_degraded_mode",
    "benchmark_reduced_order_propulsion_latency",
    "benchmark_reduced_order_slosh_latency",
    "cadence_guard_mode",
    "estimate_nozzle_thrust",
    "derive_slosh_model_params",
    "evaluate_leak_jet",
    "propagate_slosh_to_rigid_body",
    "step_slosh_state",
    "estimate_nozzle_thrust_from_chamber_flow",
    "step_chamber_flow",
    "step_combustion_chamber",
    "step_fluid_network",
]
