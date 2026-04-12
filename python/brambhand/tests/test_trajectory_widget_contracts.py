from brambhand.scenario.replay_log import ReplayLog
from brambhand.visualization.quicklook_pipeline import build_headless_quicklook_output
from brambhand.visualization.trajectory_render_contracts import build_trajectory_render_contract_3d
from brambhand.visualization.trajectory_widget_contracts import (
    TRAJECTORY_WIDGET_SCHEMA_VERSION,
    TrajectoryWidgetContract,
    build_trajectory_widget_contract,
)


def test_trajectory_widget_contract_builds_curve_layers_and_object_icons() -> None:
    replay = ReplayLog.empty()
    replay.append(
        0.0,
        "step",
        {"position_m": [0.0, 0.0, 0.0], "planned_position_m": [0.5, 0.5, 0.0]},
    )
    replay.append(
        1.0,
        "step",
        {"position_m": [1.0, 2.0, 3.0], "planned_position_m": [1.5, 2.5, 3.5]},
    )

    quicklook = build_headless_quicklook_output(replay)
    render = build_trajectory_render_contract_3d(quicklook)

    widget = build_trajectory_widget_contract(render)

    assert widget.schema_version == TRAJECTORY_WIDGET_SCHEMA_VERSION
    assert widget.source_render_schema_version == render.schema_version
    assert len(widget.curve_layers) == 2
    assert widget.curve_layers[0].name == "current_trajectory"
    assert widget.curve_layers[0].points_2d[-1] == (1.0, 2.0)
    assert widget.curve_layers[1].name == "planned_trajectory"
    assert widget.curve_layers[1].points_2d[-1] == (1.5, 2.5)

    assert len(widget.object_icons) == 2
    assert widget.object_icons[0].name == "current_vehicle"
    assert widget.object_icons[0].icon == "ship"
    assert widget.object_icons[0].x_m == 1.0
    assert widget.object_icons[1].name == "planned_vehicle"
    assert widget.object_icons[1].icon == "ghost_ship"
    assert widget.object_icons[1].x_m == 1.5


def test_trajectory_widget_contract_rejects_unsupported_schema_version() -> None:
    try:
        TrajectoryWidgetContract(
            schema_version=999,
            source_render_schema_version=1,
            curve_layers=(),
            object_icons=(),
        )
    except ValueError as exc:
        assert "schema_version" in str(exc)
    else:
        raise AssertionError("Expected trajectory widget schema-version validation failure")
