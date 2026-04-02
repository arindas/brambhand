"""Spacecraft mass bookkeeping model.

Why this module exists:
- Centralize mass/propellant accounting independent of propulsion implementation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MassModel:
    """Dry and propellant mass container with bounded consumption updates."""

    dry_mass_kg: float
    propellant_mass_kg: float

    def __post_init__(self) -> None:
        if self.dry_mass_kg <= 0.0:
            raise ValueError("dry_mass_kg must be positive.")
        if self.propellant_mass_kg < 0.0:
            raise ValueError("propellant_mass_kg cannot be negative.")

    @property
    def total_mass_kg(self) -> float:
        """Return current total spacecraft mass."""
        return self.dry_mass_kg + self.propellant_mass_kg

    def consume(self, requested_kg: float) -> tuple[MassModel, float]:
        """Consume propellant and return `(updated_model, consumed_kg)`."""
        if requested_kg < 0.0:
            raise ValueError("requested_kg cannot be negative.")

        consumed_kg = min(requested_kg, self.propellant_mass_kg)
        return (
            MassModel(
                dry_mass_kg=self.dry_mass_kg,
                propellant_mass_kg=self.propellant_mass_kg - consumed_kg,
            ),
            consumed_kg,
        )
