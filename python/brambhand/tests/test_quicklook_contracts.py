from pathlib import Path

from brambhand.scenario.replay_log import ReplayLog
from brambhand.visualization.quicklook_contracts import (
    QUICKLOOK_SEVERITY_COLOR_MAP,
    QUICKLOOK_SEVERITY_SCHEMA_VERSION,
    QUICKLOOK_STYLE_SCHEMA_VERSION,
    QUICKLOOK_TELEMETRY_SCHEMA_VERSION,
    QuicklookTelemetryContract,
    event_kind_to_severity,
    extract_quicklook_telemetry,
    severity_to_color_hex,
)
from brambhand.visualization.quicklook_pipeline import (
    build_headless_quicklook_output,
    load_headless_quicklook_output,
)


def test_quicklook_contract_extracts_trajectory_and_events_in_sequence_order() -> None:
    replay = ReplayLog.empty()
    replay.append(0.0, "step_started", {"position_m": {"x": 0.0, "y": 0.0, "z": 0.0}})
    replay.append(1.0, "step_completed", {"position_m": [1.0, 2.0, 3.0]})
    replay.append(2.0, "alarm", {"message": "warn"})

    contract = extract_quicklook_telemetry(replay)

    assert contract.schema_version == QUICKLOOK_TELEMETRY_SCHEMA_VERSION
    assert contract.severity_schema_version == QUICKLOOK_SEVERITY_SCHEMA_VERSION
    assert tuple(event.kind for event in contract.events) == (
        "step_started",
        "step_completed",
        "alarm",
    )
    assert tuple(event.severity for event in contract.events) == ("info", "info", "warning")
    assert len(contract.trajectory) == 2
    assert contract.trajectory[0].position_m == (0.0, 0.0, 0.0)
    assert contract.trajectory[1].position_m == (1.0, 2.0, 3.0)
    assert contract.planned_trajectory == ()


def test_quicklook_contract_rejects_unsupported_schema_version() -> None:
    try:
        QuicklookTelemetryContract(
            schema_version=999,
            severity_schema_version=QUICKLOOK_SEVERITY_SCHEMA_VERSION,
            trajectory=(),
            planned_trajectory=(),
            events=(),
        )
    except ValueError as exc:
        assert "schema_version" in str(exc)
    else:
        raise AssertionError("Expected quicklook schema-version validation failure")


def test_quicklook_contract_rejects_unsupported_severity_schema_version() -> None:
    try:
        QuicklookTelemetryContract(
            schema_version=QUICKLOOK_TELEMETRY_SCHEMA_VERSION,
            severity_schema_version=999,
            trajectory=(),
            planned_trajectory=(),
            events=(),
        )
    except ValueError as exc:
        assert "severity_schema_version" in str(exc)
    else:
        raise AssertionError("Expected quicklook severity-schema validation failure")


def test_headless_quicklook_pipeline_builds_2d_and_3d_outputs() -> None:
    replay = ReplayLog.empty()
    replay.append(0.0, "simulation_started", {"dt_s": 1.0})
    replay.append(
        0.0,
        "step",
        {"position_m": [0.0, 0.0, 0.0], "planned_position_m": [0.1, 0.0, 0.0]},
    )
    replay.append(
        1.0,
        "step",
        {"position_m": [1.0, 2.0, 3.0], "planned_position_m": [1.1, 2.1, 3.1]},
    )
    replay.append(2.0, "alarm", {"message": "warn"})

    output = build_headless_quicklook_output(replay)

    assert output.style_schema_version == QUICKLOOK_STYLE_SCHEMA_VERSION
    assert len(output.trajectory_2d) == 2
    assert len(output.trajectory_3d) == 2
    assert len(output.planned_trajectory_2d) == 2
    assert len(output.planned_trajectory_3d) == 2
    assert output.planned_trajectory_2d[0].x_m == 0.1
    assert output.trajectory_2d[1].x_m == 1.0
    assert output.trajectory_2d[1].y_m == 2.0
    assert output.trajectory_3d[1].z_m == 3.0

    assert len(output.event_markers) == 4
    assert output.event_markers[0].kind == "simulation_started"
    assert output.event_markers[0].severity == "info"
    assert output.event_markers[0].color_hex == QUICKLOOK_SEVERITY_COLOR_MAP["info"]
    assert output.event_markers[0].x_m is None
    assert output.event_markers[1].kind == "step"
    assert output.event_markers[1].x_m == 0.0
    assert output.event_markers[3].kind == "alarm"
    assert output.event_markers[3].severity == "warning"
    assert output.event_markers[3].color_hex == QUICKLOOK_SEVERITY_COLOR_MAP["warning"]
    assert output.event_markers[3].x_m == 1.0
    assert output.event_markers[3].y_m == 2.0
    assert output.event_markers[3].z_m == 3.0

    assert len(output.current_planned_overlay) == 2
    assert output.current_planned_overlay[0].planned_position_m == (0.1, 0.0, 0.0)
    assert output.current_planned_overlay[1].planned_position_m == (1.1, 2.1, 3.1)


def test_quicklook_severity_mapping_is_deterministic_and_has_info_fallback() -> None:
    assert event_kind_to_severity("step_completed") == "info"
    assert event_kind_to_severity("alarm") == "warning"
    assert event_kind_to_severity("fault") == "critical"
    assert event_kind_to_severity("custom_new_event") == "info"


def test_quicklook_severity_style_mapping_uses_three_color_palette() -> None:
    assert severity_to_color_hex("info") == QUICKLOOK_SEVERITY_COLOR_MAP["info"]
    assert severity_to_color_hex("warning") == QUICKLOOK_SEVERITY_COLOR_MAP["warning"]
    assert severity_to_color_hex("critical") == QUICKLOOK_SEVERITY_COLOR_MAP["critical"]


def test_current_vs_planned_overlay_handles_missing_planned_samples() -> None:
    replay = ReplayLog.empty()
    replay.append(
        0.0,
        "step",
        {"position_m": [0.0, 0.0, 0.0], "planned_position_m": [0.0, 0.1, 0.0]},
    )
    replay.append(1.0, "step", {"position_m": [1.0, 1.0, 1.0]})

    output = build_headless_quicklook_output(replay)

    assert len(output.current_planned_overlay) == 2
    assert output.current_planned_overlay[0].planned_position_m == (0.0, 0.1, 0.0)
    assert output.current_planned_overlay[1].planned_position_m is None


def test_headless_quicklook_pipeline_loads_from_jsonl(tmp_path: Path) -> None:
    replay = ReplayLog.empty()
    replay.append(0.0, "step", {"position_m": [0.0, 0.0, 0.0]})
    replay_path = tmp_path / "replay.jsonl"
    replay.save_jsonl(replay_path)

    output = load_headless_quicklook_output(replay_path)

    assert output.style_schema_version == QUICKLOOK_STYLE_SCHEMA_VERSION
    assert len(output.trajectory_3d) == 1
    assert output.trajectory_3d[0].x_m == 0.0
    assert output.planned_trajectory_3d == ()
    assert len(output.current_planned_overlay) == 1
    assert output.current_planned_overlay[0].planned_position_m is None
    assert len(output.event_markers) == 1
    assert output.event_markers[0].severity == "info"
    assert output.event_markers[0].color_hex == QUICKLOOK_SEVERITY_COLOR_MAP["info"]
    assert output.event_markers[0].x_m == 0.0
