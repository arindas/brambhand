import math

from scipy.constants import c

from brambhand.communication.delay_channel import DelayChannel
from brambhand.communication.link_model import LinkModel
from brambhand.communication.visibility import SphericalOccluder, line_of_sight_clear
from brambhand.physics.vector import Vector3


def test_line_of_sight_blocked_by_occluder() -> None:
    a = Vector3(-10.0, 0.0, 0.0)
    b = Vector3(10.0, 0.0, 0.0)
    occluder = SphericalOccluder(center_m=Vector3(0.0, 0.0, 0.0), radius_m=2.0)

    assert not line_of_sight_clear(a, b, [occluder])


def test_link_model_reports_delay_when_available() -> None:
    link = LinkModel(max_range_m=1_000_000.0)
    tx = Vector3(0.0, 0.0, 0.0)
    rx = Vector3(300_000.0, 400_000.0, 0.0)

    state = link.evaluate(tx, rx, occluders=[])

    assert state.available
    assert state.one_way_delay_s is not None
    assert math.isclose(state.one_way_delay_s, 500_000.0 / c, rel_tol=1e-12)


def test_delay_channel_and_link_integration_for_uplink_downlink() -> None:
    link = LinkModel(max_range_m=10_000_000.0)
    tx = Vector3(0.0, 0.0, 0.0)
    rx = Vector3(3_000_000.0, 0.0, 0.0)
    state = link.evaluate(tx, rx, occluders=[])

    assert state.available
    assert state.one_way_delay_s is not None

    uplink: DelayChannel[str] = DelayChannel()
    downlink: DelayChannel[str] = DelayChannel()

    t0 = 100.0
    uplink.send("BURN_CMD", current_time_s=t0, delay_s=state.one_way_delay_s)

    # Not arrived yet
    assert uplink.receive_ready(t0 + state.one_way_delay_s * 0.5) == []

    # Arrived after delay
    cmd_msgs = uplink.receive_ready(t0 + state.one_way_delay_s)
    assert cmd_msgs == ["BURN_CMD"]

    # Telemetry response travels back with same delay
    downlink.send("ACK", current_time_s=t0 + state.one_way_delay_s, delay_s=state.one_way_delay_s)
    ack_msgs = downlink.receive_ready(t0 + 2.0 * state.one_way_delay_s + 1e-12)
    assert ack_msgs == ["ACK"]
