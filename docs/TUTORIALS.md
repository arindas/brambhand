# Tutorials

This page contains guided tutorials for common usage patterns.

---

## Tutorial 1: First simulation from scratch

### Goal
Create a scenario, validate it, run it, and inspect replay output.

### Step 1: create scenario file
Save as `tutorial-1.json`:

```json
{
  "schema_version": "1.0",
  "metadata": {"name": "tutorial-1"},
  "bodies": [
    {
      "name": "earth",
      "mass": 5.972e24,
      "state": {"position": [0, 0, 0], "velocity": [0, 0, 0]}
    },
    {
      "name": "sat",
      "mass": 1000,
      "state": {"position": [7000000, 0, 0], "velocity": [0, 7500, 0]}
    }
  ]
}
```

### Step 2: validate

```bash
brambhand validate tutorial-1.json
```

### Step 3: run

```bash
brambhand run tutorial-1.json --dt 5 --steps 20 --replay-out tutorial-1-replay.jsonl
```

### Step 4: inspect replay

```bash
brambhand replay tutorial-1-replay.jsonl --kind step_completed
```

---

## Tutorial 2: Python API workflow (programmatic run)

### Goal
Run a short simulation directly through Python APIs.

```python
from brambhand.cli import run_scenario
from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.vector import Vector3
from brambhand.scenario.scenario_schema import SCENARIO_SCHEMA_VERSION, Scenario, ScenarioMetadata

scenario = Scenario(
    schema_version=SCENARIO_SCHEMA_VERSION,
    metadata=ScenarioMetadata(name="api-run"),
    bodies=(
        PhysicalBody(
            name="earth",
            mass=5.972e24,
            state=InertialState(position=Vector3(0.0, 0.0, 0.0), velocity=Vector3(0.0, 0.0, 0.0)),
        ),
        PhysicalBody(
            name="sat",
            mass=1000.0,
            state=InertialState(position=Vector3(7_000_000.0, 0.0, 0.0), velocity=Vector3(0.0, 7500.0, 0.0)),
        ),
    ),
)

summaries, replay = run_scenario(scenario, dt_s=10.0, steps=5)
print(summaries)
print(len(replay.records))
```

---

## Tutorial 3: Mission ops workflow (rendezvous + docking)

### Goal
Evaluate whether a chaser-target geometry satisfies docking constraints.

```python
from brambhand.operations.rendezvous_metrics import compute_rendezvous_metrics
from brambhand.operations.docking_model import DockingConfig, DockingModel
from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.vector import Vector3

chaser = PhysicalBody(
    name="chaser",
    mass=1000.0,
    state=InertialState(position=Vector3(0.4, 0.0, 0.0), velocity=Vector3(-0.1, 0.0, 0.0)),
)
target = PhysicalBody(
    name="target",
    mass=1000.0,
    state=InertialState(position=Vector3(0.0, 0.0, 0.0), velocity=Vector3(0.0, 0.0, 0.0)),
)

metrics = compute_rendezvous_metrics(chaser, target)
model = DockingModel(
    DockingConfig(
        capture_distance_m=0.5,
        max_capture_closing_speed_mps=0.2,
        max_capture_relative_speed_mps=0.25,
    )
)
status = model.evaluate(metrics)
print(status.state, status.reason)
```

---

## Tutorial 4: Constellation and station operations

### Goal
Group satellites under one mission config and execute station docking/resource actions.

```python
from brambhand.infrastructure.station import DockingPort, OrbitalStation, ResourceInterface
from brambhand.operations.constellation import MissionConfig, SatelliteConstellation, SatelliteMember

constellation = SatelliteConstellation(
    name="mesh",
    mission_config=MissionConfig("leo-mesh", "ground-a", telemetry_period_s=10.0),
    members=(
        SatelliteMember("sat-1", "relay", 1),
        SatelliteMember("sat-2", "relay", 2),
        SatelliteMember("sat-3", "imaging", 3),
    ),
)

station = OrbitalStation(
    name="alpha",
    ports=(DockingPort("A", ("cargo", "crew")), DockingPort("B", ("cargo",))),
    resources=(ResourceInterface("propellant", capacity=1000.0, available=400.0, unit="kg"),),
)
station, _ = station.dock("cargo-1", "cargo")
station, delivered = station.transfer_resource("propellant", 100.0)
print(constellation.member_names(), delivered)
```
