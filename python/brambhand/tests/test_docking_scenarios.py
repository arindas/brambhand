from brambhand.operations.docking_model import DockingConfig, DockingModel, DockingState
from brambhand.operations.rendezvous_metrics import compute_rendezvous_metrics
from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.vector import Vector3


def _body(name: str, pos: Vector3, vel: Vector3) -> PhysicalBody:
    return PhysicalBody(
        name=name,
        mass=1_000.0,
        state=InertialState(position=pos, velocity=vel),
    )


def test_docking_success_scenario() -> None:
    model = DockingModel(
        DockingConfig(
            capture_distance_m=0.5,
            max_capture_closing_speed_mps=0.2,
            max_capture_relative_speed_mps=0.25,
        )
    )

    target = _body("target", Vector3(0.0, 0.0, 0.0), Vector3(0.0, 0.0, 0.0))
    chaser = _body("chaser", Vector3(0.4, 0.0, 0.0), Vector3(-0.1, 0.0, 0.0))

    metrics = compute_rendezvous_metrics(chaser, target)
    status = model.evaluate(metrics)

    assert status.state == DockingState.DOCKED


def test_docking_failure_due_to_excess_closing_rate() -> None:
    model = DockingModel(
        DockingConfig(
            capture_distance_m=0.5,
            max_capture_closing_speed_mps=0.2,
            max_capture_relative_speed_mps=0.25,
        )
    )

    target = _body("target", Vector3(0.0, 0.0, 0.0), Vector3(0.0, 0.0, 0.0))
    chaser = _body("chaser", Vector3(0.4, 0.0, 0.0), Vector3(-0.4, 0.0, 0.0))

    metrics = compute_rendezvous_metrics(chaser, target)
    status = model.evaluate(metrics)

    assert status.state == DockingState.FAILED
    assert status.reason == "closing_rate_too_high"


def test_docking_failure_due_to_receding_in_capture_zone() -> None:
    model = DockingModel(
        DockingConfig(
            capture_distance_m=0.5,
            max_capture_closing_speed_mps=0.2,
            max_capture_relative_speed_mps=0.25,
        )
    )

    target = _body("target", Vector3(0.0, 0.0, 0.0), Vector3(0.0, 0.0, 0.0))
    chaser = _body("chaser", Vector3(0.4, 0.0, 0.0), Vector3(0.05, 0.0, 0.0))

    metrics = compute_rendezvous_metrics(chaser, target)
    status = model.evaluate(metrics)

    assert status.state == DockingState.FAILED
    assert status.reason == "target_receding_inside_capture_zone"
