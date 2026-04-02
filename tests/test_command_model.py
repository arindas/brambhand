import math

from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.vector import Vector3
from brambhand.spacecraft.command_model import BurnCommand, CommandModel
from brambhand.spacecraft.mass_model import MassModel
from brambhand.spacecraft.propulsion import PropulsionSystem


def test_command_model_applies_burn_only_for_window_overlap() -> None:
    cmd_model = CommandModel()
    cmd_model.add_burn(
        BurnCommand(
            start_time_s=5.0,
            duration_s=10.0,
            throttle=0.5,
            direction=Vector3(1.0, 0.0, 0.0),
        )
    )

    propulsion = PropulsionSystem(max_thrust_n=10_000.0, specific_impulse_s=300.0)
    mass = MassModel(dry_mass_kg=100.0, propellant_mass_kg=50.0)
    body = PhysicalBody(
        name="veh",
        mass=mass.total_mass_kg,
        state=InertialState(position=Vector3(0.0, 0.0, 0.0), velocity=Vector3(0.0, 0.0, 0.0)),
    )

    # Window [0, 4] should not overlap command [5, 15]
    body0, mass0, burns0 = cmd_model.apply_window(0.0, 4.0, body, mass, propulsion)
    assert burns0 == []
    assert body0 == body
    assert mass0 == mass

    # Window [10, 12] overlaps for 2 seconds
    body1, mass1, burns1 = cmd_model.apply_window(10.0, 2.0, body, mass, propulsion)
    assert len(burns1) == 1
    assert math.isclose(burns1[0].burned_duration_s, 2.0)
    assert mass1.propellant_mass_kg < mass.propellant_mass_kg
    assert body1.state.velocity.x > 0.0
