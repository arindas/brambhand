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
    fem_solver.py                 # stress/strain solving
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
   - compute thrust/torque, contacts, and damage/leak updates
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
| FR-011..FR-015 | `coupling/*`, `structures/*`, `dynamics/contact_docking.py` |
| FR-016..FR-018, FR-032..FR-037 | `geometry/*`, `structures/*`, `dynamics/*`, `visualization/*`, `scenario/*`, `persistence/assets` |
| FR-019..FR-021, FR-064..FR-066 | `scenario/*`, `persistence/*`, `core/state_snapshot.py`, replay metadata contracts |
| FR-022..FR-024, FR-059..FR-063 | `distributed/*`, `core/scheduler.py`, barrier commit protocol |
| FR-025..FR-028 | `visualization/telemetry_api.py`, `mission_control_view_model.py`, `onboard_view_model.py`, `damage_overlay_model.py` |
| FR-038..FR-043 | `visualization/scene_graph.py`, `bvh_acceleration.py`, `raymarch_pipeline.py`, `renderer_profiles.py`, `replay_camera_sync.py` |
| FR-044..FR-048 | `core/simulation_clock.py`, `core/pacing_controller.py`, `core/scheduler.py`, replay/persistence metadata |
| FR-049..FR-058 | `core/scheduler.py`, `core/simulation_runtime.py`, contract schemas, unit/frame validators, distributed sync protocol, replay metadata |
| FR-029..FR-030 | diagnostics emitted by all solver domains + run metadata persistence |

## Geometry dependency matrix (STL influence)

| Subsystem | STL-derived inputs |
|---|---|
| Rigid-body dynamics | CoM, inertia tensor, reference frames |
| Contact/docking/mechanisms | Collision mesh, contact normals, clearance envelopes |
| Propulsion nozzle model | Throat area, exit area, area ratio, contour loss factors |
| Structures/FEM/fracture | Surface/volume mesh inputs, region tagging |
| Leakage/fault propagation | Damage/leak location anchors and local geometry parameters |
| Visualization | 3D meshes + damage/leak overlays registered to geometry |

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
- Pacing controller monitors cadence error, scheduler lag, and persistence latency.
- Backpressure policy order:
  1. reduce non-critical visualization quality/frequency,
  2. reduce telemetry sampling rate (within policy bounds),
  3. pause/slow simulation when commit safety at risk.
- Persistence writes remain idempotent and commit-ordered; ingestion lag must not reorder replay semantics.

## Remaining design decisions to refine
- Initial latency/SLO targets are documented in `docs/PERFORMANCE_SLOS.md`; refine with benchmark data.
- Initial mode-selection thresholds are documented in `docs/PERFORMANCE_SLOS.md`; tune with production workload evidence.
- Initial persistence durability policy is documented in `docs/DISTRIBUTED_PROTOCOL.md`; finalize per deployment tier.
- Initial fallback/degraded-mode hierarchy is documented in `docs/DISTRIBUTED_PROTOCOL.md`; refine with coupling stress tests.

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

## Design -> Verification linkage
`VERIFICATION.md` defines V&V evidence per requirement group and per roadmap phase.