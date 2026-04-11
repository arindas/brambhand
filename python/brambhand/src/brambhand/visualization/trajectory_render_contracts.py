"""R8 trajectory render contracts for 3D curve + moving-object visualization."""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.visualization.quicklook_pipeline import HeadlessQuicklookOutput, Quicklook3DPoint

TRAJECTORY_RENDER_SCHEMA_VERSION = 1

CURRENT_TRAJECTORY_COLOR_HEX = "#00E5FF"
PLANNED_TRAJECTORY_COLOR_HEX = "#C77DFF"
CURRENT_OBJECT_COLOR_HEX = "#FFFFFF"
PLANNED_OBJECT_COLOR_HEX = "#9AA4B2"


@dataclass(frozen=True)
class TrajectoryCurve3D:
    """Single named 3D trajectory curve polyline."""

    name: str
    color_hex: str
    points: tuple[Quicklook3DPoint, ...]


@dataclass(frozen=True)
class MovingObjectMarker3D:
    """Moving object marker sampled on a trajectory curve at a target time."""

    name: str
    sim_time_s: float
    x_m: float
    y_m: float
    z_m: float
    color_hex: str


@dataclass(frozen=True)
class TrajectoryRenderContract3D:
    """Versioned render contract for 3D trajectory curves and moving markers."""

    schema_version: int
    curves: tuple[TrajectoryCurve3D, ...]
    moving_objects: tuple[MovingObjectMarker3D, ...]

    def __post_init__(self) -> None:
        if self.schema_version != TRAJECTORY_RENDER_SCHEMA_VERSION:
            raise ValueError("Unsupported trajectory render schema_version.")


def _sample_curve_at_or_before_time(
    points: tuple[Quicklook3DPoint, ...],
    sim_time_s: float,
) -> Quicklook3DPoint | None:
    if not points:
        return None

    selected: Quicklook3DPoint | None = None
    for point in points:
        if point.sim_time_s <= sim_time_s:
            selected = point
        else:
            break

    if selected is not None:
        return selected
    return points[0]


def build_trajectory_render_contract_3d(
    quicklook: HeadlessQuicklookOutput,
    sim_time_s: float | None = None,
) -> TrajectoryRenderContract3D:
    """Build deterministic 3D curves + moving markers contract for renderer clients."""
    curves = (
        TrajectoryCurve3D(
            name="current_trajectory",
            color_hex=CURRENT_TRAJECTORY_COLOR_HEX,
            points=quicklook.trajectory_3d,
        ),
        TrajectoryCurve3D(
            name="planned_trajectory",
            color_hex=PLANNED_TRAJECTORY_COLOR_HEX,
            points=quicklook.planned_trajectory_3d,
        ),
    )

    if sim_time_s is None:
        sim_time_s = 0.0 if not quicklook.trajectory_3d else quicklook.trajectory_3d[-1].sim_time_s

    moving_objects: list[MovingObjectMarker3D] = []

    current = _sample_curve_at_or_before_time(quicklook.trajectory_3d, sim_time_s)
    if current is not None:
        moving_objects.append(
            MovingObjectMarker3D(
                name="current_vehicle",
                sim_time_s=sim_time_s,
                x_m=current.x_m,
                y_m=current.y_m,
                z_m=current.z_m,
                color_hex=CURRENT_OBJECT_COLOR_HEX,
            )
        )

    planned = _sample_curve_at_or_before_time(quicklook.planned_trajectory_3d, sim_time_s)
    if planned is not None:
        moving_objects.append(
            MovingObjectMarker3D(
                name="planned_vehicle",
                sim_time_s=sim_time_s,
                x_m=planned.x_m,
                y_m=planned.y_m,
                z_m=planned.z_m,
                color_hex=PLANNED_OBJECT_COLOR_HEX,
            )
        )

    return TrajectoryRenderContract3D(
        schema_version=TRAJECTORY_RENDER_SCHEMA_VERSION,
        curves=curves,
        moving_objects=tuple(moving_objects),
    )
