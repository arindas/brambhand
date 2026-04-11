from pathlib import Path

from brambhand.scenario.replay_log import ReplayLog
from brambhand.visualization.quicklook_contracts import (
    QUICKLOOK_TELEMETRY_SCHEMA_VERSION,
    QuicklookTelemetryContract,
    extract_quicklook_telemetry,
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
    assert tuple(event.kind for event in contract.events) == (
        "step_started",
        "step_completed",
        "alarm",
    )
    assert len(contract.trajectory) == 2
    assert contract.trajectory[0].position_m == (0.0, 0.0, 0.0)
    assert contract.trajectory[1].position_m == (1.0, 2.0, 3.0)


def test_quicklook_contract_rejects_unsupported_schema_version() -> None:
    try:
        QuicklookTelemetryContract(
            schema_version=999,
            trajectory=(),
            events=(),
        )
    except ValueError as exc:
        assert "schema_version" in str(exc)
    else:
        raise AssertionError("Expected quicklook schema-version validation failure")


def test_headless_quicklook_pipeline_builds_2d_and_3d_outputs() -> None:
    replay = ReplayLog.empty()
    replay.append(0.0, "step", {"position_m": [0.0, 0.0, 0.0]})
    replay.append(1.0, "step", {"position_m": [1.0, 2.0, 3.0]})

    output = build_headless_quicklook_output(replay)

    assert len(output.trajectory_2d) == 2
    assert len(output.trajectory_3d) == 2
    assert output.trajectory_2d[1].x_m == 1.0
    assert output.trajectory_2d[1].y_m == 2.0
    assert output.trajectory_3d[1].z_m == 3.0


def test_headless_quicklook_pipeline_loads_from_jsonl(tmp_path: Path) -> None:
    replay = ReplayLog.empty()
    replay.append(0.0, "step", {"position_m": [0.0, 0.0, 0.0]})
    replay_path = tmp_path / "replay.jsonl"
    replay.save_jsonl(replay_path)

    output = load_headless_quicklook_output(replay_path)

    assert len(output.trajectory_3d) == 1
    assert output.trajectory_3d[0].x_m == 0.0
