import pytest

from brambhand.physics.vector import Vector3
from brambhand.trajectory.handoff_contracts import (
    HandoffPhaseKind,
    SOIHandoffMetadata,
    TwoBodySOIHandoffMetadataProvider,
    build_soi_handoff_metadata,
)


def test_two_body_handoff_provider_is_deterministic() -> None:
    provider = TwoBodySOIHandoffMetadataProvider(
        mu_primary_m3_s2=4.282837e13,
        sphere_of_influence_radius_m=5.77e8,
    )

    first = build_soi_handoff_metadata(
        provider,
        phase_kind=HandoffPhaseKind.ENCOUNTER,
        body_id="mars_probe",
        primary_body_id="mars",
        tick_id=42,
        sim_time_s=3600.0,
        body_position_m=Vector3(9_000_000.0, 0.0, 0.0),
        body_velocity_mps=Vector3(0.0, 3200.0, 0.0),
        primary_position_m=Vector3(0.0, 0.0, 0.0),
        primary_velocity_mps=Vector3(0.0, 0.0, 0.0),
    )
    second = build_soi_handoff_metadata(
        provider,
        phase_kind=HandoffPhaseKind.ENCOUNTER,
        body_id="mars_probe",
        primary_body_id="mars",
        tick_id=42,
        sim_time_s=3600.0,
        body_position_m=Vector3(9_000_000.0, 0.0, 0.0),
        body_velocity_mps=Vector3(0.0, 3200.0, 0.0),
        primary_position_m=Vector3(0.0, 0.0, 0.0),
        primary_velocity_mps=Vector3(0.0, 0.0, 0.0),
    )

    assert first == second
    assert first.inside_sphere_of_influence


def test_two_body_handoff_flags_outside_soi() -> None:
    provider = TwoBodySOIHandoffMetadataProvider(
        mu_primary_m3_s2=4.282837e13,
        sphere_of_influence_radius_m=1.0e7,
    )

    metadata = provider.build_metadata(
        phase_kind=HandoffPhaseKind.CAPTURE_START,
        body_id="mars_probe",
        primary_body_id="mars",
        tick_id=50,
        sim_time_s=5000.0,
        body_position_m=Vector3(2.0e7, 0.0, 0.0),
        body_velocity_mps=Vector3(0.0, 1000.0, 0.0),
        primary_position_m=Vector3(0.0, 0.0, 0.0),
        primary_velocity_mps=Vector3(0.0, 0.0, 0.0),
    )

    assert not metadata.inside_sphere_of_influence


def test_metadata_contract_validation_rejects_invalid_schema() -> None:
    with pytest.raises(ValueError, match="schema_version"):
        SOIHandoffMetadata(
            schema_version=999,
            phase_kind=HandoffPhaseKind.INSERTION_COMPLETE,
            body_id="mars_probe",
            primary_body_id="mars",
            tick_id=1,
            sim_time_s=10.0,
            distance_to_primary_m=1000.0,
            relative_speed_mps=10.0,
            specific_orbital_energy_jkg=-1.0,
            sphere_of_influence_radius_m=100_000.0,
            inside_sphere_of_influence=True,
        )
