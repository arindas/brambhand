"""R1 control target and actuation command contracts.

Why this module exists:
- Provide stable interfaces for integrating future closed-loop controllers.
"""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.physics.vector import Vector3


@dataclass(frozen=True)
class ControlTarget:
    """Desired body-frame rates and optional thrust vector target."""

    desired_body_rates_radps: Vector3
    desired_thrust_direction: Vector3 | None = None


@dataclass(frozen=True)
class ActuationCommand:
    """Controller output command envelope for propulsion/mechanisms."""

    body_torque_command_nm: Vector3
    thrust_throttle: float
    mechanism_rate_commands: dict[str, float]

    def __post_init__(self) -> None:
        if not 0.0 <= self.thrust_throttle <= 1.0:
            raise ValueError("thrust_throttle must be in [0, 1].")
