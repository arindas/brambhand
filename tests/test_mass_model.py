import math

from brambhand.spacecraft.mass_model import MassModel


def test_mass_model_total_and_consumption() -> None:
    mass = MassModel(dry_mass_kg=500.0, propellant_mass_kg=120.0)
    assert math.isclose(mass.total_mass_kg, 620.0)

    mass_after, used = mass.consume(20.0)
    assert math.isclose(used, 20.0)
    assert math.isclose(mass_after.propellant_mass_kg, 100.0)
    assert math.isclose(mass_after.total_mass_kg, 600.0)


def test_mass_model_consumption_saturates_at_available_propellant() -> None:
    mass = MassModel(dry_mass_kg=100.0, propellant_mass_kg=5.0)
    mass_after, used = mass.consume(9.0)

    assert math.isclose(used, 5.0)
    assert math.isclose(mass_after.propellant_mass_kg, 0.0)
