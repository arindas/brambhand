## TODO

- [x] Ensure memory management skill is in place (see ./SKILLS.md)
- [x] Formalize requirements
- [x] Outline design and architecture in DESIGN.md
- [x] Maintain verification strategy in VERIFICATION.md
- [x] Keep requirements `->` design `->` actions `->` TODO flow updated

## Next-phase implementation roadmap (from updated requirements)

### R1 — 6-DOF rigid-body and mechanisms baseline
- [x] Complete R1 implementation + contract/integration tests

### R2 — Propulsion fluids, combustion, and thrust estimation
- [x] Complete R2/R2.1 implementation + validation tests (including nozzle geometry sensitivity)

### R2.2 — Internal chamber-flow and leak-jet dynamics coupling
- [x] Implement reduced-order injector-to-throat chamber-flow state model with diagnostics (pressure/temperature/mixing proxies)
- [x] Couple chamber-flow state to thrust estimator/nozzle correction path with deterministic contracts
- [x] Implement leak-jet dynamics model (mass/momentum/thermal state) for propulsion and structural leak paths
- [x] Define versioned leak-jet boundary exchange payload consumed by FSI coupling
- [x] Propagate leak-jet forces/torques into 6-DOF rigid-body dynamics
- [x] Add analytical/consistency tests for chamber-flow + leak-jet force coupling and conservation envelopes
- [x] Add R2.2 latency/cadence benchmark checks against operational profile budgets with explicit reduced-order fallback behavior

### R2.3 — Reduced-order propellant slosh simulation and 6-DOF coupling
- [x] Implement tank slosh state model baseline (lumped pendulum/spring-mass equivalent) with deterministic integration
- [x] Define versioned slosh load export payload consumed by FSI/coupling controller
- [x] Propagate slosh-induced force/torque and effective CoM offsets into rigid-body 6-DOF updates
- [x] Add geometry-aware slosh parameter hooks for STL-derived tank descriptors (with non-STL parameter fallback)
- [x] Add slosh coupling tests (attitude disturbance response + conservation/energy sanity envelopes)
- [x] Add R2.3 latency/cadence benchmark checks against operational profile budgets with explicit degraded-mode controls

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
- [x] Add backend-equivalence and determinism tolerance tests (dense vs sparse modes)
- [x] Add structural latency/memory benchmark suite for 2D vs 3D profiles
- [x] Implement fracture initiation/propagation baseline model
- [x] Implement damage state propagation to mass/stiffness/contact behavior
- [x] Define connected-topology damage payload/state (holes/crack-network evolution without disjoint split) for leak/FSI consumers
- [x] Add structural failure scenario tests (including leak path creation)
- [x] Add end-to-end asteroid-impact fault-chain scenario test for connected-topology damage progression (`impact -> localized damage/hole/crack growth -> leak thrust/moment -> cabin depressurization -> alarm/event propagation`; no disjoint-body split in this R3 test)

### R3.1 — Disjoint-topology transition simulation baseline
- [x] Implement assembly-topology state graph for disjoint-body connectivity (attachments/interfaces between rigid bodies/modules)
- [x] Implement fracture-driven topology split transitions into distinct rigid bodies with deterministic IDs/provenance
- [x] Implement baseline dock/undock attach/detach topology transitions with constraint/contact handoff (lifecycle mission semantics remain in R10)
- [x] Define versioned topology-transition payload for FSI/leak-boundary consumers
- [x] Propagate topology transitions to mass properties, constraints, contact manifolds, and control authority surfaces (graph-level topology effects; material damage-state evolution remains in R3)
- [x] Add determinism/conservation tests for disjoint-topology transitions and replay reconstruction (including split-body provenance and downstream coupling continuity)

### R8.0 — Replay/trajectory quicklook
- [x] Define minimal visualization telemetry contract for trajectory/event extraction from replay artifacts
- [x] Implement headless trajectory quicklook pipeline (2D/3D) from replay JSONL
- [x] Add event markers in quicklook outputs
- [x] Add minimal severity contract in quicklook (`info|warning|critical`) with deterministic event->severity mapping table
- [x] Add basic severity styling in quicklook markers (3-color palette) with backward-compatible extension path for richer UI theming later
- [x] Add `current` vs `planned` trajectory overlay baseline (planned from predictor/scenario intent)
- [x] Add deterministic snapshot tests for quicklook extraction and ordering
- [x] Define compact infographic trajectory widget contract (curve layers + object-icon markers) using shared trajectory render payloads

### R8.05 — Early graphical replay visualization
- [ ] Implement native desktop app shell using SDL3/GLFW platform layer and Dear ImGui docking UI baseline
- [ ] Implement replay JSONL ingest path using the same trajectory/view-model contracts as downstream live mode
- [ ] Implement compact trajectory infographic panel (current/planned curves + object icons) using shared trajectory render contracts
- [ ] Add desktop replay quicklook workflow acceptance tests (trajectory + event-marker readability and deterministic ordering)

### R4 — Fluid-structure interaction coupling
- [x] Implement two-way FSI coupler with convergence residuals
- [x] Implement coupling controller (iteration budget, thresholds, fallback)
- [x] Define backend-neutral FSI fluid-boundary provider contract (shared by reduced-order and optional CFD providers)
- [x] Integrate topology-transition + leak-jet + slosh boundary payloads into FSI exchange contracts
- [x] Define initial coupling policy: partitioned baseline with explicit criteria for monolithic escalation
- [x] Add convergence diagnostics and residual telemetry channels
- [x] Add FSI benchmark tests for coupled stability (including failure/recovery paths)
- [x] Add integrated chain test: `fracture/topology update -> leak/slosh boundary update -> FSI residual convergence/fallback -> 6-DOF response`

### R8.1 — Dashboard data contracts and headless view-models
- [ ] Define versioned mission-control view-model schema (telemetry cards, alarms, timeline, command status)
- [ ] Define versioned onboard view-model schema (flight instruments, subsystem health, cautions/warnings)
- [ ] Define versioned Python-to-desktop stream schema contracts (`state/event/topology/frame metadata`) shared by live stream and replay adapters
- [ ] Implement Python bridge publisher baseline for live streaming with explicit sequence/schema metadata
- [ ] Implement headless view-model builders from committed simulation state + replay metadata
- [ ] Add schema compatibility tests and deterministic serialization tests
- [ ] Add replay-vs-live stream equivalence tests for ordering and timeline continuity
- [ ] Freeze baseline mission-control/onboard layout contracts for downstream UI realization

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

### R8.2 — Geometry-anchored overlay contracts
- [ ] Define crack/fracture/leak overlay schema bound to geometry region IDs
- [ ] Define severe-topology-change marker schema for structural separation fragments (debris-cloud extensions handled in R9)
- [ ] Implement overlay model adapters consuming geometry-to-subsystem mapping metadata
- [ ] Add integration tests for geometry-tag continuity across replay

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
- [ ] Implement structural fallback policy under cadence pressure (`3D -> coarse 3D -> validated 2D proxy`), with explicit operator-visible degraded-mode events
- [ ] Persist pacing/timeline metadata in run/replay artifacts
- [ ] Add timeline equivalence tests across pacing modes

### R8.3 — Replay/timeline UX contracts
- [ ] Define playback control contract (`play/pause/scrub/rate`) and deterministic seek semantics
- [ ] Define replay camera-sync metadata contract and interpolation policy hooks
- [ ] Add timeline equivalence tests for replay controls across pacing modes

### R7.2 — Inter-module orchestration contracts
- [ ] Define versioned inter-module schema contracts for cross-domain exchange
- [ ] Implement explicit model-graph DAG structure (node/edge contracts + cycle rejection)
- [ ] Implement deterministic topological scheduler order derived from model-graph DAG and persist order metadata
- [ ] Implement controlled model-graph mutation transactions at tick boundaries (including topology split/attach events)
- [ ] Implement unit/frame validation at module boundaries
- [ ] Implement explicit fault-propagation event contracts across domains
- [ ] Define cross-partition communication exchange contract for endpoints on different workers (e.g., `ground station <-> spacecraft`), including delivery tick semantics
- [ ] Implement distributed logical tick/barrier compatibility checks
- [ ] Add integration tests for causal ordering, DAG-mutation correctness, and audit-grade replay reconstruction

### R8.4 — Visualization and dashboards (full UI realization after R8.0..R8.3 contracts)
- [ ] Implement mission-control dashboard UI consuming R8.1 schemas/view-model builders (no duplicate backend contract logic)
- [ ] Implement onboard spacecraft dashboard UI consuming R8.1 schemas/view-model builders (no duplicate backend contract logic)
- [ ] Integrate live Python-stream client (gRPC baseline) with bounded buffering/backpressure observability
- [ ] Implement 3D state/damage/leak overlays and event timeline integration consuming R8.2 overlay schemas
- [ ] Implement explicit crack/fracture-path and leak-source visualization overlays
- [ ] Implement topology-discontinuity visualization support for severe failures (e.g., structural separation/snapping)
- [ ] Add operator workflow acceptance tests (latency + usability gates)
- [ ] Add visualization acceptance scenario for post-impact geometry-change overlays and leak/depressurization operator cues

### R8.5 — 3D rendering core
- [ ] Implement Vulkan renderer backend core (device/swapchain/pipeline bootstrap) behind explicit renderer interfaces
- [ ] Implement render scene graph assembly from simulation state
- [ ] Implement frame-graph orchestration for multi-pass rendering (geometry/overlay/volumetric/UI composition)
- [ ] Implement BVH acceleration structures for dynamic geometry
- [ ] Implement ray-marching-capable volumetric rendering pipeline (plume/field views)
- [ ] Implement rendering profiles (operational fast mode vs analysis mode)
- [ ] Implement rich 3D trajectory-curve and moving-object rendering using shared trajectory render contracts
- [ ] Implement deterministic replay camera/timeline synchronization
- [ ] Add rendering V&V tests (frame-time budgets, temporal stability, BVH update costs)
- [ ] Add rendering V&V scenarios for nominal engine plume and off-nominal leak plume visualization (ray-marching profiles)

### R4.1 — Optional CFD-coupled fluid/combustion adapter integration (post-R8.5)
- [ ] Define CFD adapter contracts (mesh/boundary conditions/field exchange/provenance metadata) implementing the R4 backend-neutral fluid-boundary provider contract
- [ ] Add first external CFD adapter integration behind contracts (candidate: OpenFOAM or SU2)
- [ ] Implement cadence-safe co-simulation policy via existing R4 coupling-controller interfaces (no duplicate coupler/controller stack)
- [ ] Add profile-gated performance benchmarks for CFD-coupled mode and fallback-trigger tests
- [ ] Add backend-swap determinism/provenance tests for CFD adapters vs reduced-order baseline envelopes

### R9 — Space debris and compounding accretion prediction
- [ ] Implement debris population state model and scenario integration
- [ ] Implement impact/separation fragment generation model for debris creation events
- [ ] Implement debris orbital propagation integration with core dynamics loop
- [ ] Implement compounding debris accretion/risk-growth predictor (secondary fragment generation feedback)
- [ ] Implement debris-impact coupling hooks into structural damage/leak creation workflows
- [ ] Add debris-centric end-to-end scenarios (including `asteroid strike -> fragment cloud evolution`)
- [ ] Add breakup-assumption sensitivity and casualty-risk uncertainty-band benchmark scenarios

### R10 — Docking lifecycle and booster payload transfer logistics
- [ ] Implement explicit dock/undock lifecycle state machine (approach/capture/hard-dock/detach/clearance)
- [ ] Integrate dock/undock lifecycle transitions with assembly-topology simulation contracts (attach/detach graph updates)
- [ ] Define approach safety-zone/hold-point/collision-avoidance contracts in docking lifecycle flows
- [ ] Implement hold-point authority/permission gating and proceed/abort command semantics
- [ ] Implement collision-avoidance trigger and escape-maneuver contract path from each critical approach segment
- [ ] Implement mission-phase event contracts for payload transfer operations (assembly, burn staging, separation)
- [ ] Persist lifecycle transition/event provenance in replay artifacts (capture/latch/hard-dock/detach/clearance)
- [ ] Implement booster-to-payload transfer guidance/control workflow hooks for UEO/interplanetary missions
- [ ] Implement planetary sphere-of-influence handoff propagation metadata and replay reconstruction checks
- [ ] Add dock/undock lifecycle causal-ordering tests (including hold-point/abort/escape paths)
- [ ] Add end-to-end transfer scenario (`launch -> UEO docking/assembly -> boost out of origin SOI -> destination SOI insertion`)

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

### R13 — Atmospheric launch/ascent and aero-structural behavior
- [ ] Implement atmospheric profile subsystem (density/pressure/temperature/speed-of-sound) with validity-envelope checks
- [ ] Implement aerodynamic load model baseline (drag + extensible lift/side-force) coupled into 6-DOF rigid-body dynamics
- [ ] Implement launch/ascent event sequencer (liftoff/max-q/staging/MECO/atmospheric-exit) with deterministic replay provenance
- [ ] Implement ascent atmospheric-exit and apogee prediction utilities with tolerance-governed propagated-truth checks
- [ ] Implement ascent guidance/attitude-profile control hooks (gravity-turn/profile-following baseline)
- [ ] Implement launch-load buckling risk screening and cyclic fatigue accumulation hooks into fracture-initiation workflows
- [ ] Add integrated launch scenario tests covering drag-loaded ascent, max-q region behavior, atmospheric exit, and apogee prediction
- [ ] Add fatigue/buckling-to-fracture progression scenarios and alarm/event propagation tests

### R14 — Advanced structural fidelity stack
- [ ] Implement nonlinear structural solve baseline (geometric nonlinearity) with convergence diagnostics/termination telemetry
- [ ] Implement material nonlinearity hook contracts (yield/plastic response baseline) with profile-aware model selection
- [ ] Implement transient structural dynamics workflows (modal/direct integration baseline) and replay-compatible state serialization
- [ ] Implement explicit buckling analysis workflows (eigenvalue baseline + post-buckling progression policy)
- [ ] Extend fatigue modeling from threshold hooks to mission-phase fatigue accumulation and crack-growth coupling
- [ ] Implement adaptive refinement/remeshing policy interfaces around structural hot-spots with deterministic remesh provenance
- [ ] Implement thermo-structural coupling hooks (temperature-dependent material properties + thermal-load coupling into stress/buckling/fatigue/fracture workflows)
- [ ] Add advanced structural benchmark suite against trusted references with tolerance-governed acceptance per profile
- [ ] Add degraded-mode/fallback policy tests for advanced structural fidelity under compute-pressure constraints

## Design, verification, and validation documentation gaps
- [x] Complete initial documentation gap closure set (`VALIDATION.md`, `docs/DISTRIBUTED_PROTOCOL.md`, `docs/PERFORMANCE_SLOS.md`)

## Quality hardening
- [x] Raise coverage floor by adding targeted edge/error-path tests for CLI command flows, propulsion validation guards, and constellation validation guards
- [ ] Continue coverage hardening with structural backend failure-branch tests and low-coverage propulsion/dynamics edge paths

## Documentation and traceability
- [x] Sync requirements/design/TODO/V&V docs with implemented R1/R2/R2.1/R3 scope, structural scalability roadmap, and legacy communication continuity requirements
- [ ] Keep requirement-to-design matrix current as architecture evolves
- [ ] Keep V&V traceability matrix current with new evidence
- [ ] Keep VALIDATION scenario/benchmark registry current with new acceptance evidence
- [ ] Keep inline API docs complete for all new public modules
- [ ] Maintain release notes for each semver milestone
- [x] Track unresolved UI/renderer/transport decisions in DESIGN decision log with explicit owner and due milestone (baseline stack fixed to SDL3/GLFW + Dear ImGui + Vulkan + Python gRPC bridge)
