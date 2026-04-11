from brambhand.scenario.replay_log import ReplayLog
from brambhand.visualization.quicklook_pipeline import build_headless_quicklook_output
from brambhand.visualization.trajectory_render_contracts import (
    CURRENT_OBJECT_COLOR_HEX,
    CURRENT_TRAJECTORY_COLOR_HEX,
    PLANNED_OBJECT_COLOR_HEX,
    PLANNED_TRAJECTORY_COLOR_HEX,
    TRAJECTORY_RENDER_SCHEMA_VERSION,
    TrajectoryRenderContract3D,
    build_trajectory_render_contract_3d,
)


def test_trajectory_render_contract_builds_current_and_planned_3d_curves() -> None:
    replay = ReplayLog.empty()
    replay.append(
        0.0,
        "step",
        {"position_m": [0.0, 0.0, 0.0], "planned_position_m": [0.5, 0.5, 0.0]},
    )
    replay.append(
        1.0,
        "step",
        {"position_m": [1.0, 2.0, 3.0], "planned_position_m": [1.5, 2.5, 3.0]},
    )

    quicklook = build_headless_quicklook_output(replay)
    render = build_trajectory_render_contract_3d(quicklook)

    assert render.schema_version == TRAJECTORY_RENDER_SCHEMA_VERSION
    assert len(render.curves) == 2
    assert render.curves[0].name == "current_trajectory"
    assert render.curves[0].color_hex == CURRENT_TRAJECTORY_COLOR_HEX
    assert render.curves[1].name == "planned_trajectory"
    assert render.curves[1].color_hex == PLANNED_TRAJECTORY_COLOR_HEX
    assert len(render.curves[0].points) == 2
    assert len(render.curves[1].points) == 2

    assert len(render.moving_objects) == 2
    assert render.moving_objects[0].name == "current_vehicle"
    assert render.moving_objects[0].color_hex == CURRENT_OBJECT_COLOR_HEX
    assert render.moving_objects[0].x_m == 1.0
    assert render.moving_objects[1].name == "planned_vehicle"
    assert render.moving_objects[1].color_hex == PLANNED_OBJECT_COLOR_HEX
    assert render.moving_objects[1].x_m == 1.5


def test_trajectory_render_contract_samples_marker_at_requested_time() -> None:
    replay = ReplayLog.empty()
    replay.append(
        0.0,
        "step",
        {"position_m": [0.0, 0.0, 0.0], "planned_position_m": [0.5, 0.5, 0.0]},
    )
    replay.append(
        1.0,
        "step",
        {"position_m": [10.0, 0.0, 0.0], "planned_position_m": [10.5, 0.5, 0.0]},
    )
    quicklook = build_headless_quicklook_output(replay)

    render = build_trajectory_render_contract_3d(quicklook, sim_time_s=0.4)

    assert render.moving_objects[0].x_m == 0.0
    assert render.moving_objects[1].x_m == 0.5


def test_trajectory_render_contract_rejects_unsupported_schema_version() -> None:
    try:
        TrajectoryRenderContract3D(schema_version=999, curves=(), moving_objects=())
    except ValueError as exc:
        assert "schema_version" in str(exc)
    else:
        raise AssertionError("Expected trajectory render schema-version validation failure")
