"""Deterministic two-way fluid-structure coupling baseline with residual telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from brambhand.fluid.contracts import FluidBoundaryLoad
from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class InterfaceDisplacement:
    """Structural interface displacement feedback consumed by fluid solvers."""

    interface_id: str
    displacement_body_m: Vector3

    def __post_init__(self) -> None:
        if not self.interface_id:
            raise ValueError("interface_id must be non-empty.")


@dataclass(frozen=True)
class FSICouplingParams:
    """Iteration and convergence controls for two-way partitioned FSI coupling."""

    max_iterations: int
    residual_tolerance: float
    relaxation_factor: float = 1.0

    def __post_init__(self) -> None:
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive.")
        if self.residual_tolerance < 0.0:
            raise ValueError("residual_tolerance cannot be negative.")
        if self.relaxation_factor <= 0.0 or self.relaxation_factor > 1.0:
            raise ValueError("relaxation_factor must be in (0, 1].")


@dataclass(frozen=True)
class FSICouplingIterationTelemetry:
    """Per-iteration convergence diagnostics for the coupling loop."""

    iteration: int
    residual: float
    interface_count: int


@dataclass(frozen=True)
class FSICouplingResult:
    """Coupling outputs and deterministic convergence telemetry."""

    converged: bool
    termination_reason: str
    iterations_used: int
    residual_history: tuple[FSICouplingIterationTelemetry, ...]
    fluid_loads: tuple[FluidBoundaryLoad, ...]
    interface_displacements: tuple[InterfaceDisplacement, ...]


class FluidBoundaryProvider(Protocol):
    """Provider that computes fluid-side interface loads from structure feedback."""

    def evaluate(
        self,
        interface_displacements: tuple[InterfaceDisplacement, ...],
    ) -> tuple[FluidBoundaryLoad, ...]: ...


class StructuralBoundaryProvider(Protocol):
    """Provider that computes structural interface displacement from fluid loads."""

    def evaluate(
        self,
        fluid_loads: tuple[FluidBoundaryLoad, ...],
    ) -> tuple[InterfaceDisplacement, ...]: ...


def _canonicalize_displacements(
    displacements: tuple[InterfaceDisplacement, ...],
) -> tuple[InterfaceDisplacement, ...]:
    return tuple(sorted(displacements, key=lambda item: item.interface_id))


def _canonicalize_loads(loads: tuple[FluidBoundaryLoad, ...]) -> tuple[FluidBoundaryLoad, ...]:
    return tuple(sorted(loads, key=lambda item: item.interface_id))


def _displacement_map(
    displacements: tuple[InterfaceDisplacement, ...],
) -> dict[str, InterfaceDisplacement]:
    return {item.interface_id: item for item in displacements}


def _compute_residual(
    previous: tuple[InterfaceDisplacement, ...],
    current: tuple[InterfaceDisplacement, ...],
) -> float:
    previous_map = _displacement_map(previous)
    current_map = _displacement_map(current)
    interface_ids = set(previous_map) | set(current_map)
    residual = 0.0

    zero_displacement = Vector3(0.0, 0.0, 0.0)
    for interface_id in interface_ids:
        prev = previous_map.get(
            interface_id,
            InterfaceDisplacement(
                interface_id=interface_id,
                displacement_body_m=zero_displacement,
            ),
        )
        curr = current_map.get(
            interface_id,
            InterfaceDisplacement(
                interface_id=interface_id,
                displacement_body_m=zero_displacement,
            ),
        )
        delta = curr.displacement_body_m - prev.displacement_body_m
        residual = max(residual, delta.norm())
    return residual


def _relax_displacements(
    previous: tuple[InterfaceDisplacement, ...],
    current: tuple[InterfaceDisplacement, ...],
    relaxation_factor: float,
) -> tuple[InterfaceDisplacement, ...]:
    previous_map = _displacement_map(previous)
    current_map = _displacement_map(current)
    relaxed: list[InterfaceDisplacement] = []

    zero_displacement = InterfaceDisplacement(
        interface_id="_",
        displacement_body_m=Vector3(0.0, 0.0, 0.0),
    )
    for interface_id in sorted(set(previous_map) | set(current_map)):
        prev_vector = previous_map.get(interface_id, zero_displacement)
        curr_vector = current_map.get(interface_id, zero_displacement)
        blended = (
            (1.0 - relaxation_factor) * prev_vector.displacement_body_m
            + relaxation_factor * curr_vector.displacement_body_m
        )
        relaxed.append(
            InterfaceDisplacement(interface_id=interface_id, displacement_body_m=blended)
        )

    return tuple(relaxed)


def couple_fsi_two_way(
    fluid_provider: FluidBoundaryProvider,
    structural_provider: StructuralBoundaryProvider,
    params: FSICouplingParams,
    initial_displacements: tuple[InterfaceDisplacement, ...] = (),
) -> FSICouplingResult:
    """Execute deterministic partitioned two-way FSI coupling iterations."""
    previous_displacements = _canonicalize_displacements(initial_displacements)
    residual_history: list[FSICouplingIterationTelemetry] = []
    final_loads: tuple[FluidBoundaryLoad, ...] = ()
    final_displacements = previous_displacements

    for iteration in range(1, params.max_iterations + 1):
        final_loads = _canonicalize_loads(fluid_provider.evaluate(previous_displacements))
        proposed_displacements = _canonicalize_displacements(
            structural_provider.evaluate(final_loads)
        )
        residual = _compute_residual(previous_displacements, proposed_displacements)
        residual_history.append(
            FSICouplingIterationTelemetry(
                iteration=iteration,
                residual=residual,
                interface_count=len(proposed_displacements),
            )
        )

        if residual <= params.residual_tolerance:
            return FSICouplingResult(
                converged=True,
                termination_reason="converged",
                iterations_used=iteration,
                residual_history=tuple(residual_history),
                fluid_loads=final_loads,
                interface_displacements=proposed_displacements,
            )

        previous_displacements = _relax_displacements(
            previous_displacements,
            proposed_displacements,
            relaxation_factor=params.relaxation_factor,
        )
        final_displacements = proposed_displacements

    return FSICouplingResult(
        converged=False,
        termination_reason="max_iterations",
        iterations_used=params.max_iterations,
        residual_history=tuple(residual_history),
        fluid_loads=final_loads,
        interface_displacements=final_displacements,
    )
