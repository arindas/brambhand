# Verification and Validation (V&V)

This document defines how `brambhand` is checked for **correct implementation**
(verification) and **fitness for intended use** (validation).

## 1) Verification strategy (build the system right)

Verification uses automated tests and static checks:

- Lint/style: `ruff check .`
- Type checks: `mypy src tests`
- Unit/integration tests: `pytest`

### Test categories

1. Unit tests for module-level correctness
2. Integration tests for cross-module behavior
3. Determinism/replay tests for reproducibility
4. Regression tests for previously fixed behavior

## 2) Validation strategy (build the right system)

Validation uses mission-representative workflows to confirm requirements are met:

- CLI flow: validate scenario -> run -> replay inspect
- Orbital propagation behavior under realistic two-body setups
- Burn execution consistency with analytical rocket equation
- Communication delay and LOS behavior under scripted scenarios
- Rendezvous/docking safety envelope checks
- Scenario/replay persistence roundtrip checks

Validation artifacts are implemented as executable tests under `tests/` and CLI smoke CI workflow.

## 3) Requirement -> verification/validation traceability

| Requirement group | Verification evidence | Validation evidence |
|---|---|---|
| FR-001..FR-004 | `tests/test_vector.py`, `tests/test_gravity_model.py`, `tests/test_integrator.py`, `tests/test_deterministic_replay.py` | Circular-orbit bounded behavior and deterministic replay runs |
| FR-005..FR-008 | `tests/test_mass_model.py`, `tests/test_propulsion.py`, `tests/test_command_model.py` | Burn outcomes aligned with Tsiolkovsky equation + depletion scenarios |
| FR-009..FR-012 | `tests/test_orbit_elements.py`, `tests/test_trajectory_predictor.py` | Roundtrip orbital conversion and forward prediction consistency |
| FR-013..FR-015 | `tests/test_communication.py` | Delayed uplink/downlink and LOS/range gating workflows |
| FR-016..FR-018 | `tests/test_rendezvous_metrics.py`, `tests/test_docking_scenarios.py` | Docking success/failure mission envelope scenarios |
| FR-019..FR-021 | `tests/test_scenario_loader.py`, `tests/test_replay_log.py`, `tests/test_cli.py`, `tests/test_cli_commands.py` | End-to-end CLI validation/run/replay workflows and persistence checks |

## 4) Non-functional requirement coverage (NR)

- NR-001 (stability): monitored via orbital propagation tests (`test_integrator.py`)
- NR-002 (determinism): `test_deterministic_replay.py`, stable sorting in snapshots/replay sequencing
- NR-003/NR-004 (modularity/extensibility): module boundaries in `src/brambhand/*`
- NR-005 (testability): comprehensive tests across modules
- NR-006 (performance): baseline small-scenario runs exercised in tests/CLI smoke
- NR-007 (observability): structured events, snapshots, replay JSONL
- NR-008 (documentation): synchronized requirements/design/V&V + inline API docs in source files

## 5) Definition of done (per feature)

- Requirement linkage updated (`REQUIREMENTS.md`)
- Design linkage updated (`DESIGN.md`)
- Inline API docs added/updated in source code
- Verification tests added and passing
- Validation scenario or workflow evidence added
- `TODO.md` updated
