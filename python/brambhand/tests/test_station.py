import pytest

from brambhand.infrastructure.station import DockingPort, OrbitalStation, ResourceInterface


def _station() -> OrbitalStation:
    return OrbitalStation(
        name="alpha",
        ports=(
            DockingPort(port_id="A", compatible_vehicle_classes=("crew", "cargo")),
            DockingPort(port_id="B", compatible_vehicle_classes=("cargo",)),
        ),
        resources=(
            ResourceInterface(
                resource_name="propellant",
                capacity=1000.0,
                available=400.0,
                unit="kg",
            ),
            ResourceInterface(
                resource_name="power",
                capacity=100.0,
                available=60.0,
                unit="kWh",
            ),
        ),
    )


def test_station_docking_and_undocking() -> None:
    station = _station()

    station, port_id = station.dock(vehicle_id="cargo-1", vehicle_class="cargo")
    assert port_id == "A"

    station, port_id2 = station.dock(vehicle_id="cargo-2", vehicle_class="cargo")
    assert port_id2 == "B"

    station = station.undock("cargo-1")
    assert station.ports[0].occupied_by is None


def test_station_rejects_incompatible_vehicle() -> None:
    station = _station()
    with pytest.raises(ValueError, match="No compatible free docking port"):
        station.dock(vehicle_id="probe-1", vehicle_class="probe")


def test_station_resource_transfer() -> None:
    station = _station()

    station, transferred = station.transfer_resource("propellant", 150.0)
    assert transferred == 150.0
    propellant = next(r for r in station.resources if r.resource_name == "propellant")
    assert propellant.available == 250.0

    station, transferred2 = station.transfer_resource("propellant", 500.0)
    assert transferred2 == 250.0
    propellant2 = next(r for r in station.resources if r.resource_name == "propellant")
    assert propellant2.available == 0.0
