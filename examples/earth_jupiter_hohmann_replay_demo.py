#!/usr/bin/env python3
"""Generate a replay JSONL demo for 2D Earth->Jupiter Hohmann-transfer quicklook."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

AU_M = 149_597_870_700.0
MU_SUN_M3_S2 = 1.32712440018e20
EARTH_ORBIT_RADIUS_M = 1.0 * AU_M
JUPITER_ORBIT_RADIUS_M = 5.2044 * AU_M


def _build_event(sequence: int, sim_time_s: float, kind: str, severity: str) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "sim_time_s": sim_time_s,
        "kind": kind,
        "severity": severity,
        "payload_json": {},
    }


def generate_frames(samples: int, run_id: str) -> list[dict[str, Any]]:
    if samples < 4:
        raise ValueError("samples must be >= 4")

    r1 = EARTH_ORBIT_RADIUS_M
    r2 = JUPITER_ORBIT_RADIUS_M
    a = 0.5 * (r1 + r2)
    e = (r2 - r1) / (r2 + r1)

    transfer_time_s = math.pi * math.sqrt(a**3 / MU_SUN_M3_S2)
    mean_motion = math.sqrt(MU_SUN_M3_S2 / a**3)

    frames: list[dict[str, Any]] = []
    for i in range(samples + 1):
        frac = i / samples
        sim_time_s = frac * transfer_time_s

        true_anomaly = mean_motion * sim_time_s
        radius = a * (1.0 - e**2) / (1.0 + e * math.cos(true_anomaly))

        planned_x = radius * math.cos(true_anomaly)
        planned_y = radius * math.sin(true_anomaly)

        perturb = 1.0 + 0.015 * math.sin(4.0 * true_anomaly)
        current_x = planned_x * perturb
        current_y = planned_y * perturb

        events: list[dict[str, Any]] = []
        if i == 0:
            events.append(_build_event(10_000 + i, sim_time_s, "simulation_started", "info"))
        if i == samples // 2:
            events.append(_build_event(10_000 + i, sim_time_s, "threshold_crossed", "warning"))
        if i == samples:
            events.append(_build_event(10_000 + i, sim_time_s, "alarm_raised", "critical"))

        frames.append(
            {
                "schema_version": 1,
                "run_id": run_id,
                "tick_id": i,
                "sim_time_s": sim_time_s,
                "sequence": i,
                "bodies": [
                    {
                        "body_id": "current_vehicle",
                        "position_m": {"x": current_x, "y": current_y, "z": 0.0},
                    },
                    {
                        "body_id": "planned_vehicle",
                        "position_m": {"x": planned_x, "y": planned_y, "z": 0.0},
                    },
                ],
                "events": events,
            }
        )

    return frames


def save_jsonl(frames: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for frame in frames:
            handle.write(json.dumps(frame, sort_keys=True))
            handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Earth->Jupiter Hohmann replay JSONL demo for brambhand desktop replay window."
    )
    parser.add_argument("--out", type=Path, required=True, help="Output replay JSONL path.")
    parser.add_argument("--samples", type=int, default=360, help="Transfer samples (>=4).")
    parser.add_argument("--run-id", type=str, default="earth_jupiter_hohmann_demo")
    args = parser.parse_args()

    frames = generate_frames(samples=args.samples, run_id=args.run_id)
    save_jsonl(frames, args.out)

    print(
        f"saved={args.out} frames={len(frames)} transfer_time_days="
        f"{frames[-1]['sim_time_s'] / 86400.0:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
