"""R1 docking contact screening and impulse response baseline.

Why this module exists:
- Define deterministic contact/capture outcomes before full rigid-body
  contact solver integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DockingContactOutcome(StrEnum):
    """High-level docking contact result class."""

    NO_CONTACT = "no_contact"
    CONTACT = "contact"
    CAPTURED = "captured"
    REJECTED = "rejected"


@dataclass(frozen=True)
class DockingContactParams:
    """Threshold and impact parameters for contact/capture screening."""

    capture_distance_m: float
    max_capture_speed_mps: float
    contact_distance_m: float
    restitution: float = 0.2
    effective_mass_kg: float = 100.0
    hard_impact_speed_mps: float = 1.0

    def __post_init__(self) -> None:
        if self.capture_distance_m <= 0.0:
            raise ValueError("capture_distance_m must be positive.")
        if self.max_capture_speed_mps <= 0.0:
            raise ValueError("max_capture_speed_mps must be positive.")
        if self.contact_distance_m <= 0.0:
            raise ValueError("contact_distance_m must be positive.")
        if self.capture_distance_m > self.contact_distance_m:
            raise ValueError("capture_distance_m must be <= contact_distance_m.")
        if not 0.0 <= self.restitution <= 1.0:
            raise ValueError("restitution must be in [0, 1].")
        if self.effective_mass_kg <= 0.0:
            raise ValueError("effective_mass_kg must be positive.")
        if self.hard_impact_speed_mps <= 0.0:
            raise ValueError("hard_impact_speed_mps must be positive.")


@dataclass(frozen=True)
class DockingContactResult:
    """Deterministic contact decision output."""

    outcome: DockingContactOutcome
    reason: str | None = None
    impulse_ns: float = 0.0
    post_contact_relative_speed_mps: float = 0.0


def evaluate_docking_contact(
    relative_distance_m: float,
    relative_speed_mps: float,
    params: DockingContactParams,
) -> DockingContactResult:
    """Classify docking interaction and estimate scalar contact impulse.

    Convention:
    - positive `relative_speed_mps` => closing speed
    - negative `relative_speed_mps` => receding speed
    """
    if relative_distance_m > params.contact_distance_m:
        return DockingContactResult(DockingContactOutcome.NO_CONTACT)

    if relative_speed_mps < 0.0:
        return DockingContactResult(
            DockingContactOutcome.REJECTED,
            reason="receding_in_contact_zone",
            post_contact_relative_speed_mps=relative_speed_mps,
        )

    if relative_distance_m <= params.capture_distance_m:
        if relative_speed_mps <= params.max_capture_speed_mps:
            return DockingContactResult(
                DockingContactOutcome.CAPTURED,
                impulse_ns=params.effective_mass_kg * relative_speed_mps,
                post_contact_relative_speed_mps=0.0,
            )
        return DockingContactResult(
            DockingContactOutcome.REJECTED,
            reason="capture_speed_exceeded",
            post_contact_relative_speed_mps=relative_speed_mps,
        )

    if relative_speed_mps > params.hard_impact_speed_mps:
        return DockingContactResult(
            DockingContactOutcome.REJECTED,
            reason="hard_impact_rejection",
            post_contact_relative_speed_mps=relative_speed_mps,
        )

    impulse = (1.0 + params.restitution) * params.effective_mass_kg * relative_speed_mps
    post_speed = -params.restitution * relative_speed_mps
    return DockingContactResult(
        DockingContactOutcome.CONTACT,
        impulse_ns=impulse,
        post_contact_relative_speed_mps=post_speed,
    )
