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

__all__ = [
    "FSI_BOUNDARY_EXCHANGE_SCHEMA_VERSION",
    "FSIBoundaryExchangeContract",
    "FSICouplingControllerPolicy",
    "FSICouplingControllerResult",
    "FSICouplingIterationTelemetry",
    "FSICouplingParams",
    "FSICouplingResult",
    "FSIControllerMode",
    "InterfaceDisplacement",
    "build_fsi_boundary_exchange_contract",
    "couple_fsi_two_way",
    "run_fsi_coupling_with_controller",
]
