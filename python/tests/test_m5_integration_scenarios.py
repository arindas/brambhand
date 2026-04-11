from brambhand.guidance.trajectory_predictor import TrajectoryPredictor
from brambhand.infrastructure.station import DockingPort, OrbitalStation, ResourceInterface
from brambhand.operations.constellation import (
    MissionConfig,
    SatelliteConstellation,
    SatelliteMember,
)
from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.gravity_model import NBodyGravityModel
from brambhand.physics.integrator import VelocityVerletIntegrator
from brambhand.physics.vector import Vector3


def test_multi_satellite_constellation_scenario() -> None:
    constellation = SatelliteConstellation(
        name="mesh",
        mission_config=MissionConfig("leo-mesh", "ground-a", telemetry_period_s=10.0),
        members=(
            SatelliteMember("sat-1", "relay", 1),
            SatelliteMember("sat-2", "relay", 2),
            SatelliteMember("sat-3", "imaging", 3),
        ),
    )

    earth = PhysicalBody(
        name="earth",
        mass=5.972e24,
        state=InertialState(position=Vector3(0.0, 0.0, 0.0), velocity=Vector3(0.0, 0.0, 0.0)),
    )
    sats = [
        PhysicalBody(
            name=member.vehicle_name,
            mass=500.0,
            state=InertialState(
                position=Vector3(7_000_000.0 + 1_000.0 * member.orbital_slot, 0.0, 0.0),
                velocity=Vector3(0.0, 7_500.0, 0.0),
            ),
        )
        for member in constellation.members
    ]

    predictor = TrajectoryPredictor(VelocityVerletIntegrator(NBodyGravityModel()))
    frames = predictor.predict([earth, *sats], dt_s=5.0, steps=5)

    final_names = {body.name for body in frames[-1]}
    assert set(constellation.member_names()).issubset(final_names)


def test_station_operations_integration_scenario() -> None:
    station = OrbitalStation(
        name="orbital-alpha",
        ports=(
            DockingPort("port-1", ("cargo", "crew")),
            DockingPort("port-2", ("cargo",)),
        ),
        resources=(ResourceInterface("propellant", capacity=2000.0, available=600.0, unit="kg"),),
    )

    station, _ = station.dock("cargo-1", "cargo")
    station, _ = station.dock("cargo-2", "cargo")

    station, delivered = station.transfer_resource("propellant", 450.0)
    assert delivered == 450.0

    station = station.undock("cargo-2")
    assert any(port.occupied_by is None for port in station.ports)
