"""Scenario file I/O helpers.

Why this module exists:
- Keep JSON file handling separate from schema parsing logic.
"""

from __future__ import annotations

import json
from pathlib import Path

from brambhand.scenario.scenario_schema import Scenario, scenario_from_dict, scenario_to_dict


def load_scenario(path: str | Path) -> Scenario:
    """Load and validate scenario JSON from file path."""
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return scenario_from_dict(data)


def save_scenario(path: str | Path, scenario: Scenario) -> None:
    """Serialize and save scenario JSON to file path."""
    serialized = scenario_to_dict(scenario)
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(serialized, handle, indent=2, sort_keys=True)
        handle.write("\n")
