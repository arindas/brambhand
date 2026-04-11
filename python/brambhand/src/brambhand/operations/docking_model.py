"""Rendezvous capture envelope evaluation for docking operations.

Why this module exists:
- Make docking safety checks explicit, testable, and configurable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from brambhand.operations.rendezvous_metrics import RendezvousMetrics


class DockingState(StrEnum):
    """High-level docking outcome/state."""

    APPROACH = "approach"
    CAPTURED = "captured"
    DOCKED = "docked"
    FAILED = "failed"


@dataclass(frozen=True)
class DockingConfig:
    """Capture threshold configuration."""

    capture_distance_m: float
    max_capture_closing_speed_mps: float
    max_capture_relative_speed_mps: float

    def __post_init__(self) -> None:
        if self.capture_distance_m <= 0.0:
            raise ValueError("capture_distance_m must be positive.")
        if self.max_capture_closing_speed_mps <= 0.0:
            raise ValueError("max_capture_closing_speed_mps must be positive.")
        if self.max_capture_relative_speed_mps <= 0.0:
            raise ValueError("max_capture_relative_speed_mps must be positive.")


@dataclass(frozen=True)
class DockingStatus:
    """Docking evaluation result with optional failure reason."""

    state: DockingState
    reason: str | None = None


@dataclass(frozen=True)
class DockingModel:
    """Evaluate whether rendezvous metrics satisfy docking constraints."""

    config: DockingConfig

    def evaluate(self, metrics: RendezvousMetrics) -> DockingStatus:
        """Return docking status for given relative geometry/velocity metrics."""
        if metrics.range_m > self.config.capture_distance_m:
            return DockingStatus(state=DockingState.APPROACH)

        relative_speed = metrics.relative_velocity_mps.norm()
        if metrics.closing_rate_mps < 0.0:
            return DockingStatus(
                state=DockingState.FAILED,
                reason="target_receding_inside_capture_zone",
            )
        if metrics.closing_rate_mps > self.config.max_capture_closing_speed_mps:
            return DockingStatus(state=DockingState.FAILED, reason="closing_rate_too_high")
        if relative_speed > self.config.max_capture_relative_speed_mps:
            return DockingStatus(state=DockingState.FAILED, reason="relative_speed_too_high")

        return DockingStatus(state=DockingState.DOCKED)
