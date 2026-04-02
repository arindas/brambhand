"""Deterministic delayed message queue used for link latency modeling.

Why this module exists:
- Encapsulate delayed delivery semantics independent of link geometry logic.
- Preserve deterministic delivery ordering via sequence numbers for replayability.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import TypeVar

T = TypeVar("T")


@dataclass(order=True)
class _QueuedMessage[T]:
    """Internal heap record keyed by delivery time then insertion sequence."""

    delivery_time_s: float
    sequence: int
    payload: T = field(compare=False)


@dataclass
class DelayChannel[T]:
    """Deliver messages after a configured propagation delay."""

    _queue: list[_QueuedMessage[T]] = field(default_factory=list)
    _sequence: int = 0

    def send(self, payload: T, current_time_s: float, delay_s: float) -> None:
        """Enqueue payload to become available at `current_time_s + delay_s`."""
        if delay_s < 0.0:
            raise ValueError("delay_s cannot be negative.")
        msg = _QueuedMessage(
            delivery_time_s=current_time_s + delay_s,
            sequence=self._sequence,
            payload=payload,
        )
        self._sequence += 1
        heapq.heappush(self._queue, msg)

    def receive_ready(self, current_time_s: float) -> list[T]:
        """Pop and return all messages whose delivery time has been reached."""
        ready: list[T] = []
        while self._queue and self._queue[0].delivery_time_s <= current_time_s:
            ready.append(heapq.heappop(self._queue).payload)
        return ready
