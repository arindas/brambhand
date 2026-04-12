"""Compact infographic trajectory-widget contracts built from shared render payloads."""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.visualization.trajectory_render_contracts import TrajectoryRenderContract3D

TRAJECTORY_WIDGET_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TrajectoryWidgetCurveLayer:
    """Compact widget curve layer projected from a named render curve."""

    name: str
    color_hex: str
    points_2d: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class TrajectoryWidgetObjectIcon:
    """Compact widget object-icon marker projected from a moving 3D object marker."""

    name: str
    icon: str
    color_hex: str
    x_m: float
    y_m: float


@dataclass(frozen=True)
class TrajectoryWidgetContract:
    """Versioned compact infographic widget payload for trajectory overlays."""

    schema_version: int
    source_render_schema_version: int
    curve_layers: tuple[TrajectoryWidgetCurveLayer, ...]
    object_icons: tuple[TrajectoryWidgetObjectIcon, ...]

    def __post_init__(self) -> None:
        if self.schema_version != TRAJECTORY_WIDGET_SCHEMA_VERSION:
            raise ValueError("Unsupported trajectory widget schema_version.")


def _icon_name_for_object(marker_name: str) -> str:
    if "planned" in marker_name:
        return "ghost_ship"
    return "ship"


def build_trajectory_widget_contract(
    render_contract: TrajectoryRenderContract3D,
) -> TrajectoryWidgetContract:
    """Build compact 2D widget layers/icons from shared trajectory render payloads."""
    curve_layers = tuple(
        TrajectoryWidgetCurveLayer(
            name=curve.name,
            color_hex=curve.color_hex,
            points_2d=tuple((point.x_m, point.y_m) for point in curve.points),
        )
        for curve in render_contract.curves
    )
    object_icons = tuple(
        TrajectoryWidgetObjectIcon(
            name=marker.name,
            icon=_icon_name_for_object(marker.name),
            color_hex=marker.color_hex,
            x_m=marker.x_m,
            y_m=marker.y_m,
        )
        for marker in render_contract.moving_objects
    )
    return TrajectoryWidgetContract(
        schema_version=TRAJECTORY_WIDGET_SCHEMA_VERSION,
        source_render_schema_version=render_contract.schema_version,
        curve_layers=curve_layers,
        object_icons=object_icons,
    )
