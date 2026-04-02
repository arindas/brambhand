from brambhand.cli import run_scenario
from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.vector import Vector3
from brambhand.scenario.scenario_schema import SCENARIO_SCHEMA_VERSION, Scenario, ScenarioMetadata


def test_run_scenario_returns_body_summaries_and_replay() -> None:
    scenario = Scenario(
        schema_version=SCENARIO_SCHEMA_VERSION,
        metadata=ScenarioMetadata(name="cli-smoke"),
        bodies=(
            PhysicalBody(
                name="earth",
                mass=5.972e24,
                state=InertialState(
                    position=Vector3(0.0, 0.0, 0.0),
                    velocity=Vector3(0.0, 0.0, 0.0),
                ),
            ),
            PhysicalBody(
                name="sat",
                mass=1000.0,
                state=InertialState(
                    position=Vector3(7_000_000.0, 0.0, 0.0),
                    velocity=Vector3(0.0, 7_500.0, 0.0),
                ),
            ),
        ),
    )

    summaries, replay = run_scenario(scenario=scenario, dt_s=5.0, steps=3)

    assert len(summaries) == 2
    assert len(replay.records) == 4
    assert replay.records[0].kind == "simulation_started"
    assert replay.records[-1].kind == "step_completed"
