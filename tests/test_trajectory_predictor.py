from brambhand.guidance.trajectory_predictor import TrajectoryPredictor
from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.gravity_model import NBodyGravityModel
from brambhand.physics.integrator import VelocityVerletIntegrator
from brambhand.physics.vector import Vector3


def test_trajectory_predictor_matches_integrator_step() -> None:
    integrator = VelocityVerletIntegrator(gravity_model=NBodyGravityModel())
    predictor = TrajectoryPredictor(integrator=integrator)

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
    predicted = predictor.predict(bodies=bodies, dt_s=10.0, steps=1)
    stepped = integrator.step(bodies, 10.0)

    assert len(predicted) == 1
    assert predicted[0] == stepped
