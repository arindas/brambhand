"""Time-window command application for burn execution.

Why this module exists:
- Decouple command scheduling from propulsion implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from brambhand.physics.body import PhysicalBody
from brambhand.physics.vector import Vector3
from brambhand.spacecraft.mass_model import MassModel
from brambhand.spacecraft.propulsion import BurnResult, PropulsionSystem


@dataclass(frozen=True)
class BurnCommand:
    """Scheduled finite burn command."""

    start_time_s: float
    duration_s: float
    throttle: float
    direction: Vector3

    def __post_init__(self) -> None:
        if self.start_time_s < 0.0:
            raise ValueError("start_time_s cannot be negative.")
        if self.duration_s < 0.0:
            raise ValueError("duration_s cannot be negative.")
        if not 0.0 <= self.throttle <= 1.0:
            raise ValueError("throttle must be in [0, 1].")


@dataclass
class CommandModel:
    """Applies burn commands over simulation time windows."""

    pending_burns: list[BurnCommand] = field(default_factory=list)

    def add_burn(self, command: BurnCommand) -> None:
        """Add command and keep deterministic execution order."""
        self.pending_burns.append(command)
        self.pending_burns.sort(key=lambda c: (c.start_time_s, c.duration_s, c.throttle))

    def apply_window(
        self,
        sim_time_s: float,
        dt_s: float,
        body: PhysicalBody,
        mass_model: MassModel,
        propulsion: PropulsionSystem,
    ) -> tuple[PhysicalBody, MassModel, list[BurnResult]]:
        """Apply all command overlaps within `[sim_time_s, sim_time_s + dt_s]`."""
        if dt_s <= 0.0:
            raise ValueError("dt_s must be positive.")

        window_start = sim_time_s
        window_end = sim_time_s + dt_s

        current_body = body
        current_mass = mass_model
        burn_results: list[BurnResult] = []

        for command in self.pending_burns:
            burn_start = command.start_time_s
            burn_end = command.start_time_s + command.duration_s

            overlap_start = max(window_start, burn_start)
            overlap_end = min(window_end, burn_end)
            overlap = overlap_end - overlap_start

            if overlap <= 0.0:
                continue

            result = propulsion.apply_burn(
                body=current_body,
                mass_model=current_mass,
                direction=command.direction,
                throttle=command.throttle,
                duration_s=overlap,
            )
            burn_results.append(result)
            current_body = result.body
            current_mass = result.mass_model

        return current_body, current_mass, burn_results
