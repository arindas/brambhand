# Verification and Validation (V&V)

This document defines how high-fidelity `brambhand` requirements are verified (built right) and traced to validation evidence.
Detailed scenario/benchmark acceptance criteria are maintained in `VALIDATION.md`.

## 1) V&V strategy

## Verification (engineering correctness)
- Static quality gates: `ruff`, `mypy`
- Unit tests per module
- Coupled-solver integration tests
- Determinism/replay consistency tests
- Regression tests for every fixed defect

## Validation (fitness and realism)
- Analytical benchmark comparison (where closed-form exists)
- Reference dataset comparison (engine, structural, fluid benchmarks)
- Scenario-level mission workflows (docking, leak, damage progression)
- Operator workflow validation (mission-control/onboard telemetry usability)

## 2) Test pyramid for the target system

1. **Unit tests**
   - rigid-body equations, quaternion/rotation handling
   - fluid network components and conservation checks
   - combustion model outputs in nominal/off-nominal points
   - FEM element and assembly checks
   - fracture rule logic
   - STL parsing, mesh metadata extraction, and nozzle geometry feature extraction
   - renderer profile configuration, BVH structure integrity, and ray-march parameter validation

2. **Domain integration tests**
   - propulsion chain (fluid -> combustion -> thrust)
   - docking contact -> rigid-body response
   - structural damage -> leakage emergence
   - FSI coupling iterations and convergence
   - visualization pipeline (scene graph -> BVH -> render output) for deterministic replay frames

3. **System integration tests**
   - end-to-end scenario run with persistence and replay
   - checkpoint/restart equivalence tests
   - distributed run consistency against single-node baseline

4. **Validation suites**
   - benchmark packs for orbit, propulsion, and structure
   - mission-control workflow acceptance scenarios

## 3) Requirement traceability (V&V evidence plan)

| Requirement group | Verification evidence | Validation evidence |
|---|---|---|
| FR-001..FR-005 | 6-DOF unit/integration tests, controller loop tests | closed-loop attitude/thrust maneuver scenarios |
| FR-006..FR-010, FR-031 | fluid/combustion tests, thrust estimator tests, nozzle-geometry correction tests | engine operating-map comparisons, leak fault scenarios, contour/area-ratio sensitivity checks |
| FR-011..FR-015 | FEM/fracture unit tests, FSI convergence tests, docking contact tests | structural damage progression and docking impact scenarios |
| FR-016..FR-018, FR-032..FR-037 | STL importer/parser tests, mass/inertia extraction tests, collision/FEM preprocessing tests, geometry-mapping schema tests | CAD-to-simulation reproducibility checks and geometry-anchored damage/leak visualization checks |
| FR-019..FR-021, FR-064..FR-066 | DB persistence tests, idempotent tick-commit tests, replay/checkpoint determinism tests | long-run restart and replay audit workflows |
| FR-022..FR-024, FR-059..FR-063 | partition/sync protocol tests, barrier-commit atomicity tests, orchestration integration tests | multi-node consistency and throughput scenarios without partition replicas |
| FR-025..FR-028 | telemetry/view-model contract tests | operator acceptance scenarios (mission-control + onboard) |
| FR-038..FR-043 | rendering pipeline tests (scene graph, BVH update/query, ray-march quality controls, replay camera sync) | visual analysis scenarios with profile switching and frame reproducibility checks |
| FR-044..FR-048 | simulation-clock and pacing-controller tests, multi-rate scheduler tests, replay metadata consistency tests | real-time/accelerated/offline mode scenario playback with timeline equivalence checks |
| FR-049..FR-058 | inter-module contract tests (schema, units, frame checks), scheduler-order tests, causality/fault-propagation tests, distributed tick-barrier tests | end-to-end reconstruction and cross-module incident replay audits |
| FR-029..FR-030 | diagnostics/metadata emission tests | reproducible run record audits |

## 4) Non-functional verification plan
- NR-001..NR-003: validity envelope docs + convergence residual assertions + calibration tests
- NR-004..NR-005: deterministic replay and distributed tolerance checks
- NR-006..NR-008: scalability/load tests + ingestion durability + restart-time tests
- NR-022..NR-024: cadence error/jitter/drift tests and pacing-mode equivalence checks
- NR-025..NR-028: interface validation, provenance completeness, degraded-mode visibility tests
- NR-029..NR-031: barrier commit skew, persistence commit-latency bounds, deterministic retry/idempotency tests
- NR-009..NR-011: modular interface tests + schema version compatibility checks
- NR-012..NR-013: alarm/error propagation tests for faults and bad configs
- NR-014..NR-015: dashboard latency/render stress tests
- NR-018..NR-021: rendering frame-time budgets, temporal stability checks, BVH update-cost tests, ray-march reproducibility parameter logging
- NR-016..NR-017: docs synchronization checks + inline API doc coverage

## 5) Phase-gated acceptance criteria

- **R1 gate:** 6-DOF + mechanism contact scenarios verified, deterministic replay intact
- **R2 gate:** propulsion chain validated against reference points and leak cases
- **R2.1 gate:** nozzle-geometry-aware thrust correction validated against geometry-derived test fixtures
- **R3 gate:** FEM/fracture pipeline stable on benchmark structures
- **R4 gate:** FSI coupling converges under documented residual thresholds
- **R5 gate:** STL ingestion produces valid derived properties/meshes for target assets
- **R6 gate:** DB-backed replay/checkpoint survives long-run test suites
- **R7 gate:** distributed consistency/performance targets met
- **R7.1 gate:** pacing/time-scale modes meet cadence bounds and preserve simulation timeline equivalence
- **R7.2 gate:** inter-module/distributed contracts enforce atomic barrier commits and replay-grade persistence provenance
- **R8 gate:** dashboard/operator workflows pass acceptance scenarios
- **R8.1 gate:** 3D rendering pipeline meets profile-specific frame-time/quality targets with deterministic replay camera sync

## 6) Definition of done (feature level)
- Requirement IDs linked
- Design sections linked
- Inline API docstrings updated
- Verification tests added + passing
- Validation scenario evidence added
- Traceability row updated in this document
- TODO sequencing updated