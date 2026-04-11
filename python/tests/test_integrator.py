import math

from scipy.constants import G

from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.gravity_model import NBodyGravityModel
from brambhand.physics.integrator import VelocityVerletIntegrator
from brambhand.physics.vector import Vector3


def test_circular_orbit_radius_remains_bounded() -> None:
    earth_mu = G * 5.972e24
    orbit_r = 6_771_000.0
    orbit_v = math.sqrt(earth_mu / orbit_r)

    earth = PhysicalBody(
        name="earth",
        mass=5.972e24,
        state=InertialState(
            position=Vector3(0.0, 0.0, 0.0),
            velocity=Vector3(0.0, 0.0, 0.0),
        ),
    )
    satellite = PhysicalBody(
        name="sat",
        mass=1_000.0,
        state=InertialState(
            position=Vector3(orbit_r, 0.0, 0.0),
            velocity=Vector3(0.0, orbit_v, 0.0),
        ),
    )

    integrator = VelocityVerletIntegrator(gravity_model=NBodyGravityModel())
    bodies = [earth, satellite]

    dt = 5.0
    steps = 1200  # 100 minutes

    for _ in range(steps):
        bodies = integrator.step(bodies, dt)

    final_sat = next(body for body in bodies if body.name == "sat")
    final_radius = final_sat.state.position.norm()

    assert math.isclose(final_radius, orbit_r, rel_tol=2e-3)
