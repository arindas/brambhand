"""Command-line interfaces for validating, running, and inspecting simulations.

Why this module exists:
- Provide a stable user-facing entrypoint (`brambhand`) for common workflows.
- Keep deterministic run logic reusable from both CLI and tests (`run_scenario`).
- Support reproducibility by writing and filtering replay logs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from brambhand.physics.gravity_model import NBodyGravityModel
from brambhand.physics.integrator import VelocityVerletIntegrator
from brambhand.scenario.replay_log import ReplayLog
from brambhand.scenario.scenario_loader import load_scenario
from brambhand.scenario.scenario_schema import SCENARIO_SCHEMA_VERSION, Scenario


def run_scenario(
    scenario: Scenario,
    dt_s: float,
    steps: int,
) -> tuple[list[str], ReplayLog]:
    """Run deterministic fixed-step propagation for a loaded scenario.

    Why: this isolates core CLI runtime behavior into a testable function and
    keeps run output deterministic for regression checks.
    """
    if dt_s <= 0.0:
        raise ValueError("dt_s must be positive.")
    if steps < 0:
        raise ValueError("steps must be non-negative.")

    bodies = list(scenario.bodies)
    integrator = VelocityVerletIntegrator(gravity_model=NBodyGravityModel())

    replay = ReplayLog.empty()
    sim_time = 0.0
    replay.append(sim_time_s=sim_time, kind="simulation_started", payload={"dt_s": dt_s})

    for step in range(1, steps + 1):
        bodies = integrator.step(bodies, dt_s)
        sim_time += dt_s
        replay.append(sim_time_s=sim_time, kind="step_completed", payload={"step": step})

    summaries = [
        json.dumps(
            {
                "name": body.name,
                "mass": body.mass,
                "position_m": [
                    body.state.position.x,
                    body.state.position.y,
                    body.state.position.z,
                ],
                "velocity_mps": [
                    body.state.velocity.x,
                    body.state.velocity.y,
                    body.state.velocity.z,
                ],
            },
            sort_keys=True,
        )
        for body in sorted(bodies, key=lambda b: b.name)
    ]
    return summaries, replay


def validate_scenario(path: Path) -> Scenario:
    """Load and validate a scenario file against current schema rules."""
    return load_scenario(path)


def replay_summary(
    replay: ReplayLog,
    kind: str | None = None,
    start_time_s: float | None = None,
    end_time_s: float | None = None,
) -> list[str]:
    """Filter replay records and render stable JSON lines.

    Why: enables CLI-driven debugging and audit of command/event timelines.
    """
    lines: list[str] = []
    for record in replay.records:
        if kind is not None and record.kind != kind:
            continue
        if start_time_s is not None and record.sim_time_s < start_time_s:
            continue
        if end_time_s is not None and record.sim_time_s > end_time_s:
            continue
        lines.append(
            json.dumps(
                {
                    "sequence": record.sequence,
                    "sim_time_s": record.sim_time_s,
                    "kind": record.kind,
                    "payload": record.payload,
                },
                sort_keys=True,
            )
        )
    return lines


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser with `run`, `validate`, and `replay` commands."""
    parser = argparse.ArgumentParser(description="brambhand simulation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a scenario simulation")
    run_parser.add_argument("scenario", type=Path, help="Path to scenario JSON file.")
    run_parser.add_argument("--dt", type=float, default=10.0, help="Fixed timestep in seconds.")
    run_parser.add_argument(
        "--steps",
        type=int,
        default=10,
        help="Number of fixed integration steps.",
    )
    run_parser.add_argument(
        "--replay-out",
        type=Path,
        default=None,
        help="Optional output JSONL replay path.",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate scenario schema and data")
    validate_parser.add_argument("scenario", type=Path, help="Path to scenario JSON file.")

    replay_parser = subparsers.add_parser("replay", help="Inspect replay JSONL records")
    replay_parser.add_argument("replay", type=Path, help="Path to replay JSONL file.")
    replay_parser.add_argument("--kind", type=str, default=None, help="Filter by event kind.")
    replay_parser.add_argument(
        "--start-time",
        type=float,
        default=None,
        help="Filter events with sim_time_s >= start-time.",
    )
    replay_parser.add_argument(
        "--end-time",
        type=float,
        default=None,
        help="Filter events with sim_time_s <= end-time.",
    )

    return parser


def main() -> int:
    """CLI entrypoint invoked by `brambhand` console script."""
    args = build_parser().parse_args()

    if args.command == "validate":
        scenario = validate_scenario(args.scenario)
        print(
            "scenario_valid="
            f"true name={scenario.metadata.name!r} schema_version={SCENARIO_SCHEMA_VERSION}"
        )
        return 0

    if args.command == "run":
        scenario = load_scenario(args.scenario)
        summaries, replay = run_scenario(scenario=scenario, dt_s=args.dt, steps=args.steps)

        print(f"scenario={scenario.metadata.name!r} steps={args.steps} dt={args.dt}")
        for summary in summaries:
            print(summary)

        if args.replay_out is not None:
            replay.save_jsonl(args.replay_out)
            print(f"replay_saved={args.replay_out}")

        return 0

    if args.command == "replay":
        replay = ReplayLog.load_jsonl(args.replay)
        lines = replay_summary(
            replay,
            kind=args.kind,
            start_time_s=args.start_time,
            end_time_s=args.end_time,
        )
        print(f"replay_records={len(lines)}")
        for line in lines:
            print(line)
        return 0

    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
