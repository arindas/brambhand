"""Versioned maneuver command contracts.

Why this module exists:
- Keep maneuver schema explicit and reusable across runtime/replay/tooling.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from brambhand.physics.vector import Vector3

MANEUVER_SCHEMA_VERSION = 1


class ManeuverMode(StrEnum):
    IMPULSIVE = "impulsive"
    FINITE_BURN_CONSTANT_THRUST = "finite_burn_constant_thrust"
    FINITE_BURN_GUIDED = "finite_burn_guided"


class ManeuverFrame(StrEnum):
    INERTIAL = "inertial"
    LVLH = "lvlh"
    BODY = "body"


@dataclass(frozen=True)
class ManeuverCommand:
    schema_version: int
    command_id: str
    body_id: str
    requested_tick: int
    mode: ManeuverMode
    direction: Vector3
    frame: ManeuverFrame = ManeuverFrame.INERTIAL
    # impulsive
    delta_v_mps: float = 0.0
    # finite burn
    throttle: float = 0.0
    duration_ticks: int = 1
    # provenance
    phase_id: str = ""
    target_id: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != MANEUVER_SCHEMA_VERSION:
            raise ValueError("Unsupported maneuver schema_version")
        if not self.command_id:
            raise ValueError("command_id cannot be empty")
        if not self.body_id:
            raise ValueError("body_id cannot be empty")
        if self.requested_tick < 0:
            raise ValueError("requested_tick cannot be negative")
        if self.mode == ManeuverMode.IMPULSIVE and self.delta_v_mps < 0.0:
            raise ValueError("delta_v_mps cannot be negative")
        if self.mode in {ManeuverMode.FINITE_BURN_CONSTANT_THRUST, ManeuverMode.FINITE_BURN_GUIDED}:
            if not 0.0 <= self.throttle <= 1.0:
                raise ValueError("throttle must be in [0,1]")
            if self.duration_ticks <= 0:
                raise ValueError("duration_ticks must be positive")
