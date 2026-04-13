import math

from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.vector import Vector3
from brambhand.spacecraft.mass_model import MassModel
from brambhand.spacecraft.propulsion import PropulsionSystem
from brambhand.trajectory.maneuver_contracts import (
    MANEUVER_SCHEMA_VERSION,
    ManeuverCommand,
    ManeuverMode,
)
from brambhand.trajectory.maneuver_executor import ManeuverExecutor


def _make_body_and_mass() -> tuple[PhysicalBody, MassModel]:
    mass = MassModel(dry_mass_kg=100.0, propellant_mass_kg=50.0)
    body = PhysicalBody(
        name="probe",
        mass=mass.total_mass_kg,
        state=InertialState(position=Vector3(0.0, 0.0, 0.0), velocity=Vector3(0.0, 0.0, 0.0)),
    )
    return body, mass


def test_impulsive_command_applies_once_at_requested_tick() -> None:
    body, mass = _make_body_and_mass()
    propulsion = PropulsionSystem(max_thrust_n=1_000.0, specific_impulse_s=250.0)
    executor = ManeuverExecutor()
    cmd = ManeuverCommand(
        schema_version=MANEUVER_SCHEMA_VERSION,
        command_id="sep-1",
        body_id="probe",
        requested_tick=3,
        mode=ManeuverMode.IMPULSIVE,
        direction=Vector3(1.0, 0.0, 0.0),
        delta_v_mps=12.0,
    )

    b0, m0, r0 = executor.apply_tick(2, 1.0, body, mass, propulsion, [cmd])
    assert b0 == body
    assert m0 == mass
    assert r0 == []

    b1, m1, r1 = executor.apply_tick(3, 1.0, body, mass, propulsion, [cmd])
    assert len(r1) == 1
    assert math.isclose(b1.state.velocity.x, 12.0)
    assert m1 == mass

    b2, m2, r2 = executor.apply_tick(3, 1.0, b1, m1, propulsion, [cmd])
    assert r2 == []
    assert b2 == b1


def test_finite_burn_consumes_propellant_and_is_segment_idempotent() -> None:
    body, mass = _make_body_and_mass()
    propulsion = PropulsionSystem(max_thrust_n=5_000.0, specific_impulse_s=300.0)
    executor = ManeuverExecutor()
    cmd = ManeuverCommand(
        schema_version=MANEUVER_SCHEMA_VERSION,
        command_id="burn-1",
        body_id="probe",
        requested_tick=5,
        mode=ManeuverMode.FINITE_BURN_CONSTANT_THRUST,
        direction=Vector3(0.0, 1.0, 0.0),
        throttle=0.4,
        duration_ticks=3,
    )

    b = body
    m = mass
    total_records = 0
    for tick in range(4, 9):
        b, m, records = executor.apply_tick(tick, 2.0, b, m, propulsion, [cmd])
        total_records += len(records)

    assert total_records == 3
    assert b.state.velocity.y > 0.0
    assert m.propellant_mass_kg < mass.propellant_mass_kg

    # Re-applying a processed segment should be idempotent.
    b2, m2, r2 = executor.apply_tick(6, 2.0, b, m, propulsion, [cmd])
    assert r2 == []
    assert b2 == b
    assert m2 == m


def test_finite_burn_reports_propellant_depleted_termination_reason() -> None:
    mass = MassModel(dry_mass_kg=100.0, propellant_mass_kg=0.01)
    body = PhysicalBody(
        name="probe",
        mass=mass.total_mass_kg,
        state=InertialState(position=Vector3(0.0, 0.0, 0.0), velocity=Vector3(0.0, 0.0, 0.0)),
    )
    propulsion = PropulsionSystem(max_thrust_n=20_000.0, specific_impulse_s=300.0)
    executor = ManeuverExecutor()
    cmd = ManeuverCommand(
        schema_version=MANEUVER_SCHEMA_VERSION,
        command_id="burn-deplete",
        body_id="probe",
        requested_tick=1,
        mode=ManeuverMode.FINITE_BURN_CONSTANT_THRUST,
        direction=Vector3(1.0, 0.0, 0.0),
        throttle=1.0,
        duration_ticks=1,
    )

    _, _, records = executor.apply_tick(1, 5.0, body, mass, propulsion, [cmd])
    assert len(records) == 1
    assert records[0].termination_reason == "propellant_depleted"
