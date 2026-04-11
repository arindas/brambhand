"""R3 fracture initiation and damage-propagation baseline contracts."""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.structures.fem.contracts import FEMSolveResult2D, FEMSolveResult3D

CONNECTED_TOPOLOGY_DAMAGE_PAYLOAD_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class FractureInitiationParams:
    """Stress-threshold policy for deterministic fracture initiation baseline."""

    yield_von_mises_pa: float
    ultimate_von_mises_pa: float

    def __post_init__(self) -> None:
        if self.yield_von_mises_pa <= 0.0:
            raise ValueError("yield_von_mises_pa must be positive.")
        if self.ultimate_von_mises_pa < self.yield_von_mises_pa:
            raise ValueError("ultimate_von_mises_pa must be >= yield_von_mises_pa.")


@dataclass(frozen=True)
class ElementDamageState:
    """Per-element damage state from fracture-initiation evaluation."""

    element_id: int
    von_mises_pa: float
    damage_fraction: float
    fractured: bool

    def __post_init__(self) -> None:
        if self.element_id < 0:
            raise ValueError("element_id cannot be negative.")
        if self.von_mises_pa < 0.0:
            raise ValueError("von_mises_pa cannot be negative.")
        if not 0.0 <= self.damage_fraction <= 1.0:
            raise ValueError("damage_fraction must be in [0, 1].")


@dataclass(frozen=True)
class DamagePropagationResult:
    """Aggregate damage and propagated behavior modifiers."""

    element_states: tuple[ElementDamageState, ...]
    mean_damage_fraction: float
    max_damage_fraction: float
    failed_element_fraction: float
    mass_scale: float
    stiffness_scale: float
    contact_stiffness_scale: float
    leak_path_created: bool


@dataclass(frozen=True)
class ConnectedTopologyDamagePayload:
    """Connected-topology damage state for leak/FSI consumers.

    This payload explicitly represents damage-without-split semantics by keeping a
    single `component_id` while encoding holes/crack-network progression metadata.
    """

    component_id: str
    schema_version: int
    damaged_element_ids: tuple[int, ...]
    failed_element_ids: tuple[int, ...]
    crack_network_edges: tuple[tuple[int, int], ...]
    hole_area_proxy_m2: float
    leak_path_candidate_element_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.component_id:
            raise ValueError("component_id must be non-empty.")
        if self.schema_version != CONNECTED_TOPOLOGY_DAMAGE_PAYLOAD_SCHEMA_VERSION:
            raise ValueError("Unsupported connected-topology damage schema_version.")
        if self.hole_area_proxy_m2 < 0.0:
            raise ValueError("hole_area_proxy_m2 cannot be negative.")


def _damage_from_stress(stress_pa: float, params: FractureInitiationParams) -> float:
    if stress_pa <= params.yield_von_mises_pa:
        return 0.0
    if stress_pa >= params.ultimate_von_mises_pa:
        return 1.0
    span = params.ultimate_von_mises_pa - params.yield_von_mises_pa
    if span == 0.0:
        return 1.0
    return (stress_pa - params.yield_von_mises_pa) / span


def evaluate_fracture_initiation(
    von_mises_pa_by_element: tuple[float, ...],
    params: FractureInitiationParams,
) -> tuple[ElementDamageState, ...]:
    """Evaluate deterministic per-element damage state from von-Mises stresses."""
    states: list[ElementDamageState] = []
    for element_id, stress_pa in enumerate(von_mises_pa_by_element):
        if stress_pa < 0.0:
            raise ValueError("von_mises_pa_by_element values cannot be negative.")
        damage = _damage_from_stress(stress_pa, params)
        states.append(
            ElementDamageState(
                element_id=element_id,
                von_mises_pa=stress_pa,
                damage_fraction=damage,
                fractured=damage >= 1.0,
            )
        )
    return tuple(states)


def evaluate_fracture_initiation_from_fem_2d(
    solve_result: FEMSolveResult2D,
    params: FractureInitiationParams,
) -> tuple[ElementDamageState, ...]:
    """Evaluate fracture initiation directly from 2D FEM solve outputs."""
    return evaluate_fracture_initiation(
        tuple(element.von_mises_pa for element in solve_result.element_results),
        params,
    )


def evaluate_fracture_initiation_from_fem_3d(
    solve_result: FEMSolveResult3D,
    params: FractureInitiationParams,
) -> tuple[ElementDamageState, ...]:
    """Evaluate fracture initiation directly from 3D FEM solve outputs."""
    return evaluate_fracture_initiation(
        tuple(element.von_mises_pa for element in solve_result.element_results),
        params,
    )


def propagate_damage_effects(
    element_states: tuple[ElementDamageState, ...],
    max_mass_loss_fraction: float = 0.2,
    min_stiffness_scale: float = 0.05,
    max_contact_compliance_multiplier: float = 4.0,
    leak_path_damage_threshold: float = 0.85,
) -> DamagePropagationResult:
    """Propagate element damage into mass/stiffness/contact baseline modifiers."""
    if not element_states:
        raise ValueError("element_states cannot be empty.")
    if not 0.0 <= max_mass_loss_fraction <= 1.0:
        raise ValueError("max_mass_loss_fraction must be in [0, 1].")
    if not 0.0 < min_stiffness_scale <= 1.0:
        raise ValueError("min_stiffness_scale must be in (0, 1].")
    if max_contact_compliance_multiplier < 1.0:
        raise ValueError("max_contact_compliance_multiplier must be >= 1.")
    if not 0.0 <= leak_path_damage_threshold <= 1.0:
        raise ValueError("leak_path_damage_threshold must be in [0, 1].")

    damages = tuple(state.damage_fraction for state in element_states)
    mean_damage = sum(damages) / len(damages)
    max_damage = max(damages)
    failed_fraction = sum(1 for d in damages if d >= 1.0) / len(damages)

    mass_scale = 1.0 - max_mass_loss_fraction * mean_damage
    stiffness_scale = max(min_stiffness_scale, 1.0 - mean_damage)
    compliance = 1.0 + (max_contact_compliance_multiplier - 1.0) * max_damage
    contact_stiffness_scale = 1.0 / compliance
    leak_path_created = max_damage >= leak_path_damage_threshold

    return DamagePropagationResult(
        element_states=element_states,
        mean_damage_fraction=mean_damage,
        max_damage_fraction=max_damage,
        failed_element_fraction=failed_fraction,
        mass_scale=mass_scale,
        stiffness_scale=stiffness_scale,
        contact_stiffness_scale=contact_stiffness_scale,
        leak_path_created=leak_path_created,
    )


def build_connected_topology_damage_payload(
    element_states: tuple[ElementDamageState, ...],
    component_id: str,
    leak_path_damage_threshold: float = 0.85,
    hole_area_per_failed_element_m2: float = 1e-4,
) -> ConnectedTopologyDamagePayload:
    """Build connected-topology damage payload from element damage states."""
    if not element_states:
        raise ValueError("element_states cannot be empty.")
    if not 0.0 <= leak_path_damage_threshold <= 1.0:
        raise ValueError("leak_path_damage_threshold must be in [0, 1].")
    if hole_area_per_failed_element_m2 < 0.0:
        raise ValueError("hole_area_per_failed_element_m2 cannot be negative.")

    damaged_ids = tuple(sorted(s.element_id for s in element_states if s.damage_fraction > 0.0))
    failed_ids = tuple(sorted(s.element_id for s in element_states if s.fractured))
    leak_candidates = tuple(
        sorted(
            s.element_id
            for s in element_states
            if s.damage_fraction >= leak_path_damage_threshold
        )
    )

    crack_edges: list[tuple[int, int]] = []
    for left, right in zip(damaged_ids, damaged_ids[1:], strict=False):
        crack_edges.append((left, right))

    return ConnectedTopologyDamagePayload(
        component_id=component_id,
        schema_version=CONNECTED_TOPOLOGY_DAMAGE_PAYLOAD_SCHEMA_VERSION,
        damaged_element_ids=damaged_ids,
        failed_element_ids=failed_ids,
        crack_network_edges=tuple(crack_edges),
        hole_area_proxy_m2=hole_area_per_failed_element_m2 * len(failed_ids),
        leak_path_candidate_element_ids=leak_candidates,
    )
