"""Initial FSI coupling policy for partitioned baseline and monolithic escalation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from brambhand.coupling.controller import FSICouplingControllerResult
from brambhand.coupling.exchange_contracts import FSIBoundaryExchangeContract

FSICouplingStrategy = Literal["partitioned", "monolithic"]


@dataclass(frozen=True)
class FSICouplingPolicyThresholds:
    """Explicit thresholds controlling partitioned->monolithic escalation."""

    max_partitioned_iterations: int
    max_partitioned_final_residual: float
    max_partitioned_total_mass_flow_kgps: float
    monolithic_transition_kinds: tuple[str, ...] = ("split", "fracture_split")

    def __post_init__(self) -> None:
        if self.max_partitioned_iterations <= 0:
            raise ValueError("max_partitioned_iterations must be positive.")
        if self.max_partitioned_final_residual < 0.0:
            raise ValueError("max_partitioned_final_residual cannot be negative.")
        if self.max_partitioned_total_mass_flow_kgps < 0.0:
            raise ValueError("max_partitioned_total_mass_flow_kgps cannot be negative.")
        if any(not kind for kind in self.monolithic_transition_kinds):
            raise ValueError("monolithic_transition_kinds entries must be non-empty.")


@dataclass(frozen=True)
class FSICouplingPolicyDecision:
    """Policy decision with deterministic escalation rationale."""

    strategy: FSICouplingStrategy
    reason: str
    final_residual: float
    total_mass_flow_kgps: float
    iterations_used: int


def _final_residual(controller_result: FSICouplingControllerResult) -> float:
    history = controller_result.active_result.residual_history
    if not history:
        return 0.0
    return history[-1].residual


def _total_mass_flow_kgps(exchange: FSIBoundaryExchangeContract) -> float:
    return sum(load.mass_flow_kgps for load in exchange.fluid_boundary_loads)


def decide_fsi_coupling_strategy(
    *,
    controller_result: FSICouplingControllerResult,
    exchange: FSIBoundaryExchangeContract,
    thresholds: FSICouplingPolicyThresholds,
) -> FSICouplingPolicyDecision:
    """Select partitioned baseline or monolithic escalation from explicit criteria."""
    final_residual = _final_residual(controller_result)
    total_mass_flow = _total_mass_flow_kgps(exchange)
    iterations_used = controller_result.total_iterations_used

    if exchange.topology_transition is not None and (
        exchange.topology_transition.transition_kind in thresholds.monolithic_transition_kinds
    ):
        return FSICouplingPolicyDecision(
            strategy="monolithic",
            reason="topology_transition_requires_monolithic",
            final_residual=final_residual,
            total_mass_flow_kgps=total_mass_flow,
            iterations_used=iterations_used,
        )

    if not controller_result.converged:
        return FSICouplingPolicyDecision(
            strategy="monolithic",
            reason="partitioned_not_converged",
            final_residual=final_residual,
            total_mass_flow_kgps=total_mass_flow,
            iterations_used=iterations_used,
        )

    if final_residual > thresholds.max_partitioned_final_residual:
        return FSICouplingPolicyDecision(
            strategy="monolithic",
            reason="residual_exceeds_partitioned_threshold",
            final_residual=final_residual,
            total_mass_flow_kgps=total_mass_flow,
            iterations_used=iterations_used,
        )

    if iterations_used > thresholds.max_partitioned_iterations:
        return FSICouplingPolicyDecision(
            strategy="monolithic",
            reason="iterations_exceed_partitioned_budget",
            final_residual=final_residual,
            total_mass_flow_kgps=total_mass_flow,
            iterations_used=iterations_used,
        )

    if total_mass_flow > thresholds.max_partitioned_total_mass_flow_kgps:
        return FSICouplingPolicyDecision(
            strategy="monolithic",
            reason="mass_flow_exceeds_partitioned_threshold",
            final_residual=final_residual,
            total_mass_flow_kgps=total_mass_flow,
            iterations_used=iterations_used,
        )

    return FSICouplingPolicyDecision(
        strategy="partitioned",
        reason="partitioned_within_thresholds",
        final_residual=final_residual,
        total_mass_flow_kgps=total_mass_flow,
        iterations_used=iterations_used,
    )
