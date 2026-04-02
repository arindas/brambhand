from brambhand.core.event_bus import Event, EventBus
from brambhand.core.state_snapshot import StateSnapshot, build_state_snapshot
from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.gravity_model import NBodyGravityModel
from brambhand.physics.integrator import VelocityVerletIntegrator
from brambhand.physics.vector import Vector3


def _run_simulation() -> list[StateSnapshot]:
    event_bus = EventBus()
    integrator = VelocityVerletIntegrator(gravity_model=NBodyGravityModel())

    earth = PhysicalBody(
        name="earth",
        mass=5.972e24,
        state=InertialState(
            position=Vector3(0.0, 0.0, 0.0),
            velocity=Vector3(0.0, 0.0, 0.0),
        ),
    )
    sat = PhysicalBody(
        name="sat",
        mass=1_000.0,
        state=InertialState(
            position=Vector3(7_000_000.0, 0.0, 0.0),
            velocity=Vector3(0.0, 7_500.0, 0.0),
        ),
    )

    bodies = [earth, sat]
    snapshots: list[StateSnapshot] = []

    sim_time = 0.0
    dt = 10.0
    steps = 50

    event_bus.emit(Event(sim_time_s=sim_time, kind="simulation_started", payload={"dt": dt}))

    for step in range(steps):
        bodies = integrator.step(bodies, dt)
        sim_time += dt
        event_bus.emit(
            Event(
                sim_time_s=sim_time,
                kind="step_completed",
                payload={"step": step + 1},
            )
        )
        snapshots.append(
            build_state_snapshot(
                sim_time_s=sim_time,
                bodies=bodies,
                events=event_bus.snapshot(),
            )
        )

    return snapshots


def test_deterministic_replay_produces_identical_snapshots() -> None:
    first_run = _run_simulation()
    second_run = _run_simulation()

    assert first_run == second_run
