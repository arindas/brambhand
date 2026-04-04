# Release Notes

## Unreleased

### Added

- R1 dynamics verification expansion:
  - gyroscopic coupling test coverage for non-spherical inertia in `dynamics/rigid_body_6dof.py`
  - docking threshold boundary coverage in `dynamics/contact_docking.py`
- R2.1 nozzle geometry-aware thrust correction baseline:
  - `NozzleGeometryCorrection` input contract
  - area-ratio efficiency factor and contour-loss scaling in thrust estimates
  - backward-compatible optional geometry input in `estimate_nozzle_thrust(...)`
- R2.1 sensitivity tests in `tests/test_propulsion_r2_contracts.py` for:
  - area-ratio influence on thrust
  - contour-loss impact on thrust
- R3 structural FEM baseline:
  - added deterministic linear static 2D triangular FEM solver (canonical path: `structures/fem/solver.py`)
  - added `tests/test_structures_r3_contracts.py` for solve behavior, linearity, and element stress outputs
  - added sparse assembly path (COO->CSR) and structural `nnz` telemetry in solve results
  - added solver backend abstraction for reduced systems (`dense_direct`, `sparse_direct`, `sparse_iterative`)
  - added preconditioned sparse-iterative solve path (Jacobi/none) with convergence telemetry
  - added matrix-free iterative operator prototype backend for reduced-system structural solves
  - hardened matrix-free mode with residual safeguards, optional sparse-direct consistency checks, and robustness protections
  - added advanced matrix-free block-Jacobi preconditioning and benchmark utility for convergence comparison
  - added explicit structural solver termination reason telemetry across dense/sparse/matrix-free backends
  - added matrix-free acceptance-threshold definitions/evaluators for operational and analysis profiles
  - refactored structural FEM implementation into modular components (`fem/contracts.py`, `fem/geometry.py`, `fem/backends.py`, orchestration facade in `fem/solver.py`)
  - added 3D tetrahedral solid FEM baseline (`FEMModel3D`, `solve_linear_static_fem_3d(...)`) with dense/sparse direct/sparse iterative backend support
  - added 2D-vs-3D model-selection policy helpers (`select_structural_model_dimension(...)`) with out-of-plane span/load/constraint thresholds
  - completed structural FEM migration to canonical `brambhand.structures.fem.*` namespace (`contracts`, `geometry`, `backends`, `solver`, `selection`) and removed legacy `fem_*` shim modules
  - added backend-equivalence + deterministic-repeatability tolerance tests for dense-vs-sparse structural solves (2D and 3D)
  - added structural latency/memory benchmark suite utility for 2D-vs-3D profile comparisons (P50/P95 solve timing + `nnz`-derived sparse storage estimate)
- Documentation/traceability update for structural scaling:
  - added structural solver scalability requirements (FR-074..FR-079, NR-032..NR-035)
  - updated R3 TODO roadmap for sparse backends, matrix-free path, and 2D/3D performance validation
  - updated V&V and performance SLO docs for structural latency/memory targets and evidence plans
- Documentation/roadmap expansion for mission-analysis parity:
  - added FR-103..FR-114 and NR-041..NR-046 for OD, uncertainty/dispersion, operational constraints, mission products, and interactive analysis reproducibility
  - added adapter-oriented R11/R12 design and TODO planning with OSS-library integration surfaces and in-house fallback strategy
- Agent/developer process clarity improvements:
  - added `AGENT.md` as canonical agent runbook (startup order, memory protocol, done checklist)
  - added `CLAUDE.md` as Claude-oriented mirror of agent runbook
  - added `docs/AGENT_MEMORY.md` with memory read/write/compaction rules for new environments
  - clarified root `README.md`, `SKILLS.md`, `CONTRIBUTING.md`, and `docs/README.md` to point agents to canonical process docs
- Research-to-planning synchronization updates:
  - added free-flow research session notes in `docs/RESEARCH_NOTES.md`
  - synchronized `REQUIREMENTS`/`DESIGN`/`TODO`/`VERIFICATION`/`VALIDATION` on docking safety-zone contracts, trajectory initial-guess utilities, and OD process-noise/covariance-consistency planning
- Architectural decoupling parity extension:
  - added FR-115..FR-117 and NR-047..NR-048 for solver-module decomposition, backend-neutral adapter boundaries, and centralized frame/time conversion integrity
  - updated design/TODO/V&V linkage for coupling-mitigation implementation policy
- Scope-planning extension for atmospheric launch/ascent and aero-structural behavior:
  - added FR-119..FR-124 and NR-050..NR-052 for atmosphere/drag modeling, launch event sequencing, atmospheric-exit+apogee prediction, ascent attitude workflows, and buckling/fatigue-to-fracture integration
  - added deferred R13 roadmap phase in `TODO.md` (scheduled post-R12 to avoid derailing active R3-R12 delivery)
  - updated `DESIGN.md`, `VERIFICATION.md`, and `VALIDATION.md` traceability for launch/ascent acceptance evidence planning
- Scope-planning extension for full-fledged advanced structural fidelity:
  - added FR-125..FR-131 and NR-053..NR-056 for nonlinear/material/transient/buckling/fatigue-growth/thermal-coupling/adaptive-remesh FEM progression
  - added deferred R14 roadmap phase in `TODO.md` (scheduled post-R13 to preserve active milestone cadence)
  - updated `DESIGN.md`, `VERIFICATION.md`, and `VALIDATION.md` with R14 traceability and gate planning

## v0.1.0 (2026-04-02)

`v0.1.0` is the first integrated release of **brambhand** with core simulation,
mission operations primitives, CLI workflows, CI automation, and comprehensive docs.

### Highlights

- Deterministic N-body translational simulation baseline
- Spacecraft mass/propulsion/command modeling
- Guidance conversion and trajectory prediction tools
- Communication LOS + delayed channel model
- Rendezvous metrics and docking envelope checks
- Scenario schema + replay persistence
- Constellation and station infrastructure primitives
- CLI workflows: `validate`, `run`, `replay`
- GitHub issue/PR templates and CI pipelines
- Full docs set (quickstart, concepts, workflows, tutorials)
- Inline source docstrings as API source of truth

### Included pre-release milestones

- `v0.1.0-alpha.0` — project bootstrap, requirements/design/V&V scaffolding
- `v0.1.0-alpha.1` — M1 orbital physics baseline
- `v0.1.0-alpha.2` — M2 spacecraft control baseline
- `v0.1.0-alpha.3` — M3 guidance + communication baseline
- `v0.1.0-alpha.4` — M4 rendezvous + docking baseline
- `v0.1.0-alpha.5` — M5 scenario/replay + infrastructure/constellation
- `v0.1.0-alpha.6` — CLI workflows (`run`, `validate`, `replay`)
- `v0.1.0-alpha.7` — GitHub templates + CI workflows

### Quality status

At release cut:

- `ruff check .` passing
- `mypy src tests` passing
- `pytest` passing

### Notes

- API docs are maintained inline in source docstrings under `src/brambhand/`.
- See `docs/` for user/developer guides and workflows.
