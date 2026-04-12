from brambhand.fluid.contracts import (
    DockingTransitionKind,
    FaultTransitionKind,
    TopologyTransition,
    parse_optional_topology_transition_kind,
    parse_topology_transition_kind,
)


def test_parse_topology_transition_kind_accepts_enum_values_and_strings() -> None:
    assert (
        parse_topology_transition_kind(DockingTransitionKind.ATTACH)
        == DockingTransitionKind.ATTACH
    )
    assert parse_topology_transition_kind(FaultTransitionKind.FRACTURE_SPLIT) == (
        FaultTransitionKind.FRACTURE_SPLIT
    )
    assert parse_topology_transition_kind("attach") == DockingTransitionKind.ATTACH
    assert parse_topology_transition_kind(" fracture_split ") == FaultTransitionKind.FRACTURE_SPLIT


def test_parse_optional_topology_transition_kind_handles_none() -> None:
    assert parse_optional_topology_transition_kind(None) is None
    assert parse_optional_topology_transition_kind("detach") == DockingTransitionKind.DETACH


def test_parse_topology_transition_kind_rejects_unsupported_values() -> None:
    for raw in ("dock_attach", "", 123):
        try:
            parse_topology_transition_kind(raw)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected topology transition kind parse failure")


def test_topology_transition_coerces_string_kind_via_parser() -> None:
    transition = TopologyTransition(
        transition_id="tx-parse",
        schema_version=1,
        transition_kind="attach",  # type: ignore[arg-type]
        revision=1,
        body_ids_before=("a",),
        body_ids_after=("a", "b"),
        interface_ids_after=(),
        interface_endpoints_after=(),
        provenance={"source": "test"},
    )
    assert transition.transition_kind == DockingTransitionKind.ATTACH
