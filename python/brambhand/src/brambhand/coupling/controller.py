"""FSI coupling controller with iteration budgets, thresholds, and fallback policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from brambhand.coupling.fsi_coupler import (
    FluidBoundaryProvider,
    FSICouplingParams,
    FSICouplingResult,
    InterfaceDisplacement,
    StructuralBoundaryProvider,
    couple_fsi_two_way,
)

FSIControllerMode = Literal["nominal", "fallback", "failed"]


@dataclass(frozen=True)
class FSICouplingControllerPolicy:
    """Controller policy for nominal/fallback coupling attempts."""

    nominal_iteration_budget: int
    nominal_residual_threshold: float
    nominal_relaxation_factor: float = 1.0
    fallback_enabled: bool = True
    fallback_iteration_budget: int = 8
    fallback_residual_threshold: float = 1e-4
    fallback_relaxation_factor: float = 0.5

    def __post_init__(self) -> None:
        if self.nominal_iteration_budget <= 0:
            raise ValueError("nominal_iteration_budget must be positive.")
        if self.nominal_residual_threshold < 0.0:
            raise ValueError("nominal_residual_threshold cannot be negative.")
        if self.nominal_relaxation_factor <= 0.0 or self.nominal_relaxation_factor > 1.0:
            raise ValueError("nominal_relaxation_factor must be in (0, 1].")
        if self.fallback_iteration_budget <= 0:
            raise ValueError("fallback_iteration_budget must be positive.")
        if self.fallback_residual_threshold < 0.0:
            raise ValueError("fallback_residual_threshold cannot be negative.")
        if self.fallback_relaxation_factor <= 0.0 or self.fallback_relaxation_factor > 1.0:
            raise ValueError("fallback_relaxation_factor must be in (0, 1].")


@dataclass(frozen=True)
class FSICouplingControllerResult:
    """Controller outcome with nominal/fallback attempt provenance."""

    mode: FSIControllerMode
    converged: bool
    termination_reason: str
    total_iterations_used: int
    active_result: FSICouplingResult
    nominal_result: FSICouplingResult
    fallback_result: FSICouplingResult | None


def run_fsi_coupling_with_controller(
    fluid_provider: FluidBoundaryProvider,
    structural_provider: StructuralBoundaryProvider,
    policy: FSICouplingControllerPolicy,
    initial_displacements: tuple[InterfaceDisplacement, ...] = (),
) -> FSICouplingControllerResult:
    """Run nominal FSI coupling attempt and optional fallback policy."""
    nominal_result = couple_fsi_two_way(
        fluid_provider=fluid_provider,
        structural_provider=structural_provider,
        params=FSICouplingParams(
            max_iterations=policy.nominal_iteration_budget,
            residual_tolerance=policy.nominal_residual_threshold,
            relaxation_factor=policy.nominal_relaxation_factor,
        ),
        initial_displacements=initial_displacements,
    )

    if nominal_result.converged:
        return FSICouplingControllerResult(
            mode="nominal",
            converged=True,
            termination_reason="nominal_converged",
            total_iterations_used=nominal_result.iterations_used,
            active_result=nominal_result,
            nominal_result=nominal_result,
            fallback_result=None,
        )

    if not policy.fallback_enabled:
        return FSICouplingControllerResult(
            mode="failed",
            converged=False,
            termination_reason="nominal_not_converged_no_fallback",
            total_iterations_used=nominal_result.iterations_used,
            active_result=nominal_result,
            nominal_result=nominal_result,
            fallback_result=None,
        )

    fallback_result = couple_fsi_two_way(
        fluid_provider=fluid_provider,
        structural_provider=structural_provider,
        params=FSICouplingParams(
            max_iterations=policy.fallback_iteration_budget,
            residual_tolerance=policy.fallback_residual_threshold,
            relaxation_factor=policy.fallback_relaxation_factor,
        ),
        initial_displacements=nominal_result.interface_displacements,
    )
    total_iterations_used = nominal_result.iterations_used + fallback_result.iterations_used

    if fallback_result.converged:
        return FSICouplingControllerResult(
            mode="fallback",
            converged=True,
            termination_reason="fallback_converged",
            total_iterations_used=total_iterations_used,
            active_result=fallback_result,
            nominal_result=nominal_result,
            fallback_result=fallback_result,
        )

    return FSICouplingControllerResult(
        mode="failed",
        converged=False,
        termination_reason="fallback_not_converged",
        total_iterations_used=total_iterations_used,
        active_result=fallback_result,
        nominal_result=nominal_result,
        fallback_result=fallback_result,
    )
