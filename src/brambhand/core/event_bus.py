"""Event collection primitives for deterministic simulation timelines.

Why this module exists:
- Provide stable ordered event capture for replay and debugging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Event:
    """A timestamped simulation event."""

    sim_time_s: float
    kind: str
    payload: dict[str, Any]


@dataclass
class EventBus:
    """In-memory event collector preserving append order."""

    _events: list[Event] = field(default_factory=list)

    def emit(self, event: Event) -> None:
        """Append a new event to the ordered stream."""
        self._events.append(event)

    def snapshot(self) -> list[Event]:
        """Return a shallow copy of current event stream."""
        return list(self._events)

    def clear(self) -> None:
        """Clear collected events."""
        self._events.clear()
