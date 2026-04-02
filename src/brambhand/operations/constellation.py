"""Satellite constellation grouping and mission configuration primitives.

Why this module exists:
- Represent mission-level grouping separate from per-vehicle dynamics state.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MissionConfig:
    """Shared configuration for satellites participating in one mission."""

    mission_name: str
    control_center: str
    telemetry_period_s: float

    def __post_init__(self) -> None:
        if not self.mission_name.strip():
            raise ValueError("mission_name must be non-empty.")
        if not self.control_center.strip():
            raise ValueError("control_center must be non-empty.")
        if self.telemetry_period_s <= 0.0:
            raise ValueError("telemetry_period_s must be positive.")


@dataclass(frozen=True)
class SatelliteMember:
    """Satellite identity + role within a constellation."""

    vehicle_name: str
    role: str
    orbital_slot: int

    def __post_init__(self) -> None:
        if not self.vehicle_name.strip():
            raise ValueError("vehicle_name must be non-empty.")
        if not self.role.strip():
            raise ValueError("role must be non-empty.")


@dataclass(frozen=True)
class SatelliteConstellation:
    """Collection of satellites coordinated under one mission config."""

    name: str
    mission_config: MissionConfig
    members: tuple[SatelliteMember, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("constellation name must be non-empty.")
        if len(self.members) == 0:
            raise ValueError("constellation must include at least one member.")

        names = [m.vehicle_name for m in self.members]
        if len(set(names)) != len(names):
            raise ValueError("constellation member names must be unique.")

        slots = [m.orbital_slot for m in self.members]
        if len(set(slots)) != len(slots):
            raise ValueError("constellation orbital slots must be unique.")

    def members_by_role(self, role: str) -> tuple[SatelliteMember, ...]:
        """Return members matching the requested mission role."""
        return tuple(member for member in self.members if member.role == role)

    def member_names(self) -> tuple[str, ...]:
        """Return member vehicle names in stored order."""
        return tuple(member.vehicle_name for member in self.members)
