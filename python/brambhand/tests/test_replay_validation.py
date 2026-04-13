from brambhand.physics.vector import Vector3
from brambhand.trajectory.replay_validation import (
    detect_uncommanded_discontinuities,
    validate_replay_probe_continuity,
)


def test_detect_uncommanded_discontinuity_when_jump_without_command() -> None:
    positions = [
        Vector3(0.0, 0.0, 0.0),
        Vector3(10.0, 0.0, 0.0),
        Vector3(20.0, 0.0, 0.0),
        Vector3(2000.0, 0.0, 0.0),
    ]
    discontinuities = detect_uncommanded_discontinuities(positions, commanded_ticks=set())
    assert len(discontinuities) == 1
    assert discontinuities[0].tick == 3


def test_no_discontinuity_when_jump_at_command_tick() -> None:
    positions = [
        Vector3(0.0, 0.0, 0.0),
        Vector3(10.0, 0.0, 0.0),
        Vector3(20.0, 0.0, 0.0),
        Vector3(2000.0, 0.0, 0.0),
    ]
    discontinuities = detect_uncommanded_discontinuities(positions, commanded_ticks={3})
    assert discontinuities == []


def test_validate_replay_probe_continuity_uses_maneuver_records() -> None:
    frames = [
        {
            "tick_id": 0,
            "bodies": [{"body_id": "mars_probe", "position_m": {"x": 0.0, "y": 0.0, "z": 0.0}}],
            "maneuver_records": [],
        },
        {
            "tick_id": 1,
            "bodies": [{"body_id": "mars_probe", "position_m": {"x": 10.0, "y": 0.0, "z": 0.0}}],
            "maneuver_records": [],
        },
        {
            "tick_id": 2,
            "bodies": [{"body_id": "mars_probe", "position_m": {"x": 20.0, "y": 0.0, "z": 0.0}}],
            "maneuver_records": [],
        },
        {
            "tick_id": 3,
            "bodies": [{"body_id": "mars_probe", "position_m": {"x": 2000.0, "y": 0.0, "z": 0.0}}],
            "maneuver_records": [{"body_id": "mars_probe", "delta_v_applied_mps": 50.0}],
        },
    ]

    discontinuities = validate_replay_probe_continuity(frames)
    assert discontinuities == []


def test_validate_replay_probe_continuity_reports_uncommanded_jump() -> None:
    frames = [
        {
            "tick_id": 0,
            "bodies": [{"body_id": "mars_probe", "position_m": {"x": 0.0, "y": 0.0, "z": 0.0}}],
            "maneuver_records": [],
        },
        {
            "tick_id": 1,
            "bodies": [{"body_id": "mars_probe", "position_m": {"x": 10.0, "y": 0.0, "z": 0.0}}],
            "maneuver_records": [],
        },
        {
            "tick_id": 2,
            "bodies": [{"body_id": "mars_probe", "position_m": {"x": 20.0, "y": 0.0, "z": 0.0}}],
            "maneuver_records": [],
        },
        {
            "tick_id": 3,
            "bodies": [{"body_id": "mars_probe", "position_m": {"x": 2000.0, "y": 0.0, "z": 0.0}}],
            "maneuver_records": [],
        },
    ]

    discontinuities = validate_replay_probe_continuity(frames)
    assert len(discontinuities) == 1
    assert discontinuities[0].tick == 3
