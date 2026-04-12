"""Convergence diagnostics and telemetry-channel helpers for FSI coupling."""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.coupling.controller import FSICouplingControllerResult

FSI_TELEMETRY_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ResidualTelemetryPoint:
    """One residual sample in deterministic coupling-iteration order."""

    iteration: int
    residual: float


@dataclass(frozen=True)
class FSICouplingTelemetryChannels:
    """Named telemetry channels emitted for FSI convergence diagnostics."""

    residual_history: tuple[ResidualTelemetryPoint, ...]
    iteration_budget: tuple[int, int]
    convergence_flags: tuple[bool, bool]
    mode_and_reason: tuple[str, str]


@dataclass(frozen=True)
class FSICouplingConvergenceDiagnostics:
    """Versioned convergence diagnostics payload for FSI controller runs."""

    schema_version: int
    final_residual: float
    iterations_used: int
    converged: bool
    channels: FSICouplingTelemetryChannels

    def __post_init__(self) -> None:
        if self.schema_version != FSI_TELEMETRY_SCHEMA_VERSION:
            raise ValueError("Unsupported FSI telemetry schema_version.")
        if self.final_residual < 0.0:
            raise ValueError("final_residual cannot be negative.")
        if self.iterations_used < 0:
            raise ValueError("iterations_used cannot be negative.")


def build_fsi_convergence_diagnostics(
    controller_result: FSICouplingControllerResult,
) -> FSICouplingConvergenceDiagnostics:
    """Build versioned convergence diagnostics + telemetry channels from controller result."""
    residual_history = tuple(
        ResidualTelemetryPoint(
            iteration=item.iteration,
            residual=item.residual,
        )
        for item in controller_result.active_result.residual_history
    )
    final_residual = 0.0 if not residual_history else residual_history[-1].residual
    active_iterations = controller_result.active_result.iterations_used
    nominal_budget = controller_result.nominal_result.iterations_used

    return FSICouplingConvergenceDiagnostics(
        schema_version=FSI_TELEMETRY_SCHEMA_VERSION,
        final_residual=final_residual,
        iterations_used=controller_result.total_iterations_used,
        converged=controller_result.converged,
        channels=FSICouplingTelemetryChannels(
            residual_history=residual_history,
            iteration_budget=(active_iterations, nominal_budget),
            convergence_flags=(
                controller_result.nominal_result.converged,
                controller_result.fallback_result.converged
                if controller_result.fallback_result is not None
                else False,
            ),
            mode_and_reason=(controller_result.mode, controller_result.termination_reason),
        ),
    )
