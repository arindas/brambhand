import json

import pytest

from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.vector import Vector3
from brambhand.scenario.scenario_loader import load_scenario, save_scenario
from brambhand.scenario.scenario_schema import SCENARIO_SCHEMA_VERSION, Scenario, ScenarioMetadata


def test_scenario_save_and_load_roundtrip(tmp_path) -> None:
    scenario = Scenario(
        schema_version=SCENARIO_SCHEMA_VERSION,
        metadata=ScenarioMetadata(name="earth-orbit", description="basic earth + sat scenario"),
        bodies=(
            PhysicalBody(
                name="earth",
                mass=5.972e24,
                state=InertialState(
                    position=Vector3(0.0, 0.0, 0.0), velocity=Vector3(0.0, 0.0, 0.0)
                ),
            ),
            PhysicalBody(
                name="sat",
                mass=1000.0,
                state=InertialState(
                    position=Vector3(7_000_000.0, 0.0, 0.0), velocity=Vector3(0.0, 7_500.0, 0.0)
                ),
            ),
        ),
    )

    path = tmp_path / "scenario.json"
    save_scenario(path, scenario)
    loaded = load_scenario(path)

    assert loaded == scenario


def test_scenario_loader_rejects_unsupported_version(tmp_path) -> None:
    path = tmp_path / "scenario.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "999.0",
                "metadata": {"name": "bad"},
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

    with pytest.raises(ValueError, match="Unsupported scenario schema_version"):
        load_scenario(path)
