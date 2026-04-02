"""Replay timeline persistence model.

Why this module exists:
- Persist deterministic event streams for debugging and regression verification.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReplayRecord:
    """Single replay record in ordered event timeline."""

    sequence: int
    sim_time_s: float
    kind: str
    payload: dict[str, Any]


@dataclass
class ReplayLog:
    """Ordered replay log with JSONL persistence helpers."""

    records: list[ReplayRecord]

    @classmethod
    def empty(cls) -> ReplayLog:
        """Create empty replay log."""
        return cls(records=[])

    def append(self, sim_time_s: float, kind: str, payload: dict[str, Any]) -> None:
        """Append replay record with auto-incremented deterministic sequence."""
        self.records.append(
            ReplayRecord(
                sequence=len(self.records),
                sim_time_s=sim_time_s,
                kind=kind,
                payload=payload,
            )
        )

    def save_jsonl(self, path: str | Path) -> None:
        """Persist records to JSON Lines format."""
        with Path(path).open("w", encoding="utf-8") as handle:
            for record in self.records:
                handle.write(json.dumps(asdict(record), sort_keys=True))
                handle.write("\n")

    @classmethod
    def load_jsonl(cls, path: str | Path) -> ReplayLog:
        """Load replay log from JSON Lines file."""
        records: list[ReplayRecord] = []
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                data = json.loads(line)
                records.append(
                    ReplayRecord(
                        sequence=int(data["sequence"]),
                        sim_time_s=float(data["sim_time_s"]),
                        kind=str(data["kind"]),
                        payload=dict(data["payload"]),
                    )
                )
        return cls(records=records)
