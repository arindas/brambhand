## TODO

- [x] Ensure memory management skill is in place (see ./SKILLS.md)
- [x] Formalize requirements
- [x] Outline design and architecture in DESIGN.md
- [x] Outline VERIFICATION.md - This should guide property based testing and test driven development
- [x] Follow requirements -> design -> action item -> todo to populate todo

## Action Items (from requirements/design)

### Milestone M1 — Orbital physics baseline
- [x] Create modern Python package skeleton under `src/brambhand/`
- [x] Set up `pyproject.toml` with runtime/dev dependencies and test tool configuration
- [x] Implement `physics/vector.py` with tested vector operations
- [x] Implement inertial state representation for celestial bodies and spacecraft
- [x] Implement `physics/gravity_model.py` (N-body acceleration)
- [x] Implement fixed-step integrator in `physics/integrator.py`
- [x] Implement snapshot/event output in `core/state_snapshot.py` and `core/event_bus.py`
- [x] Add deterministic replay smoke test

### Milestone M2 — Spacecraft control baseline
- [x] Implement propulsion and mass depletion models
- [x] Implement command model for burns and control inputs
- [x] Add unit + integration tests for delta-v and fuel usage

### Milestone M3 — Guidance + communication baseline
- [x] Implement Cartesian/Keplerian conversion utilities
- [x] Implement trajectory predictor
- [x] Implement line-of-sight and delay communication model
- [x] Add integration tests for delayed command and telemetry behavior

### Milestone M4 — Rendezvous and docking
- [x] Implement relative motion metrics
- [x] Implement docking state machine and capture checks
- [x] Add scenario tests for docking success and failure modes

### Milestone M5 — Extended systems
- [x] Implement scenario schema versioning and validation (`scenario/scenario_schema.py`)
- [x] Implement scenario load/save I/O (`scenario/scenario_loader.py`)
- [x] Implement replay log persistence (`scenario/replay_log.py`)
- [x] Implement initial constellation primitives (satellite grouping and shared mission config)
- [x] Implement initial station/infrastructure primitives (docking ports, resource interfaces)
- [x] Add integration scenarios for multi-satellite and station operations

### Stabilization and developer UX
- [x] Run and fix Ruff lint issues
- [x] Run and fix mypy type-check issues (with SciPy import override)
- [x] Add CLI scenario runner (`brambhand` entrypoint)
- [x] Add CLI smoke test coverage
- [x] Add CLI subcommands (`run`, `validate`) with tests
- [x] Add replay inspection subcommand (`replay`) with filters and tests

### Documentation completeness
- [x] Add docs index and navigation (`docs/README.md`)
- [x] Add quickstart guide (`docs/QUICKSTART.md`)
- [x] Add concepts guide (`docs/CONCEPTS.md`)
- [x] Document operational/development workflows (`docs/WORKFLOWS.md`)
- [x] Add multi-workflow tutorials (`docs/TUTORIALS.md`)
- [x] Link docs from root README and contributing guide
- [x] Move API rationale/docs into inline source docstrings (all public APIs)
- [x] Strengthen requirement->design traceability (`DESIGN.md`)
- [x] Expand verification into explicit V&V with requirement traceability (`VERIFICATION.md`)
