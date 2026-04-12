# brambhand

[<img alt="github" src="https://img.shields.io/badge/github-arindas/brambhand-8da0cb?style=for-the-badge&amp;labelColor=555555&amp;logo=github" height="20">](https://github.com/arindas/brambhand)
[<img alt="tests status" src="https://img.shields.io/github/actions/workflow/status/arindas/brambhand/ci.yml?branch=main&amp;style=for-the-badge&amp;label=tests" height="20">](https://github.com/arindas/brambhand/actions/workflows/ci.yml)
[<img alt="command check status" src="https://img.shields.io/github/actions/workflow/status/arindas/brambhand/cli-smoke.yml?branch=main&amp;style=for-the-badge&amp;label=command-check" height="20">](https://github.com/arindas/brambhand/actions/workflows/cli-smoke.yml)
[<img alt="coverage" src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Farindas%2Fbrambhand%2Fbadges%2Fbadges%2Fcoverage.json&amp;style=for-the-badge&amp;cacheSeconds=300" height="20">](https://github.com/arindas/brambhand/actions/workflows/coverage.yml)

A deterministic spaceflight simulation platform for engineering analysis.

`brambhand` is intended for mission and vehicle studies involving:
- orbit propagation and trajectory analysis
- spacecraft motion and control
- propulsion behavior (feed flow, chamber state, thrust, leaks)
- rendezvous, docking, and relative-motion checks
- communication visibility and delay effects
- structural response and failure progression
- scenario replay, audit, and reproducibility workflows

## Overview

See [`DESIGN.md`](./DESIGN.md) for the architecture and design of `brambhand`.

Current implementation supports:
- deterministic simulation stepping and replay logging
- scenario validation/run/replay via CLI
- orbit/relative-motion and rendezvous metric calculations
- docking contact screening and impulse-response baseline
- propulsion reduced-order models (feed network, chamber state, thrust, leakage, leak-jet coupling)
- structural FEM baselines (2D and 3D) with multiple solver backends and telemetry

Design constraints used across modules:
- deterministic replay for fixed inputs/configuration
- explicit convergence/health telemetry for solver paths
- requirement -> design -> verification traceability

## Roadmap

Source of truth: [`TODO.md`](./TODO.md)

- Implemented baseline domains
  - spacecraft 6-DOF motion and control interfaces
  - rendezvous metrics and docking contact screening
  - reduced-order propulsion chain through thrust/leakage/leak-jet coupling
  - structural FEM baseline stack (2D/3D, backend-selectable, telemetry-enabled)

- Current active development
  - slosh dynamics and additional propulsion coupling checks
  - fracture and damage progression behavior in structures
  - topology-transition handling (connected damage vs disjoint body separation)
  - early operator feedback views from replay/trajectory data

- Next major integrations
  - two-way fluid-structure coupling (FSI)
  - STL geometry ingestion and geometry-linked subsystem mapping
  - persistence/checkpointing and distributed runtime coordination
  - progressive visualization stack (contracts -> overlays -> dashboards -> renderer)
  - optional CFD-backed fluid providers behind the same coupling contracts

Milestone IDs (R2.2, R3.1, R8.0, etc.) are maintained in `TODO.md` for implementation tracking.

## Getting started

### Quickstart

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e './python/brambhand[dev]'
pytest python/brambhand/tests
ruff check python/brambhand
mypy python/brambhand/src python/brambhand/tests
```

### Native desktop client (C++/CMake scaffold)

Build bootstrap native client:

```bash
cmake -S c/brambhand -B c/brambhand/build
cmake --build c/brambhand/build
ctest --test-dir c/brambhand/build --output-on-failure
./c/brambhand/build/brambhand_desktop
```

## CLI

Validate a scenario file:

```bash
brambhand validate path/to/scenario.json
```

Run a scenario JSON file with fixed-step propagation:

```bash
brambhand run path/to/scenario.json --dt 10 --steps 100 --replay-out replay.jsonl
```

Inspect replay output with filters:

```bash
brambhand replay replay.jsonl --kind step_completed --start-time 100 --end-time 500
```

## Documentation

| Document | Link |
|---|---|
| Docs index | [`docs/README.md`](./docs/README.md) |
| Quickstart | [`docs/QUICKSTART.md`](./docs/QUICKSTART.md) |
| Concepts | [`docs/CONCEPTS.md`](./docs/CONCEPTS.md) |
| Workflows | [`docs/WORKFLOWS.md`](./docs/WORKFLOWS.md) |
| Tutorials | [`docs/TUTORIALS.md`](./docs/TUTORIALS.md) |
| API reference | [`docs/API_REFERENCE.md`](./docs/API_REFERENCE.md) |
| Distributed protocol | [`docs/DISTRIBUTED_PROTOCOL.md`](./docs/DISTRIBUTED_PROTOCOL.md) |
| Performance SLOs | [`docs/PERFORMANCE_SLOS.md`](./docs/PERFORMANCE_SLOS.md) |
| Validation criteria | [`VALIDATION.md`](./VALIDATION.md) |

## Contributing

- Human contributor guide: [`CONTRIBUTING.md`](./CONTRIBUTING.md)
- Engineering planning and traceability:
  - [`REQUIREMENTS.md`](./REQUIREMENTS.md)
  - [`DESIGN.md`](./DESIGN.md)
  - [`VERIFICATION.md`](./VERIFICATION.md)
  - [`VALIDATION.md`](./VALIDATION.md)
  - [`TODO.md`](./TODO.md)

For automation/agent runbooks, see [`AGENT.md`](./AGENT.md) and [`CLAUDE.md`](./CLAUDE.md).

