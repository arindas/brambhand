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
    model_graph.py               # DAG nodes/edges, validation, mutation transactions
    simulation_runtime.py         # run loop, time stepping, orchestration
    simulation_clock.py           # simulation time vs wall-clock tracking
    pacing_controller.py          # real-time / accelerated / max-throughput control
    scheduler.py                  # subsystem update schedule (executes model-graph order)
    event_bus.py
    state_snapshot.py
  dynamics/
    rigid_body_6dof.py            # translational + rotational dynamics
    mechanisms.py                 # joints, constraints, actuators
    contact_docking.py            # contact/impact dynamics for docking
    aerodynamic_loads.py          # drag/lift/side-force models for atmosphere-coupled phases
  atmosphere/
    atmosphere_profile.py         # density/pressure/temperature/speed-of-sound profiles
  launch/
    ascent_events.py              # liftoff/max-q/staging/MECO/atmospheric-exit event sequencing
    ascent_prediction.py          # atmospheric-exit and apogee predictors
    ascent_guidance.py            # launch/ascent attitude-profile control workflows
  fluid/
    contracts.py                  # backend-neutral fluid boundary/load contracts
    reduced/
      chamber_flow.py             # injector-to-throat internal flow/combustion field baseline
      slosh_model.py              # reduced-order slosh state + force/torque coupling
      leak_jet_dynamics.py        # leak jet momentum/thermal state and force coupling
    cfd/
      contracts.py                # optional CFD provider contracts
      adapters/
        openfoam_adapter.py
        su2_adapter.py
  propulsion/
    fluid_network.py              # tanks/lines/valves/injectors
    combustion_model.py           # chamber dynamics
    thrust_estimator.py           # force/torque from engine/fluid state
    nozzle_geometry.py            # nozzle shape factors from geometry assets
    leakage_model.py              # leak path + mass loss model
  structures/
    fem/
      contracts.py                # FEM contracts and configuration types (2D/3D)
      geometry.py                 # element geometry, constitutive laws, assembly utilities
      backends.py                 # linear solver backend implementations
      solver.py                   # 2D/3D solve orchestration + telemetry
      selection.py                # 2D-vs-3D model-selection policy helpers
      nonlinear.py                # geometric nonlinearity workflows
      materials.py                # material nonlinearity/plastic constitutive hooks
      transient.py                # transient structural dynamics workflows
      buckling.py                 # eigenvalue/post-buckling analysis policies
      adaptivity.py               # adaptive refinement/remeshing policy contracts
      thermal_coupling.py         # temperature-dependent material and thermal-load coupling hooks
    fracture_model.py             # crack initiation/propagation
    buckling_screen.py            # launch-load buckling risk screening
    fatigue_model.py              # cyclic fatigue accumulation and threshold checks
    structural_state.py           # stiffness/mass degradation state
    connected_topology.py         # connected-topology damage state (holes/crack-networks without body split)
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
    docking_lifecycle.py          # approach/capture/dock/undock state machine + safety-zone/hold-point/abort contracts
    assembly_topology.py          # disjoint-body attachment graph + topology transition simulation (dock/undock/fracture splits)
    transfer_logistics.py         # booster payload transfer mission phases
    soi_handoff.py                # planetary sphere-of-influence handoff metadata/contracts
  trajectory/
    optimizer_contracts.py        # backend-agnostic optimization interfaces
    trajectory_problem.py         # mission-phase trajectory problem definitions
    initial_guess.py              # Lambert/Hohmann/shape-based initial guess generators
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
    od_tuning_policy.py           # estimator initialization/process-noise tuning policy contracts
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
  bridge/
    protocol/
      stream_schema.py            # versioned state/event/timeline transport contracts
    server_py/
      stream_publisher.py         # Python runtime stream bridge (live mode)
      replay_adapter.py           # replay-log to stream-contract adapter
  client_desktop/
    platform/
      windowing.py                # SDL3/GLFW lifecycle abstraction
    stream/
      grpc_client.py              # live-stream ingestion channel
      ring_buffer.py              # bounded buffering/backpressure controls
    replay/
      replay_ingest.py            # replay JSONL ingest for offline mode
    ui/
      imgui_shell.py              # Dear ImGui docking shell and view panes
    render/
      vulkan/
        device.py                 # Vulkan device/swapchain setup
        frame_graph.py            # render-graph orchestration
        scene_renderer.py         # scene draw passes
        bvh_pipeline.py           # acceleration-structure build/update
        volumetric_pass.py        # ray-marching volumetric pass
      overlays/
        event_markers.py
        damage_overlays.py
  cli.py
```

## Runtime data flow

Normative runtime behavior is defined by text in this section and related contract sections.
The diagrams below are supplemental visual aids only.
All labeled diagram stages are explicitly defined in the textual stage list below; no additional semantics are implied by diagram layout.

```text
           ┌──────────────────────────┐    ┌──────────────────────────┐
           │         scenario         │    │          assets          │
           └────────────┬─────────────┘    └────────────┬─────────────┘
                        │                               │
                        └───────────────┬───────────────┘
                                        ▼
                ┌──────────────────────────────────────────────┐
                │      model_graph_dag.build().validate()      │
                └───────────────────────┬──────────────────────┘
                                        │
                                        ▼
                ┌──────────────────────────────────────────────┐
                │               tick loop k -> k+1             │
                └───────────────────────┬──────────────────────┘
                                        │
                                        ▼
                ┌──────────────────────────────────────────────────┐
                │ persist_commit_artifacts + emit_telemetry_events │
                └───────────────────────┬──────────────────────────┘
                                        │
                                        ▼
                ┌──────────────────────────────────────────────┐
                │   build_scene_graph + render_selected_views  │
                └───────────────────────┬──────────────────────┘
                                        │
                          ┌─────────────┴─────────────┐
                          ▼                           ▼
            ┌────────────────────────┐   ┌────────────────────────┐
            │ mission_control_output │   │     onboard_output     │
            └────────────────────────┘   └────────────────────────┘
```

Tick-loop detail (textual, authoritative):
- controls/commands update
- atmosphere + aero loads (where applicable)
- rigid-body/mechanism propagation
- fluid/combustion solve
- FSI + structural update (iterative when required)
- thrust/torque/contact + damage/leak/topology updates
- debris update
- mission-phase logistics update
- communication LOS/delay update
- diagnostics/events/telemetry emission
- state persistence/checkpoint

Textual stage definitions (authoritative):
1. **Scenario + Assets**: load versioned scenario configuration and referenced assets.
2. **Model Graph DAG build + validation**: instantiate subsystem nodes/edges, validate contracts, reject cycles.
3. **Tick Loop `k -> k+1`**: execute deterministic topological module order for one logical tick.
4. **Persist + Telemetry Emit**: emit diagnostics/events/telemetry and persist committed tick artifacts (this is the terminal subphase of each tick loop).
5. **Pacing Policy**: apply wall-clock synchronization/throttle/throughput control for next tick scheduling.
6. **Scene Graph + Rendering**: build renderable state from committed simulation state and execute selected render pipeline.
7. **Mission-Control / Onboard Outputs**: deliver telemetry/view-model/render outputs to operator-facing consumers.
8. **Distributed sync extension (optional)**: when partitioned, tick progression is gated by barrier protocol before global commit.

Required execution decisions:
1. Load versioned scenario + geometry assets.
2. Build and validate model graph DAG (node contracts, edge contracts, cycle rejection).
3. Execute each tick in deterministic topological order from the validated DAG.
4. Apply model-graph mutations only at tick boundaries via explicit mutation transactions.
5. Apply pacing controller policy (wall-clock sync, throttle, or max-throughput).
6. Build visualization scene graph and render selected views from committed state.
7. Stream telemetry/events/rendered state to operator surfaces.
8. Optionally distribute subsystems across workers with sync barriers.

## Explicit cross-domain coupling chain (failure-aware)

To avoid integration ambiguity, the following coupling sequence is explicit:
1. `structures/*` emits damage/fracture updates in two classes: connected-topology evolution (holes/crack-networks) and disjoint split events (including region IDs and separation markers).
2. `mission/assembly_topology.py` resolves disjoint-body attachment graph updates and affected interfaces.
3. `fluid/reduced/*` (reduced-order) or `fluid/cfd/*` (optional CFD) resolves leak-path/slosh/chamber boundary disturbances for affected regions via a shared boundary-provider contract.
4. `coupling/fsi_coupler.py` ingests structural + propulsion boundary updates through that shared contract and computes coupled residuals.
5. `dynamics/*` consumes resulting coupled force/torque updates (including leak-jet/slosh contributions).
6. telemetry/persistence records residuals, fallback mode, and provenance for replay.

Contract requirement: each step uses versioned schemas and deterministic ordering at tick boundaries.

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

```text
Inter-run level:      Run A │ Run B │ Run C
                      │
                      ▼
Intra-run level:      Partition P1 │ Partition P2 │ Partition P3
                      │
                      ▼
Intra-partition:      model-graph DAG execution per tick
                      (deterministic topological order)
```

Textual hierarchy definitions (authoritative):
1. **Inter-run parallelism**: independent runs execute in parallel; no state is shared across runs.
2. **Intra-run partition parallelism**: one run is split across authoritative partition owners.
3. **Intra-partition scheduling**: model-graph DAG nodes execute in deterministic topological order per tick.

### Per-tick protocol (authoritative partition owners)

```text
Tick k -> k+1

         ┌───────────────────┐
         │   LOCAL_COMPUTE   │
         └─────────┬─────────┘
                   │
                   ▼
         ┌───────────────────┐
         │ BOUNDARY_EXCHANGE │
         └─────────┬─────────┘
                   │
                   ▼
         ┌───────────────────┐
         │     RECONCILE     │
         └─────────┬─────────┘
                   │
                   ▼
         ┌───────────────────┐
         │  BARRIER_PREPARE  │
         └─────────┬─────────┘
                   │ all required partitions ready?
                   ▼
         ┌───────────────────┐
         │   GLOBAL_COMMIT   │
         └─────────┬─────────┘
                   │
                   ▼
         ┌───────────────────┐
         │    PERSIST_EMIT   │
         └───────────────────┘
```

Protocol step definitions (authoritative):
1. `LOCAL_COMPUTE`: partition owner computes tentative next state.
2. `BOUNDARY_EXCHANGE`: owners exchange required coupling/boundary data.
3. `RECONCILE`: apply boundary updates and coupling checks.
4. `BARRIER_PREPARE`: report readiness for tick commit.
5. `GLOBAL_COMMIT`: commit only when all required partitions are ready.
6. `PERSIST_EMIT`: persist tick artifacts and emit telemetry/events for the committed tick.

Ordering guarantee: `GLOBAL_COMMIT` strictly precedes `PERSIST_EMIT` for a given tick.
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

## Requirements `->` Design traceability matrix

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
| FR-119..FR-124 | `atmosphere/*`, `dynamics/aerodynamic_loads.py`, `launch/*`, `structures/buckling_screen.py`, `structures/fatigue_model.py`, coupling into `dynamics/*` + `structures/fracture_model.py` |
| FR-125..FR-131 | `structures/fem/nonlinear.py`, `structures/fem/materials.py`, `structures/fem/transient.py`, `structures/fem/buckling.py`, `structures/fem/adaptivity.py`, `structures/fem/thermal_coupling.py`, `structures/fracture_model.py`, `geometry/mesh_pipeline.py`, runtime profile/fallback selectors |
| FR-132..FR-137 | `fluid/reduced/*`, `fluid/cfd/*`, `fluid/contracts.py`, `propulsion/*`, `mission/assembly_topology.py`, `coupling/*`, `dynamics/*`, `structures/*` (including connected-topology state), replay/persistence topology provenance |
| FR-139..FR-145 | `bridge/protocol/*`, `bridge/server_py/*`, `client_desktop/platform/*`, `client_desktop/ui/*`, `client_desktop/render/vulkan/*`, `client_desktop/stream/*`, `client_desktop/replay/*`, `visualization/*`, replay/stream equivalence contracts |
| FR-044..FR-048 | `core/simulation_clock.py`, `core/pacing_controller.py`, `core/scheduler.py`, replay/persistence metadata |
| FR-049..FR-058, FR-138 | `core/model_graph.py`, `core/scheduler.py`, `core/simulation_runtime.py`, contract schemas, unit/frame validators, distributed sync protocol, replay metadata |
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
  3. reduce structural solve cadence/fidelity by policy (e.g., backend switch `dense->sparse iterative`, optional coarse mesh mode),
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

## Fluid/combustion CFD adapter strategy (post-core, cadence-guarded)

Adopt optional external CFD solvers behind stable propulsion adapter contracts,
with reduced-order chamber/slosh/leak models as the default operational path.

Adapter-oriented design (proposed):
- `fluid/contracts.py`
  - backend-neutral fluid boundary/load exchange contracts consumed by propulsion/FSI
- `fluid/cfd/contracts.py`
  - mesh/boundary-condition/field-exchange and provenance contracts for CFD providers
- `fluid/cfd/adapters/openfoam_adapter.py`
- `fluid/cfd/adapters/su2_adapter.py`

Candidate external packages (through adapters):
- OpenFOAM (via file/IPC/service adapter boundaries)
- SU2 (via Python/service wrappers)

Contract rules:
- no CFD backend types cross `fluid/*`/`propulsion/*` public interfaces
- CFD adapters implement the same FSI-facing boundary-provider contract used by reduced-order fluid models
- R4 owns coupling/controller logic; R4.1 must extend fluid providers only (no duplicate FSI coupler/controller stack)
- CFD mode is profile-gated and optional; reduced-order mode remains canonical fallback
- cadence guard must trigger deterministic fallback (`CFD -> reduced-order`) when budgets are exceeded
- persisted run artifacts include adapter/backend/version/config provenance for replay

## Interleaved visualization delivery design (R8.0..R8.5)

To provide operator-visible feedback earlier, visualization is decomposed into explicitly ordered milestones interleaved with core physics/runtime delivery.

Execution order (authoritative):
1. R8.0 after R3
2. R8.1 after R4
3. R8.2 after R5
4. R8.3 after R7.1
5. R8.4 after R7.2
6. R8.5 after R8.4

### R8.0 — Replay/trajectory quicklook (low risk, immediate)
- Inputs: `scenario/replay_log.py` records + deterministic body summaries emitted by run workflows.
- Outputs:
  - trajectory plotting artifacts (2D/3D quicklook)
  - event markers on timeline/trajectory (`simulation_started`, `step_completed`, and later command/fault events)
  - minimal severity encoding (`info|warning|critical`) with deterministic event->severity mapping and basic 3-color styling
  - optional overlay support for `current` vs `planned` traces.
- Architecture surface:
  - `visualization/quicklook_contracts.py` (versioned quicklook extraction contracts)
  - `visualization/quicklook_pipeline.py` (headless extraction + 2D/3D pipeline adapters)
  - `visualization/trajectory_overlay.py` (trace alignment utilities)
- Constraints: no dependence on full scene-graph/BVH/ray-march stack; severity mapping table must be versioned/extendable for later dashboard theming.

### R8.1 — Dashboard data contracts and view-models (headless)
- Inputs: simulation snapshots/events/alarms, replay metadata.
- Outputs:
  - mission-control view-model payloads
  - onboard view-model payloads
  - stable schema/versioning for UI clients.
- Architecture surface:
  - `visualization/telemetry_api.py`
  - `visualization/mission_control_view_model.py`
  - `visualization/onboard_view_model.py`
- Determinism policy: view-model generation is pure over committed simulation state.

### R8.2 — Geometry-anchored overlays (post-R5 dependency)
- Inputs: geometry-to-subsystem/region tags and damage/leak metadata.
- Outputs:
  - crack/fracture/leak-source overlays bound to geometry IDs
  - topology-change markers for severe-separation states.
- Architecture surface:
  - `visualization/damage_overlay_model.py`
  - geometry mapping contracts under `geometry/*`.

### R8.3 — Timeline/replay UX and control semantics (post-R6/R7.1 dependency)
- Inputs: persisted timing/provenance and pacing metadata.
- Outputs:
  - deterministic playback controls (scrub/play/pause/rate)
  - replay camera/state sync policies
  - operator incident-review event filtering.
- Architecture surface:
  - `visualization/replay_camera_sync.py`
  - timeline control contracts consumed by mission-control UI.

### R8.4/R8.5 — Full dashboard and rendering stack
- Scene graph assembly, BVH acceleration, renderer profiles, and ray-marching pipeline.
- Desktop stack realization uses SDL3/GLFW platform lifecycle + Dear ImGui shell + Vulkan renderer backend.
- Live/replay unification policy: both modes feed the same view-model and renderer contracts to preserve deterministic operator semantics.

## Python simulation <-> desktop renderer integration architecture
- **Authoritative simulation state:** Python runtime (`src/brambhand/*`) remains source of truth for physics, events, and replay persistence.
- **Live bridge path:** Python emits versioned stream frames (`state/event/topology`) over gRPC from `bridge/server_py/*`; desktop client consumes and buffers via `client_desktop/stream/*`.
- **Offline path:** Desktop client ingests replay JSONL via `client_desktop/replay/*` and uses the same visualization contracts as live mode.
- **Determinism contract:** sequence IDs + schema versions are required on bridge payloads; replay and stream ordering semantics must remain equivalent within documented tolerances.
- **Backpressure contract:** bounded ring buffers and explicit drop/degrade policies prevent UI/render stalls from blocking simulation bridge ingestion.

## Baseline UI layout (initial common-sense wireframe spec)

These are initial layout contracts to unblock backend/view-model design before final UX iteration.

### Mission-control screen (desktop)
- Top bar: run ID, sim time, wall-clock mode, pacing mode, degraded-mode badge.
- Left panel: command console + queued command status.
- Center main: 3D/trajectory viewport with layer toggles (`current`, `planned`, `optimal`, damage/leak overlays).
- Right panel: subsystem telemetry cards (propulsion, structures, comms, guidance).
- Bottom panel: event/alarm timeline with severity filtering and jump-to-time.

### Onboard screen (cockpit/minimal)
- Top strip: attitude/orbit state and critical caution/warning indicators.
- Main instruments: propulsion, power, structural integrity, cabin pressure.
- Secondary mini-view: relative-motion/docking cue and proximity metrics.
- Bottom strip: recent events and acknowledgment controls.

## Visualization architecture decisions (resolved baseline)
- Desktop UI is native and uses **SDL3/GLFW + Dear ImGui (docking baseline)**.
- 3D rendering core uses **Vulkan APIs** behind explicit renderer-module boundaries.
- Live simulation-to-UI bridge baseline is **versioned gRPC streaming**, with replay JSONL preserved as authoritative offline artifact.
- Python simulation runtime and desktop client remain process-decoupled with explicit schema-version and sequence-order contracts.
- Final interaction model for trajectory overlays (`planned` source vs `optimal` source before R11 availability) and multi-vehicle screen-density policy remain iterative UX refinements.

## Remaining design decisions to refine
- Initial latency/SLO targets are documented in `docs/PERFORMANCE_SLOS.md`; refine with benchmark data.
- Initial mode-selection thresholds are documented in `docs/PERFORMANCE_SLOS.md`; tune with production workload evidence.
- Initial persistence durability policy is documented in `docs/DISTRIBUTED_PROTOCOL.md`; finalize per deployment tier.
- Initial fallback/degraded-mode hierarchy is documented in `docs/DISTRIBUTED_PROTOCOL.md`; refine with coupling stress tests.
- FSI coupling policy needs explicit first-cut criteria for partitioned baseline operation vs monolithic escalation under instability/additional-mass sensitivity.
- Visualization stack decisions above are now fixed for baseline implementation; remaining UX refinements should preserve the same contract boundaries.

## Incremental implementation roadmap

Execution policy:
- **Core delivery lane (anti-derailment):** `R2.2 -> R2.3 -> R3 -> R3.1 -> R8.0 -> R4 -> R8.1 -> R5 -> R8.2 -> R6 -> R7 -> R7.1 -> R8.3 -> R7.2 -> R8.4 -> R8.5`.
- Do not pull post-core milestones forward unless explicitly prioritized.
- Core lane focuses on simulation correctness/coupling/replay determinism and only minimal operator-feedback surfaces needed for validation.

- **R1: 6-DOF core + mechanisms + docking contact baseline**
- **R2: Propulsion fluid network + combustion + thrust estimation + leakage**
- **R2.1: Nozzle geometry-aware thrust corrections (with STL-derived parameters)**
- **R2.2: Internal thrust-chamber flow and leak-jet dynamics coupling baseline**
- **R2.3: Reduced-order propellant slosh simulation and 6-DOF coupling baseline**
- **R3: FEM structural solver + fracture pipeline**
- **R3.1: Disjoint-topology transition simulation baseline (fracture separation + dock/undock attach/detach graph propagation)**
- **R8.0 (interleaved after R3): replay/trajectory quicklook for early visual feedback**
- **R4: FSI coupler and convergence diagnostics**
- **R8.1 (interleaved after R4): headless dashboard view-model contracts**
- **R5: STL ingestion and geometry-to-physics pipeline**
- **R8.2 (interleaved after R5): geometry-anchored overlay contracts**
- **R6: Database persistence and checkpoint/restart**
- **R7: Distributed runtime partition/sync/orchestration**
- **R7.1: Runtime pacing and time-scale control (multi-rate scheduling + cadence policy)**
- **R8.3 (interleaved after R7.1): deterministic replay/timeline UX contracts**
- **R7.2: Inter-module orchestration contracts and audit-grade replay provenance**
- **R8.4: Mission-control + onboard dashboard stack**
- **R8.5: 3D rendering core (scene graph, BVH, ray-marching, replay camera sync)**
- **R4.1: Optional CFD-coupled fluid/combustion adapter integration (deferred post-R8.5, cadence-guarded)**
- **R9: Space debris environment + compounding accretion prediction**
- **R10: Docking lifecycle + booster payload transfer logistics + interplanetary SOI handoff**
- **R11: Trajectory optimization + interplanetary mission-analysis adapters**
- **R12: Advanced mission-analysis parity extensions**
- **R13: Atmospheric launch/ascent and aero-structural behavior (deferred post-R12)**
- **R14: Advanced structural fidelity stack (deferred post-R13)**

## Current implementation status snapshot
- R1 baseline implemented in `dynamics/*` with expanded rigid-body/docking contract tests.
- R2 baseline implemented in `propulsion/*` (fluid network, combustion, thrust estimate, leakage).
- R2.1 baseline implemented in `propulsion/thrust_estimator.py` with geometry-aware area-ratio and contour-loss correction.
- R3 baseline provides linear static 2D and 3D FEM evaluation in `structures/fem/solver.py`.
- Structural solver stack is modularized under `structures/fem/*`: contracts (`contracts.py`), geometry/assembly (`geometry.py`), backend solvers (`backends.py`), selection policy (`selection.py`), and orchestration facade (`solver.py`).
- R3 now enforces 2D validity envelopes (plane-stress/plane-strain mode selection, thickness/span guardrails, out-of-plane rejection, small-strain guard).
- R3 now uses sparse assembly (`COO->CSR`) for 2D baseline stiffness with `nnz` telemetry emission.
- R3 now provides structural solver backend abstraction for reduced systems (dense direct, sparse direct, sparse iterative).
- R3 sparse-iterative path now supports configurable preconditioning (Jacobi/none) with convergence telemetry (iterations/residual).
- R3 includes matrix-free iterative reduced-system solves for large-mesh pressure scenarios.
- Matrix-free mode includes hardening safeguards: residual guardrails, optional consistency-check against sparse-direct reference, and non-finite/operator protections.
- Matrix-free path includes advanced preconditioning beyond Jacobi (node-wise block-Jacobi) and benchmark utility hooks for convergence comparison.
- Structural telemetry now includes explicit solver termination reason codes across dense/sparse/matrix-free backends.
- Matrix-free acceptance thresholds are now defined/validated for operational and analysis profiles via telemetry-based evaluators.
- Structural latency/memory benchmark utilities now provide 2D-vs-3D profile summaries (P50/P95 solve latency plus `nnz`-derived sparse storage estimates).
- Atmospheric launch/ascent and aero-structural modules are requirements-defined but intentionally deferred to R13 after current R3-R12 priorities.
- Full-fledged advanced structural fidelity modules (nonlinear/material/transient/post-buckling/fatigue-growth/adaptive-remesh/thermal-coupling) are requirements-defined and deferred to R14, following completion of R13.

## Design `->` Verification linkage
`VERIFICATION.md` defines V&V evidence per requirement group and per roadmap phase.

## Non-functional linkage note
This design primarily maps functional requirement IDs to architecture surfaces.
Non-functional requirement realization is tracked through:
- `docs/PERFORMANCE_SLOS.md` (latency/cadence/render/structural scalability targets)
- `docs/DISTRIBUTED_PROTOCOL.md` (commit, retry, durability, determinism semantics)
- `VERIFICATION.md` (NR-specific evidence plan and acceptance checks).
