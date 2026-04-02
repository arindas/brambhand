import json

from brambhand.cli import build_parser, replay_summary, validate_scenario
from brambhand.scenario.replay_log import ReplayLog


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


def test_validate_scenario_command_flow(tmp_path) -> None:
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "metadata": {"name": "validate-demo"},
                "bodies": [
                    {
                        "name": "earth",
                        "mass": 5.972e24,
                        "state": {"position": [0, 0, 0], "velocity": [0, 0, 0]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    scenario = validate_scenario(scenario_path)
    assert scenario.metadata.name == "validate-demo"
