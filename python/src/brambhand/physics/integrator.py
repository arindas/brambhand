"""Deterministic fixed-step integration algorithms.

Why this module exists:
- Keep numerical integration strategy independent from force model details.
"""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.gravity_model import NBodyGravityModel


@dataclass(frozen=True)
class VelocityVerletIntegrator:
    """Velocity-Verlet propagator for translational body dynamics."""

    gravity_model: NBodyGravityModel

    def step(self, bodies: list[PhysicalBody], dt: float) -> list[PhysicalBody]:
        """Advance all bodies by one fixed timestep `dt`."""
        if dt <= 0.0:
            raise ValueError("dt must be positive.")

        a0 = self.gravity_model.accelerations(bodies)

        predicted: list[PhysicalBody] = []
        for body, acc in zip(bodies, a0, strict=True):
            r0 = body.state.position
            v0 = body.state.velocity
            r1 = r0 + v0 * dt + acc * (0.5 * dt * dt)
            predicted.append(
                PhysicalBody(
                    name=body.name,
                    mass=body.mass,
                    state=InertialState(position=r1, velocity=v0),
                )
            )

        a1 = self.gravity_model.accelerations(predicted)

        next_bodies: list[PhysicalBody] = []
        for body, acc0, acc1, pred in zip(bodies, a0, a1, predicted, strict=True):
            v0 = body.state.velocity
            v1 = v0 + (acc0 + acc1) * (0.5 * dt)
            next_bodies.append(
                PhysicalBody(
                    name=body.name,
                    mass=body.mass,
                    state=InertialState(position=pred.state.position, velocity=v1),
                )
            )

        return next_bodies
