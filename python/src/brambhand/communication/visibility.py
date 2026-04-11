"""Line-of-sight visibility checks with simple spherical occluders.

Why this module exists:
- Provide geometry primitives for communication availability and future sensors.
"""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class SphericalOccluder:
    """A body that blocks LOS if the line segment intersects its sphere."""

    center_m: Vector3
    radius_m: float


def _distance_point_to_segment(point: Vector3, a: Vector3, b: Vector3) -> float:
    ab = b - a
    ap = point - a
    ab2 = ab.squared_norm()
    if ab2 == 0.0:
        return (point - a).norm()

    t = ap.dot(ab) / ab2
    t_clamped = max(0.0, min(1.0, t))
    closest = a + ab * t_clamped
    return (point - closest).norm()


def line_of_sight_clear(a_m: Vector3, b_m: Vector3, occluders: list[SphericalOccluder]) -> bool:
    """Return `True` when segment a->b is not blocked by any occluder."""
    for occluder in occluders:
        if _distance_point_to_segment(occluder.center_m, a_m, b_m) < occluder.radius_m:
            return False
    return True
