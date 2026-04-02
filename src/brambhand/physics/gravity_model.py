"""Newtonian N-body gravity acceleration model.

Why this module exists:
- Keep force model pluggable and separate from integration scheme.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.constants import G

from brambhand.physics.body import PhysicalBody
from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class NBodyGravityModel:
    """Compute per-body accelerations from Newtonian pairwise gravity."""

    gravitational_constant: float = G
    softening_length: float = 0.0

    def accelerations(self, bodies: list[PhysicalBody]) -> list[Vector3]:
        """Return acceleration vectors aligned with input body ordering."""
        accelerations: list[Vector3] = []
        eps2 = self.softening_length * self.softening_length

        for i, body_i in enumerate(bodies):
            ai = np.zeros(3, dtype=float)
            ri = np.array(
                [
                    body_i.state.position.x,
                    body_i.state.position.y,
                    body_i.state.position.z,
                ],
                dtype=float,
            )

            for j, body_j in enumerate(bodies):
                if i == j:
                    continue

                rj = np.array(
                    [
                        body_j.state.position.x,
                        body_j.state.position.y,
                        body_j.state.position.z,
                    ],
                    dtype=float,
                )
                delta = rj - ri
                dist2 = float(delta.dot(delta)) + eps2
                dist = np.sqrt(dist2)
                inv_dist3 = 1.0 / (dist2 * dist)
                ai += self.gravitational_constant * body_j.mass * delta * inv_dist3

            accelerations.append(Vector3(float(ai[0]), float(ai[1]), float(ai[2])))

        return accelerations
