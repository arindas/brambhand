from brambhand.fluid.contracts import (
    TOPOLOGY_TRANSITION_PAYLOAD_SCHEMA_VERSION,
    TopologyTransitionKind,
    TopologyTransitionPayload,
)
from brambhand.mission.assembly_topology import (
    AttachmentInterface,
    DockingTransitionKind,
    apply_docking_attach_transition,
    apply_docking_detach_transition,
    apply_fracture_split_transition,
    attach_interface,
    build_topology_transition_payload,
    connected_components,
    create_assembly_topology_state,
    derive_topology_propagation_effects,
    detach_interface,
    interfaces_for_body,
    reconstruct_topology_from_transition_payloads,
)


def test_assembly_topology_graph_attach_detach_and_components() -> None:
    state = create_assembly_topology_state(("core", "module_a", "module_b"))

    dock_a = AttachmentInterface(
        interface_id="dock_a",
        body_a_id="core",
        body_b_id="module_a",
        interface_kind="dock",
    )
    dock_b = AttachmentInterface(
        interface_id="dock_b",
        body_a_id="core",
        body_b_id="module_b",
        interface_kind="dock",
    )

    state = attach_interface(state, dock_a)
    state = attach_interface(state, dock_b)

    components = connected_components(state)
    assert len(components) == 1
    assert components[0].body_ids == ("core", "module_a", "module_b")
    assert state.revision == 2

    state = detach_interface(state, "dock_b")
    components = connected_components(state)
    assert len(components) == 2
    assert components[0].body_ids == ("core", "module_a")
    assert components[1].body_ids == ("module_b",)
    assert state.revision == 3


def test_assembly_topology_is_deterministic_for_unordered_inputs() -> None:
    i2 = AttachmentInterface(
        interface_id="b_if",
        body_a_id="b",
        body_b_id="c",
        interface_kind="structural",
    )
    i1 = AttachmentInterface(
        interface_id="a_if",
        body_a_id="a",
        body_b_id="b",
        interface_kind="structural",
    )

    state1 = create_assembly_topology_state(("c", "a", "b"), interfaces=(i2, i1))
    state2 = create_assembly_topology_state(("a", "b", "c"), interfaces=(i1, i2))

    assert state1 == state2
    assert tuple(iface.interface_id for iface in state1.interfaces) == ("a_if", "b_if")


def test_assembly_topology_rejects_duplicate_endpoints_and_unknown_refs() -> None:
    valid = create_assembly_topology_state(("a", "b", "c"))

    state = attach_interface(
        valid,
        AttachmentInterface("if1", "a", "b", "dock"),
    )
    try:
        attach_interface(state, AttachmentInterface("if2", "b", "a", "dock"))
    except ValueError as exc:
        assert "Duplicate interface endpoints" in str(exc)
    else:
        raise AssertionError("Expected duplicate-endpoint rejection")

    try:
        create_assembly_topology_state(
            ("a", "b"),
            interfaces=(AttachmentInterface("ifx", "a", "z", "dock"),),
        )
    except ValueError as exc:
        assert "unknown body_id" in str(exc)
    else:
        raise AssertionError("Expected unknown-body reference rejection")


def test_assembly_topology_interfaces_for_body_query() -> None:
    state = create_assembly_topology_state(("core", "m1", "m2"))
    state = attach_interface(state, AttachmentInterface("if1", "core", "m1", "dock"))
    state = attach_interface(state, AttachmentInterface("if2", "core", "m2", "dock"))

    interfaces = interfaces_for_body(state, "core")
    assert tuple(i.interface_id for i in interfaces) == ("if1", "if2")


def test_fracture_split_transition_generates_deterministic_children_and_provenance() -> None:
    state = create_assembly_topology_state(("core", "left", "right"))
    state = attach_interface(state, AttachmentInterface("if_left", "core", "left", "dock"))
    state = attach_interface(state, AttachmentInterface("if_right", "core", "right", "dock"))

    next_state, provenance = apply_fracture_split_transition(
        state,
        parent_body_id="core",
        child_labels=("frag_b", "frag_a"),
        primary_child_label="frag_a",
    )

    assert "core" not in set(next_state.body_ids)
    assert provenance.child_body_ids == ("core#frag:frag_a", "core#frag:frag_b")
    assert provenance.child_labels == ("frag_a", "frag_b")
    assert provenance.inherited_interface_ids == ("if_left", "if_right")
    assert next_state.revision == state.revision + 1

    core_interfaces = interfaces_for_body(next_state, "core#frag:frag_a")
    assert tuple(i.interface_id for i in core_interfaces) == ("if_left", "if_right")


def test_docking_attach_detach_transition_emits_handoff_provenance() -> None:
    state = create_assembly_topology_state(("chaser", "target"))

    attached, attach_provenance = apply_docking_attach_transition(
        state,
        interface_id="dock_if",
        body_a_id="chaser",
        body_b_id="target",
    )
    assert attach_provenance.transition_kind == DockingTransitionKind.ATTACH
    assert attach_provenance.constraint_handoff_state == "constraints_activated"
    assert len(attached.interfaces) == 1

    detached, detach_provenance = apply_docking_detach_transition(attached, "dock_if")
    assert detach_provenance.transition_kind == DockingTransitionKind.DETACH
    assert detach_provenance.contact_handoff_state == "contact_manifold_released"
    assert len(detached.interfaces) == 0
    assert detached.revision == state.revision + 2


def test_topology_transition_payload_mapping_for_fsi_consumers() -> None:
    state = create_assembly_topology_state(("a", "b"))
    attached, _ = apply_docking_attach_transition(
        state,
        interface_id="if_ab",
        body_a_id="a",
        body_b_id="b",
    )

    payload = build_topology_transition_payload(
        transition_id="tx-001",
        transition_kind=TopologyTransitionKind.ATTACH,
        before_state=state,
        after_state=attached,
        provenance={"source": "docking_baseline"},
    )

    assert payload.schema_version == TOPOLOGY_TRANSITION_PAYLOAD_SCHEMA_VERSION
    assert payload.transition_id == "tx-001"
    assert payload.transition_kind == TopologyTransitionKind.ATTACH
    assert payload.body_ids_before == ("a", "b")
    assert payload.interface_ids_after == ("if_ab",)
    assert payload.interface_endpoints_after == (("if_ab", "a", "b", "dock"),)


def test_topology_transition_payload_rejects_unsupported_version() -> None:
    try:
        TopologyTransitionPayload(
            transition_id="tx",
            schema_version=999,
            transition_kind=TopologyTransitionKind.ATTACH,
            revision=1,
            body_ids_before=("a",),
            body_ids_after=("a", "b"),
            interface_ids_after=("if_ab",),
            interface_endpoints_after=(("if_ab", "a", "b", "dock"),),
            provenance={"source": "test"},
        )
    except ValueError as exc:
        assert "schema_version" in str(exc)
    else:
        raise AssertionError("Expected topology transition payload version validation failure")


def test_topology_transition_payload_determinism_and_reconstruction() -> None:
    initial = create_assembly_topology_state(("core", "target"))

    state_a, _ = apply_docking_attach_transition(
        initial,
        interface_id="dock_if",
        body_a_id="core",
        body_b_id="target",
    )
    payload_a = build_topology_transition_payload(
        transition_id="tx1",
        transition_kind=TopologyTransitionKind.ATTACH,
        before_state=initial,
        after_state=state_a,
        provenance={"source": "test"},
    )

    state_b, _ = apply_fracture_split_transition(
        state_a,
        parent_body_id="core",
        child_labels=("frag2", "frag1"),
    )
    payload_b = build_topology_transition_payload(
        transition_id="tx2",
        transition_kind=TopologyTransitionKind.FRACTURE_SPLIT,
        before_state=state_a,
        after_state=state_b,
        provenance={"source": "test"},
    )

    replay = reconstruct_topology_from_transition_payloads(initial, (payload_a, payload_b))
    assert replay == state_b
    assert len(state_a.body_ids) == 2
    assert len(state_b.body_ids) == 3
    assert len(set(state_b.body_ids)) == len(state_b.body_ids)

    effects = derive_topology_propagation_effects(state_a, state_b)
    assert "core" in effects.mass_property_update_body_ids
    assert len(effects.control_authority_update_body_ids) >= 1

    state_a2, _ = apply_docking_attach_transition(
        initial,
        interface_id="dock_if",
        body_a_id="core",
        body_b_id="target",
    )
    state_b2, _ = apply_fracture_split_transition(
        state_a2,
        parent_body_id="core",
        child_labels=("frag2", "frag1"),
    )
    assert state_b2 == state_b


def test_topology_propagation_effects_cover_mass_constraints_contact_and_control() -> None:
    before = create_assembly_topology_state(("core", "target"))
    after_attach, _ = apply_docking_attach_transition(
        before,
        interface_id="dock_if",
        body_a_id="core",
        body_b_id="target",
    )

    effects_attach = derive_topology_propagation_effects(before, after_attach)
    assert effects_attach.added_interface_ids == ("dock_if",)
    assert effects_attach.constraint_update_interface_ids == ("dock_if",)
    assert effects_attach.contact_update_interface_ids == ("dock_if",)

    after_split, _ = apply_fracture_split_transition(
        after_attach,
        parent_body_id="core",
        child_labels=("f1", "f2"),
    )
    effects_split = derive_topology_propagation_effects(after_attach, after_split)

    assert "core" in effects_split.removed_body_ids
    assert len(effects_split.added_body_ids) == 2
    assert "core" in effects_split.mass_property_update_body_ids
    assert "core" in effects_split.control_authority_update_body_ids
