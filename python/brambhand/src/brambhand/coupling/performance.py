"""FSI coupled-stability benchmark helpers (including failure/recovery accounting)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from brambhand.coupling.controller import FSICouplingControllerResult


@dataclass(frozen=True)
class FSICoupledStabilityBenchmarkResult:
    """Summary metrics for repeated FSI controller benchmark runs."""

    repeats: int
    converged_count: int
    fallback_converged_count: int
    failure_count: int
    failure_recovery_count: int
    p50_iterations_used: float
    p95_iterations_used: float
    max_final_residual: float


def _percentile(samples: list[float], p: float) -> float:
    if not samples:
        raise ValueError("samples cannot be empty.")
    ordered = sorted(samples)
    idx = int(round((len(ordered) - 1) * p))
    return ordered[max(0, min(idx, len(ordered) - 1))]


def _final_residual(result: FSICouplingControllerResult) -> float:
    history = result.active_result.residual_history
    if not history:
        return 0.0
    return history[-1].residual


def benchmark_fsi_coupled_stability(
    run_case: Callable[[int], FSICouplingControllerResult],
    repeats: int = 10,
) -> FSICoupledStabilityBenchmarkResult:
    """Benchmark repeated FSI runs and summarize stability/failure-recovery behavior."""
    if repeats <= 0:
        raise ValueError("repeats must be positive.")

    iterations: list[float] = []
    final_residuals: list[float] = []
    converged_count = 0
    fallback_converged_count = 0
    failure_count = 0
    failure_recovery_count = 0
    previous_failed = False

    for run_index in range(repeats):
        result = run_case(run_index)
        iterations.append(float(result.total_iterations_used))
        final_residual = _final_residual(result)
        final_residuals.append(final_residual)

        if result.converged:
            converged_count += 1
            if result.mode == "fallback":
                fallback_converged_count += 1
            if previous_failed:
                failure_recovery_count += 1
            previous_failed = False
        else:
            failure_count += 1
            previous_failed = True

    return FSICoupledStabilityBenchmarkResult(
        repeats=repeats,
        converged_count=converged_count,
        fallback_converged_count=fallback_converged_count,
        failure_count=failure_count,
        failure_recovery_count=failure_recovery_count,
        p50_iterations_used=_percentile(iterations, 0.50),
        p95_iterations_used=_percentile(iterations, 0.95),
        max_final_residual=max(final_residuals),
    )
