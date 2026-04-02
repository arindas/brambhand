import math

from brambhand.operations.rendezvous_metrics import compute_rendezvous_metrics
from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.vector import Vector3


def test_rendezvous_metrics_computation() -> None:
    target = PhysicalBody(
        name="target",
        mass=10_000.0,
        state=InertialState(
            position=Vector3(1000.0, 0.0, 0.0),
            velocity=Vector3(0.0, 7.5, 0.0),
        ),
    )
    chaser = PhysicalBody(
        name="chaser",
        mass=5_000.0,
        state=InertialState(
            position=Vector3(1100.0, 0.0, 0.0),
            velocity=Vector3(-1.0, 7.5, 0.0),
        ),
    )

    metrics = compute_rendezvous_metrics(chaser, target)

    assert math.isclose(metrics.range_m, 100.0)
    assert math.isclose(metrics.relative_velocity_mps.x, -1.0)
    assert metrics.closing_rate_mps > 0.0
