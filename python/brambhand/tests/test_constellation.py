from brambhand.operations.constellation import (
    MissionConfig,
    SatelliteConstellation,
    SatelliteMember,
)


def test_constellation_rejects_invalid_configuration() -> None:
    try:
        MissionConfig(mission_name="", control_center="ground-a", telemetry_period_s=5.0)
    except ValueError as exc:
        assert "mission_name" in str(exc)
    else:
        raise AssertionError("Expected mission config validation failure")

    cfg = MissionConfig(mission_name="leo-net", control_center="ground-a", telemetry_period_s=5.0)

    try:
        SatelliteConstellation(name="", mission_config=cfg, members=(
            SatelliteMember(vehicle_name="sat-1", role="relay", orbital_slot=1),
        ))
    except ValueError as exc:
        assert "constellation name" in str(exc)
    else:
        raise AssertionError("Expected constellation name validation failure")

    try:
        SatelliteConstellation(
            name="dup-names",
            mission_config=cfg,
            members=(
                SatelliteMember(vehicle_name="sat-1", role="relay", orbital_slot=1),
                SatelliteMember(vehicle_name="sat-1", role="relay", orbital_slot=2),
            ),
        )
    except ValueError as exc:
        assert "member names must be unique" in str(exc)
    else:
        raise AssertionError("Expected duplicate-name validation failure")

    try:
        SatelliteConstellation(
            name="dup-slots",
            mission_config=cfg,
            members=(
                SatelliteMember(vehicle_name="sat-1", role="relay", orbital_slot=1),
                SatelliteMember(vehicle_name="sat-2", role="relay", orbital_slot=1),
            ),
        )
    except ValueError as exc:
        assert "orbital slots must be unique" in str(exc)
    else:
        raise AssertionError("Expected duplicate-slot validation failure")


def test_constellation_grouping_and_shared_config() -> None:
    cfg = MissionConfig(mission_name="leo-net", control_center="ground-a", telemetry_period_s=5.0)
    constellation = SatelliteConstellation(
        name="leo-cluster",
        mission_config=cfg,
        members=(
            SatelliteMember(vehicle_name="sat-1", role="relay", orbital_slot=1),
            SatelliteMember(vehicle_name="sat-2", role="relay", orbital_slot=2),
            SatelliteMember(vehicle_name="sat-3", role="imaging", orbital_slot=3),
        ),
    )

    assert constellation.mission_config.control_center == "ground-a"
    assert constellation.member_names() == ("sat-1", "sat-2", "sat-3")
    relay_names = tuple(m.vehicle_name for m in constellation.members_by_role("relay"))
    assert relay_names == ("sat-1", "sat-2")
