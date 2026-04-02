"""3D vector math primitives used across the simulation stack.

Why this module exists:
- Avoid ad-hoc tuple/list math and keep vector operations explicit and testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vector3:
    """Immutable 3D vector with basic linear algebra operations."""

    x: float
    y: float
    z: float

    def __add__(self, other: Vector3) -> Vector3:
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3) -> Vector3:
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vector3:
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vector3:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector3:
        if scalar == 0.0:
            raise ZeroDivisionError("Cannot divide vector by zero.")
        return Vector3(self.x / scalar, self.y / scalar, self.z / scalar)

    def dot(self, other: Vector3) -> float:
        """Return scalar dot product with `other`."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3) -> Vector3:
        """Return vector cross product with `other`."""
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def squared_norm(self) -> float:
        """Return squared Euclidean norm."""
        return self.dot(self)

    def norm(self) -> float:
        """Return Euclidean norm."""
        return math.sqrt(self.squared_norm())

    def normalized(self) -> Vector3:
        """Return unit vector in same direction."""
        magnitude = self.norm()
        if magnitude == 0.0:
            raise ValueError("Cannot normalize zero vector.")
        return self / magnitude
