import math

from scipy.constants import G

from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.gravity_model import NBodyGravityModel
from brambhand.physics.vector import Vector3


def test_two_body_accelerations_match_newtonian_solution() -> None:
    earth = PhysicalBody(
        name="earth",
        mass=5.972e24,
        state=InertialState(
            position=Vector3(0.0, 0.0, 0.0),
            velocity=Vector3(0.0, 0.0, 0.0),
        ),
    )
    moon = PhysicalBody(
        name="moon",
        mass=7.34767309e22,
        state=InertialState(
            position=Vector3(384_400_000.0, 0.0, 0.0),
            velocity=Vector3(0.0, 0.0, 0.0),
        ),
    )

    model = NBodyGravityModel()
    acc = model.accelerations([earth, moon])

    expected_earth = G * moon.mass / (384_400_000.0**2)
    expected_moon = G * earth.mass / (384_400_000.0**2)

    assert math.isclose(acc[0].x, expected_earth, rel_tol=1e-12)
    assert math.isclose(acc[1].x, -expected_moon, rel_tol=1e-12)
    assert math.isclose(acc[0].y, 0.0, abs_tol=1e-18)
    assert math.isclose(acc[0].z, 0.0, abs_tol=1e-18)
