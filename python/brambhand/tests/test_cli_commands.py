import json

from brambhand.cli import build_parser, main, replay_summary, run_scenario, validate_scenario
from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.vector import Vector3
from brambhand.scenario.replay_log import ReplayLog
from brambhand.scenario.scenario_schema import SCENARIO_SCHEMA_VERSION, Scenario, ScenarioMetadata


def test_build_parser_parses_run_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "scenario.json", "--dt", "5", "--steps", "3"])

    assert args.command == "run"
    assert str(args.scenario).endswith("scenario.json")
    assert args.dt == 5.0
    assert args.steps == 3


def test_build_parser_parses_replay_command() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "replay",
            "replay.jsonl",
            "--kind",
            "step_completed",
            "--start-time",
            "10",
            "--end-time",
            "20",
        ]
    )

    assert args.command == "replay"
    assert str(args.replay).endswith("replay.jsonl")
    assert args.kind == "step_completed"
    assert args.start_time == 10.0
    assert args.end_time == 20.0


def test_replay_summary_filters_by_kind_and_time() -> None:
    replay = ReplayLog.empty()
    replay.append(sim_time_s=0.0, kind="simulation_started", payload={"dt_s": 5.0})
    replay.append(sim_time_s=5.0, kind="step_completed", payload={"step": 1})
    replay.append(sim_time_s=10.0, kind="step_completed", payload={"step": 2})

    lines = replay_summary(
        replay,
        kind="step_completed",
        start_time_s=6.0,
        end_time_s=10.0,
    )

    assert len(lines) == 1
    assert '"step": 2' in lines[0]


def _write_minimal_scenario(path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "metadata": {"name": "validate-demo"},
                "bodies": [
                    {
                        "name": "earth",
                        "mass": 5.972e24,
                        "state": {"position": [0, 0, 0], "velocity": [0, 0, 0]},
                    },
                    {
                        "name": "sat",
                        "mass": 1000,
                        "state": {"position": [7000000, 0, 0], "velocity": [0, 7500, 0]},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_validate_scenario_command_flow(tmp_path) -> None:
    scenario_path = tmp_path / "scenario.json"
    _write_minimal_scenario(scenario_path)

    scenario = validate_scenario(scenario_path)
    assert scenario.metadata.name == "validate-demo"


def test_run_scenario_rejects_invalid_dt_and_steps() -> None:
    scenario = Scenario(
        schema_version=SCENARIO_SCHEMA_VERSION,
        metadata=ScenarioMetadata(name="cli-invalid"),
        bodies=(
            PhysicalBody(
                name="earth",
                mass=5.972e24,
                state=InertialState(
                    position=Vector3(0.0, 0.0, 0.0),
                    velocity=Vector3(0.0, 0.0, 0.0),
                ),
            ),
        ),
    )

    try:
        run_scenario(scenario=scenario, dt_s=0.0, steps=1)
    except ValueError as exc:
        assert "dt_s must be positive" in str(exc)
    else:
        raise AssertionError("Expected dt_s validation error")

    try:
        run_scenario(scenario=scenario, dt_s=1.0, steps=-1)
    except ValueError as exc:
        assert "steps must be non-negative" in str(exc)
    else:
        raise AssertionError("Expected steps validation error")


def test_cli_main_validate_run_and_replay_flows(tmp_path, monkeypatch, capsys) -> None:
    scenario_path = tmp_path / "scenario.json"
    replay_path = tmp_path / "replay.jsonl"
    _write_minimal_scenario(scenario_path)

    monkeypatch.setattr("sys.argv", ["brambhand", "validate", str(scenario_path)])
    assert main() == 0
    out = capsys.readouterr().out
    assert "scenario_valid=true" in out

    monkeypatch.setattr(
        "sys.argv",
        [
            "brambhand",
            "run",
            str(scenario_path),
            "--dt",
            "5",
            "--steps",
            "2",
            "--replay-out",
            str(replay_path),
        ],
    )
    assert main() == 0
    out = capsys.readouterr().out
    assert "replay_saved=" in out
    assert replay_path.exists()

    monkeypatch.setattr(
        "sys.argv",
        [
            "brambhand",
            "replay",
            str(replay_path),
            "--kind",
            "step_completed",
            "--start-time",
            "0",
            "--end-time",
            "20",
        ],
    )
    assert main() == 0
    out = capsys.readouterr().out
    assert "replay_records=" in out
