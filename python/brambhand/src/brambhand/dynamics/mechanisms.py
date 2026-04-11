"""R1 articulated mechanism primitives.

Why this module exists:
- Define a common joint/actuation contract for moving spacecraft components.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class JointType(StrEnum):
    """Supported baseline joint classes."""

    REVOLUTE = "revolute"
    PRISMATIC = "prismatic"


@dataclass(frozen=True)
class JointLimits:
    """Lower/upper bounds for a joint coordinate."""

    lower: float
    upper: float

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise ValueError("Joint limit lower bound must be <= upper bound.")


@dataclass(frozen=True)
class JointState:
    """Joint kinematic state."""

    joint_type: JointType
    position: float
    rate: float
    limits: JointLimits


def apply_joint_command(state: JointState, commanded_rate: float, dt_s: float) -> JointState:
    """Advance joint state under commanded rate with hard limit clamping."""
    if dt_s <= 0.0:
        raise ValueError("dt_s must be positive.")

    next_position = state.position + commanded_rate * dt_s
    clamped = max(state.limits.lower, min(state.limits.upper, next_position))
    effective_rate = (clamped - state.position) / dt_s

    return JointState(
        joint_type=state.joint_type,
        position=clamped,
        rate=effective_rate,
        limits=state.limits,
    )
