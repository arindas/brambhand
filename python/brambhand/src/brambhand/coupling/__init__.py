"""Coupling contracts and solvers across physics domains."""

from brambhand.coupling.controller import (
    FSIControllerMode,
    FSICouplingControllerPolicy,
    FSICouplingControllerResult,
    run_fsi_coupling_with_controller,
)
from brambhand.coupling.exchange_contracts import (
    FSI_BOUNDARY_EXCHANGE_SCHEMA_VERSION,
    FSIBoundaryExchangeContract,
    build_fsi_boundary_exchange_contract,
)
from brambhand.coupling.fsi_coupler import (
    FSICouplingIterationTelemetry,
    FSICouplingParams,
    FSICouplingResult,
    InterfaceDisplacement,
    couple_fsi_two_way,
)
from brambhand.coupling.policy import (
    FSICouplingPolicyDecision,
    FSICouplingPolicyThresholds,
    FSICouplingStrategy,
    decide_fsi_coupling_strategy,
)
from brambhand.coupling.telemetry import (
    FSI_TELEMETRY_SCHEMA_VERSION,
    FSICouplingConvergenceDiagnostics,
    FSICouplingTelemetryChannels,
    ResidualTelemetryPoint,
    build_fsi_convergence_diagnostics,
)

__all__ = [
    "FSI_BOUNDARY_EXCHANGE_SCHEMA_VERSION",
    "FSIBoundaryExchangeContract",
    "FSICouplingControllerPolicy",
    "FSICouplingConvergenceDiagnostics",
    "FSICouplingControllerResult",
    "FSICouplingIterationTelemetry",
    "FSICouplingParams",
    "FSICouplingPolicyDecision",
    "FSICouplingPolicyThresholds",
    "FSICouplingResult",
    "FSICouplingStrategy",
    "FSICouplingTelemetryChannels",
    "FSI_TELEMETRY_SCHEMA_VERSION",
    "FSIControllerMode",
    "InterfaceDisplacement",
    "ResidualTelemetryPoint",
    "build_fsi_boundary_exchange_contract",
    "build_fsi_convergence_diagnostics",
    "couple_fsi_two_way",
    "decide_fsi_coupling_strategy",
    "run_fsi_coupling_with_controller",
]
