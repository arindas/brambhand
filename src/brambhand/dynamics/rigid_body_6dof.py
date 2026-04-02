"""R1 6-DOF rigid-body state contracts and baseline integrator.

Why this module exists:
- Define canonical translational + rotational state containers for upcoming
  high-fidelity dynamics work.
- Provide deterministic integration with coupled rotational dynamics baseline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from brambhand.physics.vector import Vector3


class WrenchFrame(StrEnum):
    """Frame in which incoming wrench vectors are expressed."""

    INERTIAL = "inertial"
    BODY = "body"


@dataclass(frozen=True)
class UnitQuaternion:
    """Normalized quaternion attitude representation (w, x, y, z)."""

    w: float
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        norm = math.sqrt(self.w * self.w + self.x * self.x + self.y * self.y + self.z * self.z)
        if not math.isclose(norm, 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("Quaternion must be unit-normalized.")

    @classmethod
    def normalized(cls, w: float, x: float, y: float, z: float) -> UnitQuaternion:
        """Build a unit quaternion by normalizing raw components."""
        norm = math.sqrt(w * w + x * x + y * y + z * z)
        if norm == 0.0:
            raise ValueError("Cannot normalize zero quaternion.")
        return cls(w / norm, x / norm, y / norm, z / norm)

    def multiply(self, other: UnitQuaternion) -> UnitQuaternion:
        """Hamilton product `self ⊗ other`."""
        w1, x1, y1, z1 = self.w, self.x, self.y, self.z
        w2, x2, y2, z2 = other.w, other.x, other.y, other.z
        return UnitQuaternion.normalized(
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        )

    def conjugate(self) -> UnitQuaternion:
        """Return quaternion conjugate (inverse for unit quaternions)."""
        return UnitQuaternion(self.w, -self.x, -self.y, -self.z)

    def rotate_vector(self, vector: Vector3) -> Vector3:
        """Rotate vector from body frame to inertial frame using quaternion."""
        w, x, y, z = self.w, self.x, self.y, self.z
        r11 = 1.0 - 2.0 * (y * y + z * z)
        r12 = 2.0 * (x * y - z * w)
        r13 = 2.0 * (x * z + y * w)
        r21 = 2.0 * (x * y + z * w)
        r22 = 1.0 - 2.0 * (x * x + z * z)
        r23 = 2.0 * (y * z - x * w)
        r31 = 2.0 * (x * z - y * w)
        r32 = 2.0 * (y * z + x * w)
        r33 = 1.0 - 2.0 * (x * x + y * y)
        return Vector3(
            r11 * vector.x + r12 * vector.y + r13 * vector.z,
            r21 * vector.x + r22 * vector.y + r23 * vector.z,
            r31 * vector.x + r32 * vector.y + r33 * vector.z,
        )


@dataclass(frozen=True)
class RigidBody6DoFState:
    """State vector for rigid body translation and rotation."""

    position_m: Vector3
    velocity_mps: Vector3
    attitude: UnitQuaternion
    angular_velocity_radps: Vector3


@dataclass(frozen=True)
class RigidBodyProperties:
    """Rigid-body mass and principal inertia terms."""

    mass_kg: float
    inertia_diag_kgm2: tuple[float, float, float]

    def __post_init__(self) -> None:
        if self.mass_kg <= 0.0:
            raise ValueError("mass_kg must be positive.")
        if any(v <= 0.0 for v in self.inertia_diag_kgm2):
            raise ValueError("inertia diagonal terms must be positive.")


@dataclass(frozen=True)
class Wrench:
    """External force/torque applied to body."""

    force_n: Vector3
    torque_nm: Vector3


def _integrate_attitude_explicit(
    attitude: UnitQuaternion,
    angular_velocity_radps: Vector3,
    dt_s: float,
) -> UnitQuaternion:
    """Integrate quaternion via first-order exponential map approximation."""
    omega_mag = angular_velocity_radps.norm()
    if omega_mag == 0.0:
        return attitude

    half_theta = 0.5 * omega_mag * dt_s
    axis = angular_velocity_radps / omega_mag
    dq = UnitQuaternion.normalized(
        math.cos(half_theta),
        axis.x * math.sin(half_theta),
        axis.y * math.sin(half_theta),
        axis.z * math.sin(half_theta),
    )
    return attitude.multiply(dq)


def integrate_rigid_body_euler(
    state: RigidBody6DoFState,
    props: RigidBodyProperties,
    wrench: Wrench,
    dt_s: float,
    wrench_frame: WrenchFrame = WrenchFrame.INERTIAL,
) -> RigidBody6DoFState:
    """Advance rigid-body state with coupled translation and rotation dynamics.

    Rotational dynamics use diagonal inertia with Euler rigid-body equations:
    `I * w_dot = tau - w x (I w)`.
    """
    if dt_s <= 0.0:
        raise ValueError("dt_s must be positive.")

    if wrench_frame == WrenchFrame.BODY:
        force_n = state.attitude.rotate_vector(wrench.force_n)
        torque_nm = state.attitude.rotate_vector(wrench.torque_nm)
    else:
        force_n = wrench.force_n
        torque_nm = wrench.torque_nm

    acceleration = force_n / props.mass_kg
    next_velocity = state.velocity_mps + acceleration * dt_s
    next_position = state.position_m + next_velocity * dt_s

    ix, iy, iz = props.inertia_diag_kgm2
    w = state.angular_velocity_radps
    i_w = Vector3(ix * w.x, iy * w.y, iz * w.z)
    gyro = w.cross(i_w)
    effective_torque = torque_nm - gyro
    angular_acc = Vector3(
        effective_torque.x / ix,
        effective_torque.y / iy,
        effective_torque.z / iz,
    )
    next_angular_velocity = state.angular_velocity_radps + angular_acc * dt_s
    next_attitude = _integrate_attitude_explicit(state.attitude, next_angular_velocity, dt_s)

    return RigidBody6DoFState(
        position_m=next_position,
        velocity_mps=next_velocity,
        attitude=next_attitude,
        angular_velocity_radps=next_angular_velocity,
    )
