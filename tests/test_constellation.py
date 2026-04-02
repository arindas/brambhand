from brambhand.operations.constellation import (
    MissionConfig,
    SatelliteConstellation,
    SatelliteMember,
)


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
