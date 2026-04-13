"""General SOI/handoff metadata contracts with baseline two-body provider."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from brambhand.physics.vector import Vector3

SOI_HANDOFF_SCHEMA_VERSION = 1


class HandoffPhaseKind(StrEnum):
    ENCOUNTER = "encounter"
    CAPTURE_START = "capture_start"
    INSERTION_COMPLETE = "insertion_complete"


@dataclass(frozen=True)
class SOIHandoffMetadata:
    schema_version: int
    phase_kind: HandoffPhaseKind
    body_id: str
    primary_body_id: str
    tick_id: int
    sim_time_s: float
    distance_to_primary_m: float
    relative_speed_mps: float
    specific_orbital_energy_jkg: float
    sphere_of_influence_radius_m: float
    inside_sphere_of_influence: bool

    def __post_init__(self) -> None:
        if self.schema_version != SOI_HANDOFF_SCHEMA_VERSION:
            raise ValueError("Unsupported SOI handoff schema_version")
        if not self.body_id:
            raise ValueError("body_id cannot be empty")
        if not self.primary_body_id:
            raise ValueError("primary_body_id cannot be empty")
        if self.tick_id < 0:
            raise ValueError("tick_id cannot be negative")
        if self.sim_time_s < 0.0:
            raise ValueError("sim_time_s cannot be negative")
        if self.distance_to_primary_m < 0.0:
            raise ValueError("distance_to_primary_m cannot be negative")
        if self.relative_speed_mps < 0.0:
            raise ValueError("relative_speed_mps cannot be negative")
        if self.sphere_of_influence_radius_m <= 0.0:
            raise ValueError("sphere_of_influence_radius_m must be positive")


class SOIHandoffMetadataProvider(Protocol):
    """General provider interface for mission-phase SOI/handoff metadata."""

    def build_metadata(
        self,
        *,
        phase_kind: HandoffPhaseKind,
        body_id: str,
        primary_body_id: str,
        tick_id: int,
        sim_time_s: float,
        body_position_m: Vector3,
        body_velocity_mps: Vector3,
        primary_position_m: Vector3,
        primary_velocity_mps: Vector3,
    ) -> SOIHandoffMetadata: ...


@dataclass(frozen=True)
class TwoBodySOIHandoffMetadataProvider:
    """Specific baseline implementation using two-body relative-energy metrics."""

    mu_primary_m3_s2: float
    sphere_of_influence_radius_m: float

    def __post_init__(self) -> None:
        if self.mu_primary_m3_s2 <= 0.0:
            raise ValueError("mu_primary_m3_s2 must be positive")
        if self.sphere_of_influence_radius_m <= 0.0:
            raise ValueError("sphere_of_influence_radius_m must be positive")

    def build_metadata(
        self,
        *,
        phase_kind: HandoffPhaseKind,
        body_id: str,
        primary_body_id: str,
        tick_id: int,
        sim_time_s: float,
        body_position_m: Vector3,
        body_velocity_mps: Vector3,
        primary_position_m: Vector3,
        primary_velocity_mps: Vector3,
    ) -> SOIHandoffMetadata:
        rel_r = body_position_m - primary_position_m
        rel_v = body_velocity_mps - primary_velocity_mps
        distance = rel_r.norm()
        speed = rel_v.norm()
        radius = max(distance, 1.0)
        specific_energy = 0.5 * (speed * speed) - (self.mu_primary_m3_s2 / radius)

        return SOIHandoffMetadata(
            schema_version=SOI_HANDOFF_SCHEMA_VERSION,
            phase_kind=phase_kind,
            body_id=body_id,
            primary_body_id=primary_body_id,
            tick_id=tick_id,
            sim_time_s=sim_time_s,
            distance_to_primary_m=distance,
            relative_speed_mps=speed,
            specific_orbital_energy_jkg=specific_energy,
            sphere_of_influence_radius_m=self.sphere_of_influence_radius_m,
            inside_sphere_of_influence=distance <= self.sphere_of_influence_radius_m,
        )


def build_soi_handoff_metadata(
    provider: SOIHandoffMetadataProvider,
    *,
    phase_kind: HandoffPhaseKind,
    body_id: str,
    primary_body_id: str,
    tick_id: int,
    sim_time_s: float,
    body_position_m: Vector3,
    body_velocity_mps: Vector3,
    primary_position_m: Vector3,
    primary_velocity_mps: Vector3,
) -> SOIHandoffMetadata:
    """Build handoff metadata through the general provider interface."""

    return provider.build_metadata(
        phase_kind=phase_kind,
        body_id=body_id,
        primary_body_id=primary_body_id,
        tick_id=tick_id,
        sim_time_s=sim_time_s,
        body_position_m=body_position_m,
        body_velocity_mps=body_velocity_mps,
        primary_position_m=primary_position_m,
        primary_velocity_mps=primary_velocity_mps,
    )
