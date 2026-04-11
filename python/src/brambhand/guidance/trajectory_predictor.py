"""Forward prediction helper built on the active physics integrator.

Why this module exists:
- Keep trajectory prediction logic reusable for planning and what-if analysis.
"""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.physics.body import PhysicalBody
from brambhand.physics.integrator import VelocityVerletIntegrator


@dataclass(frozen=True)
class TrajectoryPredictor:
    """Predict future body states with fixed-step propagation."""

    integrator: VelocityVerletIntegrator

    def predict(
        self,
        bodies: list[PhysicalBody],
        dt_s: float,
        steps: int,
    ) -> list[list[PhysicalBody]]:
        """Return sequence of predicted states for `steps` integration steps."""
        if dt_s <= 0.0:
            raise ValueError("dt_s must be positive.")
        if steps < 0:
            raise ValueError("steps must be non-negative.")

        states: list[list[PhysicalBody]] = []
        current = bodies
        for _ in range(steps):
            current = self.integrator.step(current, dt_s)
            states.append(current)
        return states
