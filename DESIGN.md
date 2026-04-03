# DESIGN

## Purpose
This design defines the target architecture for the new high-fidelity requirement set in `REQUIREMENTS.md`, including multi-physics coupling, distributed execution, persistence, and operational visualization.

## Design principles
- **Physics-domain modularity:** rigid body, fluids, combustion, FEM/fracture, and FSI must be independently evolvable.
- **Tiered fidelity:** support reduced-order and high-fidelity modes via interchangeable model adapters.
- **Deterministic orchestration:** deterministic execution/replay for a fixed model set and seed.
- **Observability-first:** all solvers emit convergence/stability diagnostics.
- **Scalable runtime:** single-node and distributed execution share same scenario/telemetry contracts.
- **Operator-centric outputs:** mission-control and onboard views consume stable telemetry/event streams.

## Target architecture

```text
src/brambhand/
  core/
    simulation_runtime.py         # run loop, time stepping, orchestration
    simulation_clock.py           # simulation time vs wall-clock tracking
    pacing_controller.py          # real-time / accelerated / max-throughput control
    scheduler.py                  # subsystem update schedule
    event_bus.py
    state_snapshot.py
  dynamics/
    rigid_body_6dof.py            # translational + rotational dynamics
    mechanisms.py                 # joints, constraints, actuators
    contact_docking.py            # contact/impact dynamics for docking
  propulsion/
    fluid_network.py              # tanks/lines/valves/injectors
    combustion_model.py           # chamber dynamics
    thrust_estimator.py           # force/torque from engine state
    nozzle_geometry.py            # nozzle shape factors from geometry assets
    leakage_model.py              # leak path + mass loss model
  structures/
    fem/
      contracts.py                # FEM contracts and configuration types (2D/3D)
      geometry.py                 # element geometry, constitutive laws, assembly utilities
      backends.py                 # linear solver backend implementations
      solver.py                   # 2D/3D solve orchestration + telemetry
      selection.py                # 2D-vs-3D model-selection policy helpers
    fracture_model.py             # crack initiation/propagation
    structural_state.py           # stiffness/mass degradation state
  coupling/
    fsi_coupler.py                # fluid-structure two-way coupling
    coupling_controller.py        # iteration, residual checks, convergence gates
  geometry/
    stl_import.py                 # STL ingestion
    mass_properties.py            # inertia, CoM derivation/adaptation
    nozzle_extractor.py           # throat/exit/area-ratio extraction from nozzle STL
    mesh_pipeline.py              # collision/FEM mesh preparation
  scenario/
    scenario_schema.py
    scenario_loader.py
    replay_log.py
    checkpoint_store.py
  persistence/
    db_models.py                  # run/scenario/telemetry/event/checkpoint schemas
    event_store.py
    telemetry_store.py
    checkpoint_store.py
  distributed/
    partitioner.py                # workload decomposition
    sync_protocol.py              # inter-worker state sync
    orchestrator_client.py        # job lifecycle integration
  mission/
    docking_lifecycle.py          # approach/capture/dock/undock state machine
    transfer_logistics.py         # booster payload transfer mission phases
    soi_handoff.py                # planetary sphere-of-influence handoff metadata/contracts
  trajectory/
    optimizer_contracts.py        # backend-agnostic optimization interfaces
    trajectory_problem.py         # mission-phase trajectory problem definitions
    ephemeris_provider.py         # pluggable ephemeris/frame provider contracts
    transfer_analysis.py          # Lambert/Hohmann/gravity-assist workflow adapters
    campaign_runner.py            # batch window sweep/trade-study orchestration
    dispersion.py                 # Monte Carlo/dispersion campaign helpers
    constraints.py                # mission operational constraint evaluation contracts
    adapters/                     # OSS backend adapters (swappable)
      scipy_adapter.py
      pykep_adapter.py
      tudat_adapter.py
      orekit_adapter.py
  navigation/
    od_contracts.py               # orbit-determination abstraction interfaces
    covariance_propagation.py     # covariance/uncertainty propagation contracts
    tracking_models.py            # measurement model adapters
  mission_products/
    report_generator.py           # maneuver/nav/constraint report products
    product_schema.py             # versioned ops-product schemas
  debris/
    debris_population.py          # debris entity catalog + propagation state
    debris_fragmentation.py       # impact/separation fragment generation models
    accretion_predictor.py        # compounding debris-risk growth prediction
  visualization/
    telemetry_api.py              # dashboard backend API
    mission_control_view_model.py
    onboard_view_model.py
    damage_overlay_model.py
    scene_graph.py                # renderable scene assembly from sim state
    bvh_acceleration.py           # BVH build/update/query pipeline
    raymarch_pipeline.py          # volumetric rendering pipeline
    renderer_profiles.py          # operational vs analysis render modes
    replay_camera_sync.py         # deterministic camera/timeline sync
  cli.py
```

## Runtime data flow
1. Load versioned scenario + geometry assets.
2. Build model graph (rigid bodies, fluid networks, combustion, structures, couplers).
3. For each time step:
   - update controls/commands
   - propagate rigid-body/mechanism states
   - solve propulsion fluid/combustion subsystem
   - execute FSI + structural updates (iterative if required)
   - compute thrust/torque, contacts, and damage/leak/topology-change updates
   - update debris population/fragment propagation and accretion-risk state
   - process mission-phase logistics (dock/undock lifecycle, booster transfer phases, planetary handoff states)
   - evaluate communication LOS/range and delayed channel deliveries
   - emit diagnostics/events/telemetry snapshots
   - persist state and optional checkpoint
4. Apply pacing controller policy (wall-clock synchronization, throttle mode, or max-throughput).
5. Build visualization scene graph and update acceleration structures.
6. Render selected views using profile-specific raster/ray-march pipelines.
7. Stream telemetry/events and rendered states to mission-control and onboard dashboards.
8. Optionally distribute subsystems across workers with sync barriers.

## Fidelity strategy
- **F0:** Reduced-order, fast mission planning (current baseline extended).
- **F1:** Intermediate engineering mode (lumped fluids + simplified structures).
- **F2:** High-fidelity mode (CFD/FEM coupled, fracture-enabled selected components).

All modes share scenario and telemetry contracts; adapter interfaces isolate solver details.

## Persistence and database model (conceptual)
- `scenarios` (versioned input + asset refs)
- `runs` (config, model versions, seed, worker topology)
- `events` (ordered timeline)
- `telemetry_samples` (time-series channels)
- `checkpoints` (state blobs + metadata)
- `assets` (STL and derived meshes/properties)

## Distributed execution model
- Partition by subsystem and/or vehicle group.
- **Single-authority partition ownership** (no partition replicas in current scope).
- Use deterministic logical tick barriers.
- Define synchronization contracts:
  - state exchange payload schema
  - max tolerated staleness/consistency drift
  - convergence/coupling residual exchange

## Concurrency and parallelism model (distributed, no replicas)

### Execution hierarchy
1. **Inter-run parallelism**: multiple independent runs can execute in parallel.
2. **Intra-run partition parallelism**: one run is split into partitions across workers.
3. **Intra-partition module scheduling**: modules execute by dependency graph per tick.

### Per-tick protocol (authoritative partition owners)
For tick `k -> k+1`:
1. `LOCAL_COMPUTE`: each partition owner computes tentative next state.
2. `BOUNDARY_EXCHANGE`: owners exchange required boundary/coupling data.
3. `RECONCILE`: apply boundary updates and coupling checks.
4. `BARRIER_PREPARE`: partition reports ready-to-commit for tick `k+1`.
5. `GLOBAL_COMMIT`: scheduler commits tick only when all required partitions are ready.
6. `PERSIST_EMIT`: persist tick artifacts and emit telemetry/events.

No partition commits early outside this protocol.

### Recovery policy
If a partition misses barrier deadline:
- deterministic retry window
- optional repartition/reassignment
- or controlled run pause

No silent partial commit is permitted.

## Persistence linkage for distributed ticks
Persistence stores commit-grade artifacts keyed by `(run_id, partition_id, tick_id)`:
- partition state digest/checkpoint pointer
- ordered events/telemetry payload references
- scheduler order and pacing metadata
- worker provenance metadata

Write semantics:
- idempotent tick writes
- commit-order reads based on logical tick, not ingestion order
- replay reconstruction uses committed global tick order

## Requirements -> Design traceability matrix

| Requirement group | Primary architecture areas |
|---|---|
| FR-001..FR-005 | `dynamics/*`, `core/*` |
| FR-006..FR-010, FR-031 | `propulsion/*`, `geometry/nozzle_extractor.py` |
| FR-011..FR-015, FR-072..FR-073, FR-081 | `coupling/*`, `structures/*`, `dynamics/contact_docking.py` (current: 2D + 3D FEM baselines with model selection; planned: fracture/topology-separation progression) |
| FR-074..FR-080 | `structures/fem/*` (contracts/geometry/backends/solver/selection), solver telemetry channels, runtime config/profile selectors |
| FR-016..FR-018, FR-032..FR-037, FR-082 | `geometry/*`, `structures/*`, `dynamics/*`, `visualization/*`, `scenario/*`, `persistence/assets` |
| FR-019..FR-021, FR-064..FR-066 | `scenario/*`, `persistence/*`, `core/state_snapshot.py`, replay metadata contracts |
| FR-022..FR-024, FR-059..FR-063 | `distributed/*`, `core/scheduler.py`, barrier commit protocol |
| FR-025..FR-028 | `visualization/telemetry_api.py`, `mission_control_view_model.py`, `onboard_view_model.py`, `damage_overlay_model.py` |
| FR-038..FR-043, FR-083 | `visualization/scene_graph.py`, `bvh_acceleration.py`, `raymarch_pipeline.py`, `renderer_profiles.py`, `replay_camera_sync.py` |
| FR-084..FR-085 | `debris/*`, `dynamics/*`, `scenario/*`, `persistence/*`, `visualization/*` |
| FR-086..FR-090 | `operations/*`, `guidance/*`, `dynamics/contact_docking.py`, transfer/orchestration workflows, scenario/replay mission-phase metadata |
| FR-091..FR-102 | `trajectory/*`, `mission/*`, `guidance/*`, scenario mission-phase DSL/contracts, persistence provenance for optimization campaigns |
| FR-103..FR-114 | `navigation/*`, `trajectory/*`, `mission_products/*`, constraint/dispersion services, benchmark-validation harnesses, interactive analysis session metadata |
| FR-115..FR-118 | `structures/fem/*` decomposition boundaries and namespace policy, `trajectory/*` adapter contracts, shared frame/time provider services across trajectory/navigation/mission modules |
| FR-044..FR-048 | `core/simulation_clock.py`, `core/pacing_controller.py`, `core/scheduler.py`, replay/persistence metadata |
| FR-049..FR-058 | `core/scheduler.py`, `core/simulation_runtime.py`, contract schemas, unit/frame validators, distributed sync protocol, replay metadata |
| FR-067..FR-071 | `physics/*`, `communication/*`, `guidance/*`, `operations/*`, `scenario/*`, `cli.py`, regression test suites |
| FR-029..FR-030 | diagnostics emitted by all solver domains + run metadata persistence |

## Geometry dependency matrix (STL influence)

| Subsystem | STL-derived inputs |
|---|---|
| Rigid-body dynamics | CoM, inertia tensor, reference frames |
| Contact/docking/mechanisms | Collision mesh, contact normals, clearance envelopes |
| Propulsion nozzle model | Throat area, exit area, area ratio, contour loss factors |
| Structures/FEM/fracture | Surface/volume mesh inputs, region tagging |
| Leakage/fault propagation | Damage/leak location anchors and local geometry parameters |
| Debris/fragmentation | Break/split surfaces and fragment seed regions for post-failure debris generation |
| Visualization | 3D meshes + crack/fracture/leak overlays and topology-change states registered to geometry |

## Clock-linked subsystem policy
All time-dependent subsystems are clock-linked through the runtime scheduler:
- dynamics/mechanisms/contact
- propulsion/combustion/leakage
- structures/fracture/FSI
- communication delay/link models
- persistence sampling/checkpointing
- visualization update/interpolation/replay camera sync

## Hybrid scaling deployment modes
1. **Single-node operational mode**
   - multi-rate scheduler, real-time pacing target, reduced render profile
2. **Single-node throughput mode**
   - max-throughput pacing, batch/offline analysis, relaxed wall-clock coupling
3. **Distributed partitioned mode**
   - one authoritative owner per partition, barrier commit per tick
4. **Hybrid portfolio mode**
   - many runs distributed across nodes + large runs internally partitioned

Selection policy (runtime/orchestrator):
- choose mode based on scenario size, fidelity level, and latency target profile.

## Module concurrency/parallelism matrix

| Module group | Tick coupling | Parallelism model | Commit scope |
|---|---|---|---|
| Dynamics/mechanisms/contact | hard-coupled to physics tick | parallel across partitions; ordered within partition DAG | global tick barrier |
| Propulsion/combustion/leakage | hard-coupled to physics tick | parallel across partitions; partially parallel within partition | global tick barrier |
| Structures/fracture/FSI | hard-coupled (possibly iterative) | parallel across partitions where decoupled; iterative coupling barriers | global tick barrier |
| Communication | soft-coupled (delay queues + link checks) | parallel link evaluations | global tick barrier for authoritative state changes |
| Persistence | post-commit coupled | async batched writes, idempotent by tick key | committed tick artifacts |
| Visualization | decoupled multi-rate from physics | concurrent render/update pipelines with interpolation | frame output tied to committed sim state |

## Latency and backpressure control
- Pacing controller monitors cadence error, scheduler lag, persistence latency, and structural solver pressure.
- Backpressure policy order:
  1. reduce non-critical visualization quality/frequency,
  2. reduce telemetry sampling rate (within policy bounds),
  3. reduce structural solve cadence/fidelity by policy (e.g., backend switch dense->sparse iterative, optional coarse mesh mode),
  4. pause/slow simulation when commit safety at risk.
- Persistence writes remain idempotent and commit-ordered; ingestion lag must not reorder replay semantics.

## Trajectory optimization and mission-analysis adapter strategy (adopt-first)

Adopt open-source trajectory/mission-analysis libraries behind stable contracts,
with in-house fallback implementations remaining possible without scenario-schema churn.

Adapter-oriented design:
- `trajectory/optimizer_contracts.py`
  - defines problem/constraint/objective and solve-result contracts
- `trajectory/ephemeris_provider.py`
  - defines ephemeris/frame provider interface and validation hooks
- `trajectory/transfer_analysis.py`
  - defines Hohmann/Lambert/gravity-assist workflow APIs independent of backend
- `trajectory/campaign_runner.py`
  - batch trade-study orchestration and provenance capture
- `navigation/od_contracts.py`
  - defines orbit-determination estimation contracts and covariance outputs
- `trajectory/constraints.py`
  - operational-constraint evaluation interfaces (eclipse/pointing/keep-out windows)
- `mission_products/report_generator.py`
  - standardized maneuver/nav/constraint analysis product generation

Candidate OSS backends (through adapters, not hard-coupled):
- Python-first:
  - `scipy` optimization stack for constrained solves and baseline campaigns
  - `poliastro` utilities for astrodynamics workflows where suitable
  - `spiceypy`/`jplephem` for ephemeris support
  - `filterpy`/SciPy-based estimation blocks for OD baseline workflows
- C++-backed (via Python bindings/adapters):
  - `pykep`/`pagmo` for trajectory optimization and Lambert/flyby workflows
  - `tudatpy` (Tudat) for higher-fidelity astrodynamics propagation/analysis
  - Orekit Python integrations for operational mission-analysis and OD workflows where adopted
  - CSPICE-backed services (via wrappers) for production ephemeris/time/frame support

Contract rules:
- scenario DSL references abstract trajectory backend IDs/config, not library-specific options
- runtime performs unit/frame normalization before/after adapter calls
- persisted outputs include backend/provenance metadata for replay and audits
- adapter swap must preserve tolerance-bounded equivalence on benchmark scenarios

Coupling-mitigation implementation policy:
- split high-complexity solver modules (e.g., structural solver stack) into:
  1) contracts/types,
  2) assembly/preprocessing,
  3) backend execution,
  4) acceptance/diagnostics utilities.
- prohibit backend-specific classes from crossing `trajectory/*`, `navigation/*`, and `mission/*` public interfaces.
- route all frame/time conversions through shared provider services (no adapter-local divergent conversion logic).

## Remaining design decisions to refine
- Initial latency/SLO targets are documented in `docs/PERFORMANCE_SLOS.md`; refine with benchmark data.
- Initial mode-selection thresholds are documented in `docs/PERFORMANCE_SLOS.md`; tune with production workload evidence.
- Initial persistence durability policy is documented in `docs/DISTRIBUTED_PROTOCOL.md`; finalize per deployment tier.
- Initial fallback/degraded-mode hierarchy is documented in `docs/DISTRIBUTED_PROTOCOL.md`; refine with coupling stress tests.
- FSI coupling policy needs explicit first-cut criteria for partitioned baseline operation vs monolithic escalation under instability/additional-mass sensitivity.

## Incremental implementation roadmap
- **R1: 6-DOF core + mechanisms + docking contact baseline**
- **R2: Propulsion fluid network + combustion + thrust estimation + leakage**
- **R2.1: Nozzle geometry-aware thrust corrections (with STL-derived parameters)**
- **R3: FEM structural solver + fracture pipeline**
- **R4: FSI coupler and convergence diagnostics**
- **R5: STL ingestion and geometry-to-physics pipeline**
- **R6: Database persistence and checkpoint/restart**
- **R7: Distributed runtime partition/sync/orchestration**
- **R7.1: Runtime pacing and time-scale control (multi-rate scheduling + cadence policy)**
- **R7.2: Inter-module orchestration contracts and audit-grade replay provenance**
- **R8: Mission-control + onboard dashboard stack**
- **R8.1: 3D rendering core (scene graph, BVH, ray-marching, replay camera sync)**
- **R9: Space debris environment + compounding accretion prediction**
- **R10: Docking lifecycle + booster payload transfer logistics + interplanetary SOI handoff**
- **R11: Trajectory optimization + interplanetary mission-analysis adapters (Hohmann/Lambert/gravity-assist + campaign orchestration)**
- **R12: Advanced mission-analysis parity extensions (OD/covariance/dispersion/ops constraints/mission products/benchmark cross-validation)**

## Current implementation status snapshot
- R1 baseline implemented in `dynamics/*` with expanded rigid-body/docking contract tests.
- R2 baseline implemented in `propulsion/*` (fluid network, combustion, thrust estimate, leakage).
- R2.1 baseline implemented in `propulsion/thrust_estimator.py` with geometry-aware area-ratio and contour-loss correction.
- R3 baseline provides linear static 2D and 3D FEM evaluation in `structures/fem/solver.py`.
- Structural solver stack is modularized under `structures/fem/*`: contracts (`contracts.py`), geometry/assembly (`geometry.py`), backend solvers (`backends.py`), selection policy (`selection.py`), and orchestration facade (`solver.py`).
- R3 now enforces 2D validity envelopes (plane-stress/plane-strain mode selection, thickness/span guardrails, out-of-plane rejection, small-strain guard).
- R3 now uses sparse assembly (COO->CSR) for 2D baseline stiffness with `nnz` telemetry emission.
- R3 now provides structural solver backend abstraction for reduced systems (dense direct, sparse direct, sparse iterative).
- R3 sparse-iterative path now supports configurable preconditioning (Jacobi/none) with convergence telemetry (iterations/residual).
- R3 includes matrix-free iterative reduced-system solves for large-mesh pressure scenarios.
- Matrix-free mode includes hardening safeguards: residual guardrails, optional consistency-check against sparse-direct reference, and non-finite/operator protections.
- Matrix-free path includes advanced preconditioning beyond Jacobi (node-wise block-Jacobi) and benchmark utility hooks for convergence comparison.
- Structural telemetry now includes explicit solver termination reason codes across dense/sparse/matrix-free backends.
- Matrix-free acceptance thresholds are now defined/validated for operational and analysis profiles via telemetry-based evaluators.

## Design -> Verification linkage
`VERIFICATION.md` defines V&V evidence per requirement group and per roadmap phase.

## Non-functional linkage note
This design primarily maps functional requirement IDs to architecture surfaces.
Non-functional requirement realization is tracked through:
- `docs/PERFORMANCE_SLOS.md` (latency/cadence/render/structural scalability targets)
- `docs/DISTRIBUTED_PROTOCOL.md` (commit, retry, durability, determinism semantics)
- `VERIFICATION.md` (NR-specific evidence plan and acceptance checks).