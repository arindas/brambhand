"""Communication link availability and propagation delay evaluation.

Why this module exists:
- Separate link physics/geometry checks from command transport queues.
- Keep light-time delay explicit and testable for mission timing behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from scipy.constants import c

from brambhand.communication.visibility import SphericalOccluder, line_of_sight_clear
from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class LinkState:
    """Evaluated one-way link state at a given instant."""

    available: bool
    one_way_delay_s: float | None


@dataclass(frozen=True)
class LinkModel:
    """Range/LOS constrained link model with finite signal propagation speed."""

    max_range_m: float | None = None
    speed_of_light_mps: float = c

    def evaluate(
        self,
        tx_pos_m: Vector3,
        rx_pos_m: Vector3,
        occluders: list[SphericalOccluder] | None = None,
    ) -> LinkState:
        """Return whether the link is available and, if so, its one-way delay."""
        occluders = occluders or []

        los_clear = line_of_sight_clear(tx_pos_m, rx_pos_m, occluders)
        if not los_clear:
            return LinkState(available=False, one_way_delay_s=None)

        distance_m = (rx_pos_m - tx_pos_m).norm()
        if self.max_range_m is not None and distance_m > self.max_range_m:
            return LinkState(available=False, one_way_delay_s=None)

        return LinkState(available=True, one_way_delay_s=distance_m / self.speed_of_light_mps)
