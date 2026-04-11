import math

from scipy.constants import g

from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.vector import Vector3
from brambhand.spacecraft.mass_model import MassModel
from brambhand.spacecraft.propulsion import PropulsionSystem


def test_propulsion_delta_v_matches_tsiolkovsky_equation() -> None:
    propulsion = PropulsionSystem(max_thrust_n=20_000.0, specific_impulse_s=320.0)
    mass = MassModel(dry_mass_kg=800.0, propellant_mass_kg=200.0)
    body = PhysicalBody(
        name="veh",
        mass=mass.total_mass_kg,
        state=InertialState(position=Vector3(0.0, 0.0, 0.0), velocity=Vector3(0.0, 0.0, 0.0)),
    )

    throttle = 0.8
    duration_s = 10.0

    mdot = (propulsion.max_thrust_n * throttle) / (320.0 * g)
    expected_consumed = mdot * duration_s
    expected_m1 = mass.total_mass_kg - expected_consumed
    expected_dv = 320.0 * g * math.log(mass.total_mass_kg / expected_m1)

    result = propulsion.apply_burn(
        body=body,
        mass_model=mass,
        direction=Vector3(1.0, 0.0, 0.0),
        throttle=throttle,
        duration_s=duration_s,
    )

    assert math.isclose(result.consumed_propellant_kg, expected_consumed, rel_tol=1e-12)
    assert math.isclose(result.body.mass, expected_m1, rel_tol=1e-12)
    assert math.isclose(result.delta_v_mps.x, expected_dv, rel_tol=1e-12)


def test_propulsion_handles_propellant_depletion() -> None:
    propulsion = PropulsionSystem(max_thrust_n=100_000.0, specific_impulse_s=300.0)
    mass = MassModel(dry_mass_kg=100.0, propellant_mass_kg=1.0)
    body = PhysicalBody(
        name="veh",
        mass=mass.total_mass_kg,
        state=InertialState(position=Vector3(0.0, 0.0, 0.0), velocity=Vector3(0.0, 0.0, 0.0)),
    )

    result = propulsion.apply_burn(
        body=body,
        mass_model=mass,
        direction=Vector3(0.0, 1.0, 0.0),
        throttle=1.0,
        duration_s=30.0,
    )

    assert math.isclose(result.mass_model.propellant_mass_kg, 0.0)
    assert result.burned_duration_s < 30.0
