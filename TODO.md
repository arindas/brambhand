## TODO

- [x] Ensure memory management skill is in place (see ./SKILLS.md)
- [x] Formalize requirements
- [x] Outline design and architecture in DESIGN.md
- [x] Maintain verification strategy in VERIFICATION.md
- [x] Keep requirements -> design -> actions -> TODO flow updated

## Next-phase implementation roadmap (from updated requirements)

### R1 — 6-DOF rigid-body and mechanisms baseline
- [x] Define R1 contracts/modules for 6-DOF, mechanisms, docking contact, and control interfaces (`dynamics/*`)
- [x] Implement 6-DOF rigid-body dynamics module (translation + rotation)
- [x] Implement articulated mechanism/joint model for moving components
- [x] Implement docking contact/impact rigid-body baseline
- [x] Add control interfaces for attitude and mechanism actuation
- [x] Add initial contract tests for rigid-body, joints, and docking screening
- [x] Add unit/integration tests for full rigid-body and docking contact behavior

### R2 — Propulsion fluids, combustion, and thrust estimation
- [x] Implement reduced-order fluid network subsystem (tank/line/valve baseline)
- [x] Implement combustion chamber dynamic model (ideal-gas baseline)
- [x] Implement thrust estimator from chamber/flow state (momentum + pressure terms)
- [x] Implement leakage model for propulsion circuits/chassis compartments
- [x] Add baseline analytical validation tests for R2 contracts
- [x] Add nozzle geometry-aware thrust correction model (area ratio/contour losses)
- [x] Add tests for nozzle shape sensitivity in thrust predictions

### R3 — Structural FEM and fracture
- [x] Implement FEM structural evaluation baseline for chassis components
- [x] Document and enforce 2D FEM validity envelope (plane-stress/plane-strain assumptions, excluded 3D effects)
- [x] Implement sparse assembly pipeline for structural FEM (COO/CSR/CSC) and record `nnz` telemetry
- [x] Add structural solver backend abstraction (dense baseline, sparse direct, sparse iterative)
- [x] Implement preconditioned sparse-iterative structural solve path with convergence telemetry
- [x] Implement matrix-free structural operator prototype for large-mesh iterative solves
- [x] Harden matrix-free structural mode to production readiness (robust failure handling, convergence safeguards, deterministic-tolerance characterization)
- [x] Add advanced matrix-free preconditioning options beyond Jacobi and benchmark convergence improvements
- [x] Extend structural convergence telemetry to include explicit solver termination reason codes across all backends
- [x] Define and validate matrix-free acceptance thresholds per mesh/profile class (operational vs analysis)
- [x] Refactor structures solver stack into modular subcomponents (contracts/assembly/backend/acceptance) to reduce module coupling
- [x] Implement 3D solid FEM baseline for chassis components and define model-selection policy (2D vs 3D)
- [x] Reorganize structural FEM implementation into dedicated `structures/fem/` namespace
- [x] Remove legacy structural FEM shim modules (`fem_solver`, `fem_contracts`, `fem_geometry`, `fem_backends`) and migrate all imports/docs/tests to canonical `structures.fem.*` paths
- [ ] Add backend-equivalence and determinism tolerance tests (dense vs sparse modes)
- [ ] Add structural latency/memory benchmark suite for 2D vs 3D profiles
- [ ] Implement fracture initiation/propagation baseline model
- [ ] Implement damage state propagation to mass/stiffness/contact behavior
- [ ] Add structural failure scenario tests (including leak path creation)
- [ ] Add end-to-end asteroid-impact fault-chain scenario test (impact -> localized damage -> leak thrust/moment -> cabin depressurization -> alarm/event propagation)

### R4 — Fluid-structure interaction coupling
- [ ] Implement two-way FSI coupler with convergence residuals
- [ ] Implement coupling controller (iteration budget, thresholds, fallback)
- [ ] Define initial coupling policy: partitioned baseline with explicit criteria for monolithic escalation
- [ ] Add convergence diagnostics and residual telemetry channels
- [ ] Add FSI benchmark tests for coupled stability (including failure/recovery paths)

### R5 — Geometry pipeline (STL import)
- [x] Add idealized/reference STL fixture sets and manifest for geometry-dependent tests
- [ ] Implement STL importer and geometry validation pipeline
- [ ] Implement derived mass/inertia property pipeline (CoM + inertia tensor) with user override checks
- [ ] Implement nozzle geometry extraction from STL (throat/exit/area ratio/contour metrics)
- [ ] Implement collision geometry extraction for docking/contact/mechanism clearance
- [ ] Implement STL-to-FEM preprocessing interfaces and region tagging
- [ ] Implement geometry-anchored damage/leak localization metadata
- [ ] Implement geometry-to-subsystem mapping registry (propulsion/structures/mechanisms/visualization)
- [ ] Add asset versioning + metadata linkage in scenario definitions

### R6 — Persistence and checkpointing
- [ ] Design and implement DB schema for runs/events/telemetry/checkpoints/assets
- [ ] Implement idempotent tick commit model keyed by `(run_id, partition_id, tick_id)`
- [ ] Persist scheduler/pacing/provenance metadata per committed tick
- [ ] Implement persistence adapters for event and telemetry streams
- [ ] Implement checkpoint save/load and restart workflow
- [ ] Add replay determinism tests using persisted artifacts

### R7 — Distributed simulation runtime
- [ ] Implement workload partitioner and synchronization protocol
- [ ] Enforce single-authority partition ownership (no replicas in current scope)
- [ ] Implement logical tick barrier and global atomic commit protocol
- [ ] Implement partition timeout/retry/recovery policy without partial commit divergence
- [ ] Implement distributed orchestrator integration interfaces
- [ ] Implement consistency/tolerance checks across worker boundaries
- [ ] Add multi-node regression and performance tests

### R7.1 — Runtime pacing and time-scale control
- [ ] Implement simulation clock abstraction (simulation time vs wall-clock time)
- [ ] Implement pacing controller (pause/slow/real-time/accelerated/max-throughput)
- [ ] Implement multi-rate scheduler support (physics/control/render ticks)
- [ ] Implement adaptive cadence policy (degrade non-critical workloads to hold cadence)
- [ ] Implement structural fallback policy under cadence pressure (3D -> coarse 3D -> validated 2D proxy), with explicit operator-visible degraded-mode events
- [ ] Persist pacing/timeline metadata in run/replay artifacts
- [ ] Add timeline equivalence tests across pacing modes

### R7.2 — Inter-module orchestration contracts
- [ ] Define versioned inter-module schema contracts for cross-domain exchange
- [ ] Implement unit/frame validation at module boundaries
- [ ] Implement deterministic scheduler-order metadata and enforcement
- [ ] Implement explicit fault-propagation event contracts across domains
- [ ] Define cross-partition communication exchange contract for endpoints on different workers (e.g., ground station <-> spacecraft), including delivery tick semantics
- [ ] Implement distributed logical tick/barrier compatibility checks
- [ ] Add integration tests for causal ordering and audit-grade replay reconstruction

### R8 — Visualization and dashboards
- [ ] Implement mission-control dashboard backend/view models
- [ ] Implement onboard spacecraft dashboard backend/view models
- [ ] Implement 3D state/damage/leak overlays and event timeline integration
- [ ] Implement explicit crack/fracture-path and leak-source visualization overlays
- [ ] Implement topology-discontinuity visualization support for severe failures (e.g., structural separation/snapping)
- [ ] Add operator workflow acceptance tests (latency + usability gates)
- [ ] Add visualization acceptance scenario for post-impact geometry-change overlays and leak/depressurization operator cues

### R8.1 — 3D rendering core
- [ ] Implement render scene graph assembly from simulation state
- [ ] Implement BVH acceleration structures for dynamic geometry
- [ ] Implement ray-marching-capable volumetric rendering pipeline (plume/field views)
- [ ] Implement rendering profiles (operational fast mode vs analysis mode)
- [ ] Implement deterministic replay camera/timeline synchronization
- [ ] Add rendering V&V tests (frame-time budgets, temporal stability, BVH update costs)
- [ ] Add rendering V&V scenarios for nominal engine plume and off-nominal leak plume visualization (ray-marching profiles)

### R9 — Space debris and compounding accretion prediction
- [ ] Implement debris population state model and scenario integration
- [ ] Implement impact/separation fragment generation model for debris creation events
- [ ] Implement debris orbital propagation integration with core dynamics loop
- [ ] Implement compounding debris accretion/risk-growth predictor (secondary fragment generation feedback)
- [ ] Implement debris-impact coupling hooks into structural damage/leak creation workflows
- [ ] Add debris-centric end-to-end scenarios (including asteroid strike -> fragment cloud evolution)
- [ ] Add breakup-assumption sensitivity and casualty-risk uncertainty-band benchmark scenarios

### R10 — Docking lifecycle and booster payload transfer logistics
- [ ] Implement explicit dock/undock lifecycle state machine (approach/capture/hard-dock/detach/clearance)
- [ ] Define approach safety-zone/hold-point/collision-avoidance contracts in docking lifecycle flows
- [ ] Implement mission-phase event contracts for payload transfer operations (assembly, burn staging, separation)
- [ ] Implement booster-to-payload transfer guidance/control workflow hooks for UEO/interplanetary missions
- [ ] Implement planetary sphere-of-influence handoff propagation metadata and replay reconstruction checks
- [ ] Add end-to-end transfer scenario (launch -> UEO docking/assembly -> boost out of origin SOI -> destination SOI insertion)

### R11 — Trajectory optimization and interplanetary mission-analysis adapters
- [ ] Define backend-agnostic trajectory optimization contracts (problem/constraints/objectives/results)
- [ ] Implement trajectory initial-guess generator utilities (Lambert/Hohmann/shape-based seeds)
- [ ] Implement pluggable ephemeris/frame provider contracts with unit/frame validation
- [ ] Implement Hohmann/Lambert workflow adapters behind abstract interfaces
- [ ] Implement gravity-assist encounter/deflection workflow adapters behind abstract interfaces
- [ ] Implement campaign/window sweep orchestration with reproducible provenance ordering
- [ ] Add adapter integration for selected OSS backends (Python-first + C++-backed bindings)
- [ ] Enforce backend-neutral adapter boundaries with integration guards against backend-specific type leakage
- [ ] Add backend-equivalence benchmark scenarios and tolerance envelopes (external vs in-house)
- [ ] Add seed-sensitivity and convergence-basin benchmark scenarios (Lambert-seeded and non-seeded initializations)

### R12 — Advanced mission-analysis parity extensions
- [ ] Implement centralized frame/time provider service used by trajectory/navigation/mission modules and adapters
- [ ] Implement orbit-determination abstraction and estimator adapters (batch LS + sequential filter baseline)
- [ ] Define estimator initialization/process-noise tuning policy and covariance-consistency checks for OD workflows
- [ ] Implement covariance/uncertainty propagation services across burns/flybys/phase transitions
- [ ] Implement Monte Carlo and injection-dispersion campaign workflows with scalable orchestration
- [ ] Implement operational constraint packs for optimization loops (eclipse, comm windows, pointing, keep-out, power/thermal)
- [ ] Implement finite-burn execution realism hooks in targeting/optimization workflows (misalignment/transients/duty cycles)
- [ ] Implement stationkeeping/formation-keeping workflow contracts and long-duration delta-v budgeting tools
- [ ] Implement mission-analysis product generation (maneuver plans, nav summaries, constraint violation reports)
- [ ] Add cross-validation harness against trusted astrodynamics references with tolerance-governed pass/fail criteria
- [ ] Add human-in-the-loop interactive trade-study session capture/replay metadata support

## Design, verification, and validation documentation gaps (reviewed)
- [x] Finalize initial numeric latency/SLO targets per deployment/render profile (`docs/PERFORMANCE_SLOS.md`)
- [x] Document automatic scaling mode-selection thresholds (single-node vs partitioned vs hybrid)
- [x] Document persistence durability policy per artifact class (events/telemetry/checkpoints)
- [x] Document coupling fallback/degraded-mode hierarchy under load
- [x] Add dedicated `VALIDATION.md` for benchmark datasets, acceptance scenarios, and operator workflow criteria
- [x] Add distributed execution protocol spec (`docs/DISTRIBUTED_PROTOCOL.md`) for tick/barrier/commit semantics
- [x] Add performance and pacing SLO doc (`docs/PERFORMANCE_SLOS.md`) tied to NR-018..NR-024, NR-029..NR-031

## Documentation and traceability
- [x] Sync requirements/design/TODO/V&V docs with implemented R1/R2/R2.1/R3 scope, structural scalability roadmap, and legacy communication continuity requirements
- [ ] Keep requirement-to-design matrix current as architecture evolves
- [ ] Keep V&V traceability matrix current with new evidence
- [ ] Keep VALIDATION scenario/benchmark registry current with new acceptance evidence
- [ ] Keep inline API docs complete for all new public modules
- [ ] Maintain release notes for each semver milestone
