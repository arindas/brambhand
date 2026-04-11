"""Propulsion reduced-order latency/cadence benchmark helpers."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

from brambhand.fluid.reduced.chamber_flow import (
    ChamberFlowParams,
    ChamberFlowState,
    step_chamber_flow,
)
from brambhand.fluid.reduced.leak_jet_dynamics import LeakJetPath, evaluate_leak_jet
from brambhand.fluid.reduced.slosh_model import (
    SloshLoad,
    SloshModelParams,
    SloshState,
    step_slosh_state,
)
from brambhand.physics.vector import Vector3


class ReducedOrderFallbackMode(StrEnum):
    """Cadence-guard mode for reduced-order propulsion updates."""

    NOMINAL = "nominal"
    REDUCED_ORDER_GUARD_ACTIVE = "reduced_order_guard_active"


@dataclass(frozen=True)
class PropulsionLatencyBenchmarkResult:
    """Latency summary for reduced-order chamber/leak-jet update path."""

    repeats: int
    p50_step_latency_s: float
    p95_step_latency_s: float
    operational_budget_s: float
    fallback_trigger_count: int


@dataclass(frozen=True)
class SloshLatencyBenchmarkResult:
    """Latency summary for reduced-order slosh update path."""

    repeats: int
    p50_step_latency_s: float
    p95_step_latency_s: float
    operational_budget_s: float
    degraded_mode_trigger_count: int


def _percentile(samples: list[float], p: float) -> float:
    if not samples:
        raise ValueError("samples cannot be empty.")
    ordered = sorted(samples)
    idx = int(round((len(ordered) - 1) * p))
    return ordered[max(0, min(idx, len(ordered) - 1))]


def cadence_guard_mode(
    step_latency_s: float,
    operational_budget_s: float,
) -> ReducedOrderFallbackMode:
    """Return cadence-guard mode for one reduced-order propulsion step."""
    if operational_budget_s <= 0.0:
        raise ValueError("operational_budget_s must be positive.")
    if step_latency_s < 0.0:
        raise ValueError("step_latency_s cannot be negative.")
    if step_latency_s > operational_budget_s:
        return ReducedOrderFallbackMode.REDUCED_ORDER_GUARD_ACTIVE
    return ReducedOrderFallbackMode.NOMINAL


def apply_slosh_degraded_mode(
    slosh_load: SloshLoad,
    mode: ReducedOrderFallbackMode,
) -> SloshLoad:
    """Apply explicit degraded-mode control policy for slosh coupling loads."""
    if mode is ReducedOrderFallbackMode.NOMINAL:
        return slosh_load
    return SloshLoad(
        force_body_n=slosh_load.force_body_n,
        torque_body_nm=Vector3(0.0, 0.0, 0.0),
        com_offset_body_m=Vector3(0.0, 0.0, 0.0),
    )


def benchmark_reduced_order_propulsion_latency(
    chamber_state: ChamberFlowState,
    chamber_params: ChamberFlowParams,
    inflow_fuel_kgps: float,
    inflow_oxidizer_kgps: float,
    throat_outflow_kgps: float,
    leak_path: LeakJetPath,
    compartment_pressure_pa: float,
    compartment_temperature_k: float,
    ambient_temperature_k: float,
    dt_s: float,
    repeats: int = 10,
    operational_budget_s: float = 0.010,
) -> PropulsionLatencyBenchmarkResult:
    """Benchmark reduced-order chamber + leak-jet update path latency."""
    if repeats <= 0:
        raise ValueError("repeats must be positive.")
    if operational_budget_s <= 0.0:
        raise ValueError("operational_budget_s must be positive.")

    latencies: list[float] = []
    fallback_count = 0
    current_state = chamber_state

    for _ in range(repeats):
        t0 = time.perf_counter()
        current_state = step_chamber_flow(
            state=current_state,
            params=chamber_params,
            inflow_fuel_kgps=inflow_fuel_kgps,
            inflow_oxidizer_kgps=inflow_oxidizer_kgps,
            throat_outflow_kgps=throat_outflow_kgps,
            dt_s=dt_s,
        ).state
        evaluate_leak_jet(
            path=leak_path,
            compartment_pressure_pa=compartment_pressure_pa,
            compartment_temperature_k=compartment_temperature_k,
            ambient_temperature_k=ambient_temperature_k,
        )
        latency = time.perf_counter() - t0
        latencies.append(latency)
        if (
            cadence_guard_mode(latency, operational_budget_s)
            is ReducedOrderFallbackMode.REDUCED_ORDER_GUARD_ACTIVE
        ):
            fallback_count += 1

    return PropulsionLatencyBenchmarkResult(
        repeats=repeats,
        p50_step_latency_s=_percentile(latencies, 0.50),
        p95_step_latency_s=_percentile(latencies, 0.95),
        operational_budget_s=operational_budget_s,
        fallback_trigger_count=fallback_count,
    )


def benchmark_reduced_order_slosh_latency(
    slosh_state: SloshState,
    slosh_params: SloshModelParams,
    body_linear_accel_body_mps2: Vector3,
    dt_s: float,
    repeats: int = 10,
    operational_budget_s: float = 0.010,
) -> SloshLatencyBenchmarkResult:
    """Benchmark reduced-order slosh update latency with degraded-mode accounting."""
    if repeats <= 0:
        raise ValueError("repeats must be positive.")
    if operational_budget_s <= 0.0:
        raise ValueError("operational_budget_s must be positive.")

    latencies: list[float] = []
    degraded_count = 0
    current_state = slosh_state

    for _ in range(repeats):
        t0 = time.perf_counter()
        step_result = step_slosh_state(
            state=current_state,
            params=slosh_params,
            body_linear_accel_body_mps2=body_linear_accel_body_mps2,
            dt_s=dt_s,
        )
        latency = time.perf_counter() - t0
        mode = cadence_guard_mode(latency, operational_budget_s)
        _ = apply_slosh_degraded_mode(step_result.load, mode)

        latencies.append(latency)
        if mode is ReducedOrderFallbackMode.REDUCED_ORDER_GUARD_ACTIVE:
            degraded_count += 1
        current_state = step_result.state

    return SloshLatencyBenchmarkResult(
        repeats=repeats,
        p50_step_latency_s=_percentile(latencies, 0.50),
        p95_step_latency_s=_percentile(latencies, 0.95),
        operational_budget_s=operational_budget_s,
        degraded_mode_trigger_count=degraded_count,
    )
