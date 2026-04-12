"""Shared fluid-domain contracts consumed by propulsion and FSI.

Why this module exists:
- Define backend-neutral boundary/load payloads so reduced-order and CFD providers
  can plug into the same downstream coupling interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from brambhand.physics.vector import Vector3

LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION = 1
SLOSH_BOUNDARY_PAYLOAD_SCHEMA_VERSION = 1
TOPOLOGY_TRANSITION_SCHEMA_VERSION = 1


class DockingTransitionKind(StrEnum):
    """Topology transitions caused by nominal docking lifecycle events."""

    ATTACH = "attach"
    DETACH = "detach"


class FaultTransitionKind(StrEnum):
    """Topology transitions caused by fault/failure progression events."""

    SPLIT = "split"
    FRACTURE_SPLIT = "fracture_split"


type TopologyTransitionKind = DockingTransitionKind | FaultTransitionKind


def parse_topology_transition_kind(value: object) -> TopologyTransitionKind:
    """Parse raw transition kind into canonical docking/fault transition enums."""
    match value:
        case DockingTransitionKind.ATTACH:
            return DockingTransitionKind.ATTACH
        case DockingTransitionKind.DETACH:
            return DockingTransitionKind.DETACH
        case FaultTransitionKind.SPLIT:
            return FaultTransitionKind.SPLIT
        case FaultTransitionKind.FRACTURE_SPLIT:
            return FaultTransitionKind.FRACTURE_SPLIT
        case str() as raw:
            normalized = raw.strip().lower()
            if normalized == DockingTransitionKind.ATTACH.value:
                return DockingTransitionKind.ATTACH
            if normalized == DockingTransitionKind.DETACH.value:
                return DockingTransitionKind.DETACH
            if normalized == FaultTransitionKind.SPLIT.value:
                return FaultTransitionKind.SPLIT
            if normalized == FaultTransitionKind.FRACTURE_SPLIT.value:
                return FaultTransitionKind.FRACTURE_SPLIT
            raise ValueError("Unsupported topology transition kind string.")
        case _:
            raise ValueError("Unsupported topology transition kind value.")


def parse_optional_topology_transition_kind(value: object) -> TopologyTransitionKind | None:
    """Parse optional raw transition kind into canonical enum value."""
    if value is None:
        return None
    return parse_topology_transition_kind(value)


@dataclass(frozen=True)
class FluidBoundaryLoad:
    """Backend-neutral fluid-side load contribution at an interface."""

    interface_id: str
    force_body_n: Vector3
    torque_body_nm: Vector3
    mass_flow_kgps: float
    temperature_k: float

    def __post_init__(self) -> None:
        if not self.interface_id:
            raise ValueError("interface_id must be non-empty.")
        if self.mass_flow_kgps < 0.0:
            raise ValueError("mass_flow_kgps cannot be negative.")
        if self.temperature_k <= 0.0:
            raise ValueError("temperature_k must be positive.")


@dataclass(frozen=True)
class FluidBoundaryDisplacement:
    """Backend-neutral interface displacement feedback from structures to fluid."""

    interface_id: str
    displacement_body_m: Vector3

    def __post_init__(self) -> None:
        if not self.interface_id:
            raise ValueError("interface_id must be non-empty.")


class FSIFluidBoundaryProvider(Protocol):
    """Backend-neutral FSI provider contract for reduced-order and CFD adapters."""

    def evaluate(
        self,
        interface_displacements: tuple[FluidBoundaryDisplacement, ...],
    ) -> tuple[FluidBoundaryLoad, ...]: ...


@dataclass(frozen=True)
class LeakJetBoundaryPayload:
    """Versioned leak-jet boundary payload consumed by FSI exchange contracts."""

    interface_id: str
    schema_version: int
    reaction_force_body_n: Vector3
    reaction_torque_body_nm: Vector3
    mass_flow_kgps: float
    jet_temperature_k: float

    def __post_init__(self) -> None:
        if not self.interface_id:
            raise ValueError("interface_id must be non-empty.")
        if self.schema_version != LEAK_JET_BOUNDARY_PAYLOAD_SCHEMA_VERSION:
            raise ValueError("Unsupported leak-jet boundary payload schema_version.")
        if self.mass_flow_kgps < 0.0:
            raise ValueError("mass_flow_kgps cannot be negative.")
        if self.jet_temperature_k <= 0.0:
            raise ValueError("jet_temperature_k must be positive.")

    def to_fluid_boundary_load(self) -> FluidBoundaryLoad:
        """Convert leak-jet payload into backend-neutral FSI boundary-load contract."""
        return FluidBoundaryLoad(
            interface_id=self.interface_id,
            force_body_n=self.reaction_force_body_n,
            torque_body_nm=self.reaction_torque_body_nm,
            mass_flow_kgps=self.mass_flow_kgps,
            temperature_k=self.jet_temperature_k,
        )


@dataclass(frozen=True)
class SloshBoundaryPayload:
    """Versioned slosh-load payload consumed by FSI/coupling-controller contracts."""

    interface_id: str
    schema_version: int
    slosh_force_body_n: Vector3
    slosh_torque_body_nm: Vector3
    com_offset_body_m: Vector3
    reference_temperature_k: float = 273.15

    def __post_init__(self) -> None:
        if not self.interface_id:
            raise ValueError("interface_id must be non-empty.")
        if self.schema_version != SLOSH_BOUNDARY_PAYLOAD_SCHEMA_VERSION:
            raise ValueError("Unsupported slosh boundary payload schema_version.")
        if self.reference_temperature_k <= 0.0:
            raise ValueError("reference_temperature_k must be positive.")

    def to_fluid_boundary_load(self) -> FluidBoundaryLoad:
        """Convert slosh payload into backend-neutral FSI boundary-load contract."""
        return FluidBoundaryLoad(
            interface_id=self.interface_id,
            force_body_n=self.slosh_force_body_n,
            torque_body_nm=self.slosh_torque_body_nm,
            mass_flow_kgps=0.0,
            temperature_k=self.reference_temperature_k,
        )


@dataclass(frozen=True)
class TopologyTransition:
    """Versioned topology-transition contract for FSI/leak-boundary consumers."""

    transition_id: str
    schema_version: int
    transition_kind: TopologyTransitionKind
    revision: int
    body_ids_before: tuple[str, ...]
    body_ids_after: tuple[str, ...]
    interface_ids_after: tuple[str, ...]
    interface_endpoints_after: tuple[tuple[str, str, str, str], ...]
    provenance: dict[str, str]

    def __post_init__(self) -> None:
        if not self.transition_id:
            raise ValueError("transition_id must be non-empty.")
        if self.schema_version != TOPOLOGY_TRANSITION_SCHEMA_VERSION:
            raise ValueError("Unsupported topology transition schema_version.")
        parsed_kind = parse_topology_transition_kind(self.transition_kind)
        object.__setattr__(self, "transition_kind", parsed_kind)
        if self.revision < 0:
            raise ValueError("revision cannot be negative.")
        if not self.body_ids_before or not self.body_ids_after:
            raise ValueError("body_ids_before/body_ids_after cannot be empty.")
        endpoint_ids = tuple(item[0] for item in self.interface_endpoints_after)
        if endpoint_ids != self.interface_ids_after:
            raise ValueError(
                "interface_endpoints_after IDs must match interface_ids_after ordering."
            )
