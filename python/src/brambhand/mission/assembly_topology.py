"""Disjoint-body assembly-topology state graph baseline (R3.1)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from brambhand.fluid.contracts import (
    TOPOLOGY_TRANSITION_PAYLOAD_SCHEMA_VERSION,
    TopologyTransitionPayload,
)


@dataclass(frozen=True)
class AttachmentInterface:
    """Attachment/interface edge between two rigid bodies/modules."""

    interface_id: str
    body_a_id: str
    body_b_id: str
    interface_kind: str

    def __post_init__(self) -> None:
        if not self.interface_id:
            raise ValueError("interface_id must be non-empty.")
        if not self.body_a_id or not self.body_b_id:
            raise ValueError("body IDs must be non-empty.")
        if self.body_a_id == self.body_b_id:
            raise ValueError("Attachment interface cannot self-connect one body.")
        if not self.interface_kind:
            raise ValueError("interface_kind must be non-empty.")


@dataclass(frozen=True)
class AssemblyTopologyState:
    """Snapshot of assembly connectivity graph and deterministic revision."""

    body_ids: tuple[str, ...]
    interfaces: tuple[AttachmentInterface, ...]
    revision: int = 0

    def __post_init__(self) -> None:
        if not self.body_ids:
            raise ValueError("body_ids cannot be empty.")
        if any(not body_id for body_id in self.body_ids):
            raise ValueError("body_ids must be non-empty strings.")
        if len(set(self.body_ids)) != len(self.body_ids):
            raise ValueError("body_ids must be unique.")
        if self.revision < 0:
            raise ValueError("revision cannot be negative.")

        body_set = set(self.body_ids)
        interface_ids: set[str] = set()
        endpoint_pairs: set[tuple[str, str]] = set()
        for interface in self.interfaces:
            if interface.interface_id in interface_ids:
                raise ValueError("interface_id values must be unique.")
            interface_ids.add(interface.interface_id)

            if interface.body_a_id not in body_set or interface.body_b_id not in body_set:
                raise ValueError("Interface references unknown body_id.")

            if interface.body_a_id <= interface.body_b_id:
                pair = (interface.body_a_id, interface.body_b_id)
            else:
                pair = (interface.body_b_id, interface.body_a_id)
            if pair in endpoint_pairs:
                raise ValueError("Duplicate interface endpoints are not allowed.")
            endpoint_pairs.add(pair)


@dataclass(frozen=True)
class TopologyComponent:
    """Connected component in assembly-topology graph."""

    body_ids: tuple[str, ...]


@dataclass(frozen=True)
class FractureSplitProvenance:
    """Deterministic provenance record for one fracture-driven split transition."""

    parent_body_id: str
    child_body_ids: tuple[str, ...]
    child_labels: tuple[str, ...]
    inherited_interface_ids: tuple[str, ...]


class DockingTransitionKind(StrEnum):
    ATTACH = "attach"
    DETACH = "detach"


@dataclass(frozen=True)
class DockingTransitionProvenance:
    """Provenance for baseline dock/undock topology transitions."""

    transition_kind: DockingTransitionKind
    interface_id: str
    body_a_id: str
    body_b_id: str
    constraint_handoff_state: str
    contact_handoff_state: str


@dataclass(frozen=True)
class TopologyPropagationEffects:
    """Graph-level propagation targets for downstream subsystem updates."""

    added_body_ids: tuple[str, ...]
    removed_body_ids: tuple[str, ...]
    added_interface_ids: tuple[str, ...]
    removed_interface_ids: tuple[str, ...]
    mass_property_update_body_ids: tuple[str, ...]
    constraint_update_interface_ids: tuple[str, ...]
    contact_update_interface_ids: tuple[str, ...]
    control_authority_update_body_ids: tuple[str, ...]


def create_assembly_topology_state(
    body_ids: tuple[str, ...],
    interfaces: tuple[AttachmentInterface, ...] = (),
) -> AssemblyTopologyState:
    """Create canonical topology state with deterministic ordering."""
    ordered_bodies = tuple(sorted(body_ids))
    ordered_interfaces = tuple(sorted(interfaces, key=lambda edge: edge.interface_id))
    return AssemblyTopologyState(
        body_ids=ordered_bodies,
        interfaces=ordered_interfaces,
        revision=0,
    )


def attach_interface(
    state: AssemblyTopologyState,
    interface: AttachmentInterface,
) -> AssemblyTopologyState:
    """Add a new attachment edge and bump topology revision."""
    updated = tuple((*state.interfaces, interface))
    ordered_interfaces = tuple(sorted(updated, key=lambda edge: edge.interface_id))
    return AssemblyTopologyState(
        body_ids=state.body_ids,
        interfaces=ordered_interfaces,
        revision=state.revision + 1,
    )


def detach_interface(
    state: AssemblyTopologyState,
    interface_id: str,
) -> AssemblyTopologyState:
    """Remove an attachment edge by ID and bump topology revision."""
    if not interface_id:
        raise ValueError("interface_id must be non-empty.")

    kept = tuple(
        interface
        for interface in state.interfaces
        if interface.interface_id != interface_id
    )
    if len(kept) == len(state.interfaces):
        raise ValueError("Unknown interface_id.")

    return AssemblyTopologyState(
        body_ids=state.body_ids,
        interfaces=kept,
        revision=state.revision + 1,
    )


def interfaces_for_body(
    state: AssemblyTopologyState,
    body_id: str,
) -> tuple[AttachmentInterface, ...]:
    """Return all interfaces touching `body_id`, ordered by interface ID."""
    if body_id not in set(state.body_ids):
        raise ValueError("Unknown body_id.")
    return tuple(
        interface
        for interface in state.interfaces
        if interface.body_a_id == body_id or interface.body_b_id == body_id
    )


def apply_fracture_split_transition(
    state: AssemblyTopologyState,
    parent_body_id: str,
    child_labels: tuple[str, ...],
    primary_child_label: str | None = None,
) -> tuple[AssemblyTopologyState, FractureSplitProvenance]:
    """Split one parent body into deterministic child bodies with provenance.

    Baseline behavior:
    - parent body is removed from topology body set
    - child body IDs are generated deterministically: `<parent>#frag:<label>`
    - interfaces previously attached to parent are rewired to a designated
      primary child to preserve graph continuity in this baseline
    """
    if parent_body_id not in set(state.body_ids):
        raise ValueError("Unknown parent_body_id.")
    if len(child_labels) < 2:
        raise ValueError("child_labels must contain at least two fragments.")
    if any(not label for label in child_labels):
        raise ValueError("child_labels must be non-empty strings.")
    if len(set(child_labels)) != len(child_labels):
        raise ValueError("child_labels must be unique.")

    ordered_labels = tuple(sorted(child_labels))
    primary = primary_child_label or ordered_labels[0]
    if primary not in set(ordered_labels):
        raise ValueError("primary_child_label must be one of child_labels.")

    child_body_ids = tuple(f"{parent_body_id}#frag:{label}" for label in ordered_labels)
    primary_body_id = f"{parent_body_id}#frag:{primary}"

    body_ids = tuple(
        sorted(tuple(body for body in state.body_ids if body != parent_body_id) + child_body_ids)
    )

    rewired_interfaces: list[AttachmentInterface] = []
    inherited_ids: list[str] = []
    for interface in state.interfaces:
        if interface.body_a_id == parent_body_id and interface.body_b_id == parent_body_id:
            continue
        if interface.body_a_id == parent_body_id:
            inherited_ids.append(interface.interface_id)
            rewired_interfaces.append(
                AttachmentInterface(
                    interface_id=interface.interface_id,
                    body_a_id=primary_body_id,
                    body_b_id=interface.body_b_id,
                    interface_kind=interface.interface_kind,
                )
            )
        elif interface.body_b_id == parent_body_id:
            inherited_ids.append(interface.interface_id)
            rewired_interfaces.append(
                AttachmentInterface(
                    interface_id=interface.interface_id,
                    body_a_id=interface.body_a_id,
                    body_b_id=primary_body_id,
                    interface_kind=interface.interface_kind,
                )
            )
        else:
            rewired_interfaces.append(interface)

    next_state = AssemblyTopologyState(
        body_ids=body_ids,
        interfaces=tuple(sorted(rewired_interfaces, key=lambda edge: edge.interface_id)),
        revision=state.revision + 1,
    )
    return (
        next_state,
        FractureSplitProvenance(
            parent_body_id=parent_body_id,
            child_body_ids=child_body_ids,
            child_labels=ordered_labels,
            inherited_interface_ids=tuple(sorted(inherited_ids)),
        ),
    )


def apply_docking_attach_transition(
    state: AssemblyTopologyState,
    interface_id: str,
    body_a_id: str,
    body_b_id: str,
    interface_kind: str = "dock",
) -> tuple[AssemblyTopologyState, DockingTransitionProvenance]:
    """Attach two bodies via docking interface with handoff provenance."""
    interface = AttachmentInterface(
        interface_id=interface_id,
        body_a_id=body_a_id,
        body_b_id=body_b_id,
        interface_kind=interface_kind,
    )
    next_state = attach_interface(state, interface)
    return (
        next_state,
        DockingTransitionProvenance(
            transition_kind=DockingTransitionKind.ATTACH,
            interface_id=interface_id,
            body_a_id=body_a_id,
            body_b_id=body_b_id,
            constraint_handoff_state="constraints_activated",
            contact_handoff_state="contact_manifold_bound",
        ),
    )


def apply_docking_detach_transition(
    state: AssemblyTopologyState,
    interface_id: str,
) -> tuple[AssemblyTopologyState, DockingTransitionProvenance]:
    """Detach two bodies at docking interface with handoff provenance."""
    target = next((edge for edge in state.interfaces if edge.interface_id == interface_id), None)
    if target is None:
        raise ValueError("Unknown interface_id.")

    next_state = detach_interface(state, interface_id)
    return (
        next_state,
        DockingTransitionProvenance(
            transition_kind=DockingTransitionKind.DETACH,
            interface_id=interface_id,
            body_a_id=target.body_a_id,
            body_b_id=target.body_b_id,
            constraint_handoff_state="constraints_released",
            contact_handoff_state="contact_manifold_released",
        ),
    )


def build_topology_transition_payload(
    transition_id: str,
    transition_kind: str,
    before_state: AssemblyTopologyState,
    after_state: AssemblyTopologyState,
    provenance: dict[str, str],
) -> TopologyTransitionPayload:
    """Build versioned topology transition payload for FSI/leak consumers."""
    interface_endpoints_after = tuple(
        (
            edge.interface_id,
            edge.body_a_id,
            edge.body_b_id,
            edge.interface_kind,
        )
        for edge in after_state.interfaces
    )
    return TopologyTransitionPayload(
        transition_id=transition_id,
        schema_version=TOPOLOGY_TRANSITION_PAYLOAD_SCHEMA_VERSION,
        transition_kind=transition_kind,
        revision=after_state.revision,
        body_ids_before=before_state.body_ids,
        body_ids_after=after_state.body_ids,
        interface_ids_after=tuple(edge.interface_id for edge in after_state.interfaces),
        interface_endpoints_after=interface_endpoints_after,
        provenance=provenance,
    )


def reconstruct_topology_from_transition_payloads(
    initial_state: AssemblyTopologyState,
    payloads: tuple[TopologyTransitionPayload, ...],
) -> AssemblyTopologyState:
    """Reconstruct topology state from ordered transition payload sequence."""
    state = initial_state
    for payload in sorted(payloads, key=lambda item: item.revision):
        if payload.body_ids_before != state.body_ids:
            raise ValueError("Transition payload continuity check failed.")

        interfaces = tuple(
            AttachmentInterface(
                interface_id=interface_id,
                body_a_id=body_a_id,
                body_b_id=body_b_id,
                interface_kind=interface_kind,
            )
            for (
                interface_id,
                body_a_id,
                body_b_id,
                interface_kind,
            ) in payload.interface_endpoints_after
        )
        state = AssemblyTopologyState(
            body_ids=payload.body_ids_after,
            interfaces=interfaces,
            revision=payload.revision,
        )
    return state


def derive_topology_propagation_effects(
    before_state: AssemblyTopologyState,
    after_state: AssemblyTopologyState,
) -> TopologyPropagationEffects:
    """Derive graph-level topology effects for mass/constraints/contact/control."""
    before_bodies = set(before_state.body_ids)
    after_bodies = set(after_state.body_ids)
    added_bodies = tuple(sorted(after_bodies - before_bodies))
    removed_bodies = tuple(sorted(before_bodies - after_bodies))

    before_interfaces = {edge.interface_id for edge in before_state.interfaces}
    after_interfaces = {edge.interface_id for edge in after_state.interfaces}
    added_interfaces = tuple(sorted(after_interfaces - before_interfaces))
    removed_interfaces = tuple(sorted(before_interfaces - after_interfaces))

    mass_targets = tuple(sorted(set(added_bodies + removed_bodies)))
    control_targets = mass_targets
    constraint_targets = tuple(sorted(set(added_interfaces + removed_interfaces)))
    contact_targets = constraint_targets

    return TopologyPropagationEffects(
        added_body_ids=added_bodies,
        removed_body_ids=removed_bodies,
        added_interface_ids=added_interfaces,
        removed_interface_ids=removed_interfaces,
        mass_property_update_body_ids=mass_targets,
        constraint_update_interface_ids=constraint_targets,
        contact_update_interface_ids=contact_targets,
        control_authority_update_body_ids=control_targets,
    )


def connected_components(state: AssemblyTopologyState) -> tuple[TopologyComponent, ...]:
    """Return deterministic connected components of assembly graph."""
    adjacency: dict[str, set[str]] = {body_id: set() for body_id in state.body_ids}
    for interface in state.interfaces:
        adjacency[interface.body_a_id].add(interface.body_b_id)
        adjacency[interface.body_b_id].add(interface.body_a_id)

    visited: set[str] = set()
    components: list[TopologyComponent] = []

    for root in state.body_ids:
        if root in visited:
            continue
        stack = [root]
        comp: list[str] = []

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            comp.append(current)
            for neighbor in sorted(adjacency[current], reverse=True):
                if neighbor not in visited:
                    stack.append(neighbor)

        components.append(TopologyComponent(body_ids=tuple(sorted(comp))))

    components.sort(key=lambda item: item.body_ids[0])
    return tuple(components)
