import math

from scipy.constants import G

from brambhand.guidance.orbit_elements import cartesian_to_keplerian, keplerian_to_cartesian
from brambhand.physics.body import InertialState
from brambhand.physics.vector import Vector3


def test_cartesian_keplerian_roundtrip() -> None:
    mu = G * 5.972e24
    original = InertialState(
        position=Vector3(7_000_000.0, 500_000.0, 300_000.0),
        velocity=Vector3(-500.0, 7_400.0, 900.0),
    )

    elements = cartesian_to_keplerian(original, mu)
    reconstructed = keplerian_to_cartesian(elements, mu)

    assert math.isclose(reconstructed.position.x, original.position.x, rel_tol=1e-7)
    assert math.isclose(reconstructed.position.y, original.position.y, rel_tol=1e-7)
    assert math.isclose(reconstructed.position.z, original.position.z, rel_tol=1e-7)
    assert math.isclose(reconstructed.velocity.x, original.velocity.x, rel_tol=1e-7)
    assert math.isclose(reconstructed.velocity.y, original.velocity.y, rel_tol=1e-7)
    assert math.isclose(reconstructed.velocity.z, original.velocity.z, rel_tol=1e-7)
