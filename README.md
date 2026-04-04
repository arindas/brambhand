# brambhand

[<img alt="github" src="https://img.shields.io/badge/github-arindas/brambhand-8da0cb?style=for-the-badge&amp;labelColor=555555&amp;logo=github" height="20">](https://github.com/arindas/brambhand)
[<img alt="tests status" src="https://img.shields.io/github/actions/workflow/status/arindas/brambhand/ci.yml?branch=main&amp;style=for-the-badge&amp;label=tests" height="20">](https://github.com/arindas/brambhand/actions/workflows/ci.yml)
[<img alt="command check status" src="https://img.shields.io/github/actions/workflow/status/arindas/brambhand/cli-smoke.yml?branch=main&amp;style=for-the-badge&amp;label=command-check" height="20">](https://github.com/arindas/brambhand/actions/workflows/cli-smoke.yml)
[<img alt="coverage" src="https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Farindas%2Fbrambhand%2Fmain%2Fbadges%2Fcoverage.json&amp;style=for-the-badge&amp;cacheSeconds=300" height="20">](https://github.com/arindas/brambhand/actions/workflows/coverage.yml)

A scientifically accurate spaceflight sandbox.

`brambhand` aims to simulate the following:
- orbital dynamics
- spacecraft control and dynamics
- spacecraft trajectory control
- navigation and guidance
- datalink and communication
- spacecraft rendezvous and docking
- satellite constellation
- space stations
- infrastructure in LEO and UEO
- interplanetary satellite systems
- interplanetary payload transfer systems
- asteroid trajectory modification
- asteroid minding

## Overview

`brambhand` is a deterministic simulation platform for mission and vehicle analysis,
organized as modular physics/operations domains under `src/brambhand/`.

Today, the project combines:
- core simulation: deterministic integration, event bus, state snapshots
- mission baseline: scenario load/save, replay logs, CLI workflows
- spacecraft operations: mass/propulsion commands, rendezvous and docking screens
- communication: LOS/occlusion checks and delay channels
- structures (R3): 2D/3D linear-static FEM with selectable solver backends

Design priorities: deterministic replay, explicit solver telemetry, and requirement-to-verification traceability.

## Roadmap

Source of truth: [`TODO.md`](./TODO.md)

### Completed

- R1: 6-DOF dynamics, mechanisms, docking contact baseline, and control interfaces
- R2: propulsion fluid network, combustion model, thrust estimator, leakage model
- R2.1: nozzle geometry-aware thrust correction (area ratio and contour loss)
- R3 foundations:
  - 2D FEM baseline with validity envelopes
  - 3D tetrahedral solid FEM baseline
  - sparse assembly and backend-selectable solves
  - matrix-free (2D) path and convergence telemetry
  - model-selection helpers (2D vs 3D)
  - backend-equivalence/determinism tolerance tests (dense vs sparse)
  - structural latency/memory benchmark suite (2D vs 3D profiles)

### In progress (core delivery lane)

- R2.2: chamber-flow + leak-jet dynamics coupling baseline
- R3 remaining work:
  - fracture initiation/propagation baseline
  - damage-state propagation to mass/stiffness/contact behavior
- R3.1: topology-transition simulation baseline (fracture separation + dock/undock attach/detach graph propagation)
- R8.0: early replay/trajectory quicklook feedback

### Planned

- Complete core lane through R8.5:
  - R4, R8.1, R5, R8.2, R6, R7, R7.1, R8.3, R7.2, R8.4, R8.5
- Post-core lane (kept from derailing core execution):
  - R9: debris-risk modeling
  - R10: docking lifecycle logistics and transfer workflows
  - R11/R12: trajectory optimization and advanced mission-analysis parity extensions
  - R13/R14: deferred atmospheric + advanced structural fidelity expansions

## Getting started

### Quickstart

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
pytest
ruff check .
mypy src tests
```

### CLI

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

- Docs index: [`docs/README.md`](./docs/README.md)
- Quickstart: [`docs/QUICKSTART.md`](./docs/QUICKSTART.md)
- Concepts: [`docs/CONCEPTS.md`](./docs/CONCEPTS.md)
- Workflows: [`docs/WORKFLOWS.md`](./docs/WORKFLOWS.md)
- Tutorials: [`docs/TUTORIALS.md`](./docs/TUTORIALS.md)
- API reference: [`docs/API_REFERENCE.md`](./docs/API_REFERENCE.md)
- Distributed protocol: [`docs/DISTRIBUTED_PROTOCOL.md`](./docs/DISTRIBUTED_PROTOCOL.md)
- Performance SLOs: [`docs/PERFORMANCE_SLOS.md`](./docs/PERFORMANCE_SLOS.md)
- Validation criteria: [`VALIDATION.md`](./VALIDATION.md)

## Contributing

- Human contributor guide: [`CONTRIBUTING.md`](./CONTRIBUTING.md)
- Engineering planning and traceability:
  - [`REQUIREMENTS.md`](./REQUIREMENTS.md)
  - [`DESIGN.md`](./DESIGN.md)
  - [`VERIFICATION.md`](./VERIFICATION.md)
  - [`VALIDATION.md`](./VALIDATION.md)
  - [`TODO.md`](./TODO.md)

For automation/agent runbooks, see [`AGENT.md`](./AGENT.md) and [`CLAUDE.md`](./CLAUDE.md).

