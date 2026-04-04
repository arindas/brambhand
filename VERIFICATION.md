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
   - chamber-flow/leak-jet dynamics and force-coupling checks
   - FEM element and assembly checks
   - fracture rule logic
   - assembly-topology transition checks (fracture split + dock/undock attach/detach)
   - STL parsing, mesh metadata extraction, and nozzle geometry feature extraction
   - replay-to-trajectory extraction and overlay alignment checks (`current`/`planned` baselines)
   - dashboard view-model schema/serialization determinism checks
   - renderer profile configuration, BVH structure integrity, and ray-march parameter validation

2. **Domain integration tests**
   - propulsion chain (`fluid -> combustion -> thrust`)
   - `docking contact -> rigid-body response`
   - `structural damage -> leakage emergence`
   - FSI coupling iterations and convergence
   - visualization quicklook pipeline (`replay -> trajectory/event layers`) determinism checks
   - visualization pipeline (`scene graph -> BVH -> render output`) for deterministic replay frames

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
| FR-011..FR-015, FR-072..FR-073, FR-081 | FEM/fracture unit tests, dimensional-validity envelope checks (2D assumption guardrails), 3D-vs-2D model-selection tests, connected-topology (hole/crack-network) and disjoint-topology (separation) propagation tests, FSI convergence and failure/recovery tests, docking contact tests | structural damage progression (connected topology), severe separation (disjoint topology), and docking impact scenarios |
| FR-016..FR-018, FR-032..FR-037, FR-082 | STL importer/parser tests, mass/inertia extraction tests, collision/FEM preprocessing tests, geometry-mapping schema tests, crack/fracture/leak overlay contract tests | CAD-to-simulation reproducibility checks and geometry-anchored crack/fracture/leak visualization checks |
| FR-019..FR-021, FR-064..FR-066 | DB persistence tests, idempotent tick-commit tests, replay/checkpoint determinism tests | long-run restart and replay audit workflows |
| FR-022..FR-024, FR-059..FR-063 | partition/sync protocol tests, barrier-commit atomicity tests, orchestration integration tests | multi-node consistency and throughput scenarios without partition replicas |
| FR-025..FR-028 | telemetry/view-model contract tests, replay-to-trajectory extraction tests, quicklook overlay determinism tests (`current` vs `planned`), severity-mapping determinism tests | operator acceptance scenarios (mission-control + onboard), early visual-feedback acceptance from replay artifacts |
| FR-038..FR-043, FR-083 | rendering pipeline tests (scene graph, BVH update/query, ray-march quality controls, replay camera sync, topology-discontinuity rendering contracts), geometry-anchored overlay contract tests | visual analysis scenarios with profile switching, severe-failure geometry-change playback, and frame reproducibility checks |
| FR-044..FR-048 | simulation-clock and pacing-controller tests, multi-rate scheduler tests, replay metadata consistency tests | real-time/accelerated/offline mode scenario playback with timeline equivalence checks |
| FR-049..FR-058, FR-138 | inter-module contract tests (schema, units, frame checks), model-graph DAG validation tests (cycle rejection + mutation transaction checks), scheduler-order tests, causality/fault-propagation tests, distributed tick-barrier tests | end-to-end reconstruction and cross-module incident replay audits |
| FR-067..FR-071 | baseline regression tests for gravity/orbit propagation, communication LOS occlusion, link delay channel behavior, scenario/replay CLI workflows | continuity scenarios proving baseline mission workflows remain valid while high-fidelity/distributed features evolve |
| FR-074..FR-080 | sparse assembly/backend tests, preconditioner convergence tests, matrix-free operator checks, backend-equivalence/determinism tolerance tests, solver telemetry contract tests, matrix-free robustness/failure-path tests | latency/memory benchmark scenarios across 2D/3D structural profiles with matrix-free acceptance thresholds |
| FR-084..FR-085 | debris population/fragmentation tests, compounding accretion predictor tests, debris-impact coupling tests | debris-growth risk scenarios and asteroid-impact fragment-cloud evolution scenarios |
| FR-086..FR-090 | rendezvous/dock/undock lifecycle tests, approach safety-zone/hold-point/collision-avoidance contract tests, booster payload-transfer mission-phase tests, sphere-of-influence handoff propagation tests, Hohmann-transfer workflow tests, gravity-assist encounter/deflection tests | end-to-end payload transfer scenarios (`launch->UEO assembly->boost->handoff to destination planetary influence`) plus Hohmann and gravity-assist mission validations |
| FR-091..FR-102 | optimizer-contract tests, ephemeris/frame-provider adapter tests, Hohmann/Lambert adapter tests, gravity-assist adapter tests, campaign-orchestration determinism/provenance tests, seed-sensitivity/convergence-basin tests, cross-backend tolerance benchmark tests | trajectory-optimization and interplanetary trade-study validation packs with backend-swap reproducibility evidence |
| FR-103..FR-114 | orbit-determination estimator tests, covariance propagation and covariance-consistency tests, Monte Carlo/dispersion workflow tests, operational-constraint loop tests, finite-burn targeting realism tests, stationkeeping workflow tests, mission-product generation contract tests, reference cross-validation harness tests, interactive-session reproducibility tests | advanced mission-analysis validation suites comparing OD/dispersion/constraint workflows to trusted references and mission-ops product acceptance criteria |
| FR-115..FR-118 | module-boundary decomposition tests, FEM namespace migration/completeness tests, adapter type-leakage guard tests, shared frame/time-provider contract tests | architecture-integrity scenarios demonstrating backend swaps, canonical public API path stability after migration, and cross-module frame/time consistency |
| FR-119..FR-124 | atmosphere-profile validity tests, aerodynamic force/moment contract tests, launch event-sequencing/replay-order tests, atmospheric-exit/apogee predictor tolerance tests, ascent guidance-control loop tests, buckling/fatigue-to-fracture coupling tests | integrated launch/ascent scenarios with max-q/staging/atmospheric-exit/apogee checks and aero-structural risk progression validation |
| FR-125..FR-131 | nonlinear structural solve tests, material-model contract tests, transient structural integration tests, buckling/post-buckling workflow tests, fatigue-growth coupling tests, deterministic remesh provenance checks, thermo-structural coupling tests | advanced structural reference-benchmark scenarios with profile-class tolerance envelopes, thermal-coupling plausibility checks, and fallback-policy observability checks |
| FR-132..FR-137 | chamber-flow/leak-jet/slosh unit/integration tests, leak-jet/slosh-to-6DOF coupling tests, topology-transition graph/state tests (fracture split + dock/undock attach/detach), FSI exchange-contract integration tests, CFD-adapter contract/backend-swap tests, replay topology/CFD provenance checks | chamber internal-flow plausibility scenarios, leak-jet disturbance scenarios, slosh-induced attitude disturbance scenarios, CFD-coupled plausibility scenarios, and topology-transition mission scenarios with conservation/replay checks |
| FR-029..FR-030 | diagnostics/metadata emission tests | reproducible run record audits |

## 4) Non-functional verification plan
- NR-001..NR-003: validity envelope docs + convergence residual assertions + calibration tests
- NR-004..NR-005: deterministic replay and distributed tolerance checks
- NR-006..NR-008: scalability/load tests + ingestion durability + restart-time tests
- NR-022..NR-024: cadence error/jitter/drift tests and pacing-mode equivalence checks
- NR-032..NR-036: structural `nnz` memory scaling checks, dimensional latency-profile tests (2D/3D), backend-switch determinism tolerance, fallback visibility tests, and matrix-free convergence stability characterization
- NR-037..NR-059: trajectory/mission-analysis adapter swap stability, frame/time validation diagnostics, campaign reproducibility ordering, external-vs-in-house tolerance equivalence, OD convergence/uncertainty stability, operational-constraint auditability, mission-product reproducibility, interactive-session replay integrity, adapter type-leakage rejection, centralized conversion-drift bounds, FEM-namespace migration/completeness parity checks on canonical import paths, atmospheric/aerodynamic validity-envelope enforcement, launch-event/apogee reproducibility tolerances, deterministic buckling/fatigue threshold observability, nonlinear/transient structural convergence diagnostics, advanced-fidelity compute-budget/fallback behavior, benchmark-governed acceptance envelopes, deterministic thermo-material provenance drift bounds, topology/leak-jet conservation-consistency checks, slosh/CFD cadence-budget compliance with explicit fallback validation, and model-graph DAG overhead/mutation-budget observability
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
- **R2.2 gate:** chamber-flow and leak-jet dynamics coupling is validated with conservation-bounded force/torque propagation evidence
- **R2.3 gate:** slosh baseline and 6-DOF coupling meet deterministic disturbance-response and cadence-budget checks
- **R3 gate:** FEM/fracture pipeline stable on benchmark structures
- **R3.1 gate:** disjoint-topology transition simulation (fracture separation + dock/undock attach/detach) is deterministic and replay-reconstructible
- **R4 gate:** FSI coupling converges under documented residual thresholds
- **R5 gate:** STL ingestion produces valid derived properties/meshes for target assets
- **R6 gate:** DB-backed replay/checkpoint survives long-run test suites
- **R7 gate:** distributed consistency/performance targets met
- **R7.1 gate:** pacing/time-scale modes meet cadence bounds and preserve simulation timeline equivalence
- **R7.2 gate:** inter-module/distributed contracts enforce atomic barrier commits, DAG-mutation correctness, and replay-grade persistence provenance
- **R8.0 gate:** replay/trajectory quicklook outputs are deterministic, event-order preserving, and use a deterministic/extensible severity mapping contract (`info|warning|critical` baseline)
- **R8.1 gate:** mission-control/onboard view-model schemas are versioned, validated, and replay-compatible
- **R8.2 gate:** geometry-overlay contracts are versioned, validated, and replay-compatible
- **R8.3 gate:** replay timeline/camera-control contracts preserve timeline equivalence across pacing modes
- **R8.4 gate:** dashboard/operator workflows pass acceptance scenarios
- **R8.5 gate:** 3D rendering pipeline meets profile-specific frame-time/quality targets with deterministic replay camera sync
- **R4.1 gate:** optional CFD-coupled fluid/combustion adapters pass cadence-guard/fallback tests and profile-gated performance envelopes
- **R13 gate:** atmospheric launch/ascent stack demonstrates drag-coupled trajectory realism, deterministic launch-event sequencing, atmospheric-exit/apogee prediction tolerance conformance, and buckling/fatigue risk-propagation evidence
- **R14 gate:** advanced structural fidelity stack demonstrates nonlinear/material/transient/buckling/fatigue-growth/thermal-coupling workflow correctness against trusted references with deterministic remesh/fallback observability

## 6) Current evidence snapshot (2026-04-02)

- R1 dynamics evidence: `tests/test_dynamics_r1_contracts.py`
  - frame-aware wrench behavior
  - gyroscopic coupling checks for non-spherical inertia
  - docking impulse/rebound and threshold boundary outcomes
- R2 propulsion evidence: `tests/test_propulsion_r2_contracts.py`
  - feed/combustion/thrust/leakage baseline checks
  - nozzle geometry sensitivity checks (area ratio + contour loss)
- Communication continuity evidence: `tests/test_communication.py`
  - LOS occlusion screening
  - one-way light-time delay checks
  - deterministic delay-channel integration behavior
- R3 structural baseline evidence: `tests/test_structures_r3_contracts.py`
  - linear-static FEM solve behavior
  - load-to-displacement linear scaling checks
  - validity-envelope enforcement checks (plane-stress thickness guard, plane-strain mode path, out-of-plane rejection)
  - sparse assembly/telemetry checks (`sparse_coo_csr`, `nnz` metrics)
  - solver-backend consistency checks (dense direct vs sparse direct vs sparse iterative vs matrix-free iterative)
  - backend-equivalence + repeatability determinism tolerance checks for dense vs sparse modes in both 2D and 3D solves
  - structural latency/memory benchmark suite coverage for 2D vs 3D profiles (P50/P95 solve timing + sparse storage estimate from `nnz` telemetry)
  - preconditioned iterative convergence telemetry checks (preconditioner id, iterations, residual)
  - explicit solver termination reason code checks across all structural backends
  - advanced matrix-free preconditioning checks (block-Jacobi) and benchmark result reporting
  - matrix-free robustness safeguards verified (residual guardrails, consistency checks, non-finite protections)
  - matrix-free acceptance-threshold evaluation verified for operational/analysis profiles (with strict-threshold failure-path checks)
  - FEM namespace migration-completeness check (tests/imports/docs use canonical `brambhand.structures.fem.*` paths)
  - element stress metric and model-validation checks
- Quality gates currently passing:
  - `ruff check .`
  - `mypy src tests`
  - `pytest -q`

## 7) Definition of done (feature level)
- Requirement IDs linked
- Design sections linked
- Inline API docstrings updated
- Verification tests added + passing
- Validation scenario evidence added
- Traceability row updated in this document
- TODO sequencing updated