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
from brambhand.propulsion.leak_jet_coupling import propagate_leak_jet_to_rigid_body
from brambhand.propulsion.leakage_model import (
    CompartmentState,
    LeakagePath,
    apply_leakage,
)
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
    "propagate_leak_jet_to_rigid_body",
    "LineState",
    "ChamberThrustCouplingParams",
    "NozzleGeometryCorrection",
    "NozzleParams",
    "TankState",
    "ThrustEstimate",
    "ValveState",
    "apply_leakage",
    "estimate_nozzle_thrust",
    "evaluate_leak_jet",
    "estimate_nozzle_thrust_from_chamber_flow",
    "step_chamber_flow",
    "step_combustion_chamber",
    "step_fluid_network",
]
