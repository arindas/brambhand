"""Scenario schema and validation.

Why this module exists:
- Keep scenario format versioned and validated at load boundaries.
- Provide stable serialization contracts for tooling and CI smoke tests.
"""

from __future__ import annotations

from dataclasses import dataclass

from brambhand.physics.body import InertialState, PhysicalBody
from brambhand.physics.vector import Vector3

SCENARIO_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ScenarioMetadata:
    """Human-facing scenario metadata."""

    name: str
    description: str | None = None


@dataclass(frozen=True)
class Scenario:
    """Versioned scenario payload used to initialize simulation state."""

    schema_version: str
    metadata: ScenarioMetadata
    bodies: tuple[PhysicalBody, ...]


def scenario_to_dict(scenario: Scenario) -> dict:
    """Serialize scenario dataclasses to JSON-compatible dictionary."""
    return {
        "schema_version": scenario.schema_version,
        "metadata": {
            "name": scenario.metadata.name,
            "description": scenario.metadata.description,
        },
        "bodies": [
            {
                "name": body.name,
                "mass": body.mass,
                "state": {
                    "position": [
                        body.state.position.x,
                        body.state.position.y,
                        body.state.position.z,
                    ],
                    "velocity": [
                        body.state.velocity.x,
                        body.state.velocity.y,
                        body.state.velocity.z,
                    ],
                },
            }
            for body in scenario.bodies
        ],
    }


def scenario_from_dict(data: dict) -> Scenario:
    """Parse and validate scenario dictionary according to active schema version."""
    version = data.get("schema_version")
    if version != SCENARIO_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported scenario schema_version="
            f"{version!r}; expected {SCENARIO_SCHEMA_VERSION!r}."
        )

    metadata_dict = data.get("metadata", {})
    name = metadata_dict.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Scenario metadata.name must be a non-empty string.")

    bodies_data = data.get("bodies", [])
    if not isinstance(bodies_data, list) or len(bodies_data) == 0:
        raise ValueError("Scenario bodies must be a non-empty list.")

    names_seen: set[str] = set()
    bodies: list[PhysicalBody] = []
    for item in bodies_data:
        body_name = item["name"]
        if body_name in names_seen:
            raise ValueError(f"Duplicate body name: {body_name}")
        names_seen.add(body_name)

        position = item["state"]["position"]
        velocity = item["state"]["velocity"]

        body = PhysicalBody(
            name=body_name,
            mass=float(item["mass"]),
            state=InertialState(
                position=Vector3(float(position[0]), float(position[1]), float(position[2])),
                velocity=Vector3(float(velocity[0]), float(velocity[1]), float(velocity[2])),
            ),
        )
        bodies.append(body)

    return Scenario(
        schema_version=version,
        metadata=ScenarioMetadata(name=name, description=metadata_dict.get("description")),
        bodies=tuple(bodies),
    )
