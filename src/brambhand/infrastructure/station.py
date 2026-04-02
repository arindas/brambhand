"""Orbital station infrastructure primitives.

Why this module exists:
- Model station-facing operational constraints (port compatibility, resources).
- Keep docking/resource business rules separate from flight dynamics.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class DockingPort:
    """Single docking interface with compatibility constraints."""

    port_id: str
    compatible_vehicle_classes: tuple[str, ...]
    occupied_by: str | None = None

    def is_available_for(self, vehicle_class: str) -> bool:
        """Return `True` if unoccupied and compatible with given vehicle class."""
        return self.occupied_by is None and vehicle_class in self.compatible_vehicle_classes


@dataclass(frozen=True)
class ResourceInterface:
    """Consumable station resource accounting record."""

    resource_name: str
    capacity: float
    available: float
    unit: str

    def __post_init__(self) -> None:
        if self.capacity <= 0.0:
            raise ValueError("capacity must be positive.")
        if not (0.0 <= self.available <= self.capacity):
            raise ValueError("available must be within [0, capacity].")


@dataclass(frozen=True)
class OrbitalStation:
    """Station state with docking ports and managed resources."""

    name: str
    ports: tuple[DockingPort, ...]
    resources: tuple[ResourceInterface, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("station name must be non-empty.")
        if len(self.ports) == 0:
            raise ValueError("station must define at least one docking port.")

    def dock(self, vehicle_id: str, vehicle_class: str) -> tuple[OrbitalStation, str]:
        """Dock vehicle to first compatible free port and return updated station."""
        for index, port in enumerate(self.ports):
            if port.is_available_for(vehicle_class):
                updated_port = replace(port, occupied_by=vehicle_id)
                updated_ports = list(self.ports)
                updated_ports[index] = updated_port
                return replace(self, ports=tuple(updated_ports)), updated_port.port_id
        raise ValueError("No compatible free docking port available.")

    def undock(self, vehicle_id: str) -> OrbitalStation:
        """Undock vehicle by ID and return updated station."""
        updated_ports = []
        found = False
        for port in self.ports:
            if port.occupied_by == vehicle_id:
                updated_ports.append(replace(port, occupied_by=None))
                found = True
            else:
                updated_ports.append(port)
        if not found:
            raise ValueError(f"Vehicle {vehicle_id!r} is not docked.")
        return replace(self, ports=tuple(updated_ports))

    def transfer_resource(self, resource_name: str, amount: float) -> tuple[OrbitalStation, float]:
        """Transfer up to `amount` from named resource and return actual transfer."""
        if amount < 0.0:
            raise ValueError("amount must be non-negative.")

        updated_resources = []
        transferred = None
        for resource in self.resources:
            if resource.resource_name == resource_name:
                actual = min(amount, resource.available)
                updated_resources.append(replace(resource, available=resource.available - actual))
                transferred = actual
            else:
                updated_resources.append(resource)

        if transferred is None:
            raise ValueError(f"Unknown resource: {resource_name!r}")

        return replace(self, resources=tuple(updated_resources)), transferred
