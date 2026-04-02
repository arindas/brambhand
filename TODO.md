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
- [ ] Add unit/integration tests for full rigid-body and docking contact behavior

### R2 — Propulsion fluids, combustion, and thrust estimation
- [x] Implement reduced-order fluid network subsystem (tank/line/valve baseline)
- [x] Implement combustion chamber dynamic model (ideal-gas baseline)
- [x] Implement thrust estimator from chamber/flow state (momentum + pressure terms)
- [x] Implement leakage model for propulsion circuits/chassis compartments
- [x] Add baseline analytical validation tests for R2 contracts
- [ ] Add nozzle geometry-aware thrust correction model (area ratio/contour losses)
- [ ] Add tests for nozzle shape sensitivity in thrust predictions

### R3 — Structural FEM and fracture
- [ ] Implement FEM structural evaluation baseline for chassis components
- [ ] Implement fracture initiation/propagation baseline model
- [ ] Implement damage state propagation to mass/stiffness/contact behavior
- [ ] Add structural failure scenario tests (including leak path creation)

### R4 — Fluid-structure interaction coupling
- [ ] Implement two-way FSI coupler with convergence residuals
- [ ] Implement coupling controller (iteration budget, thresholds, fallback)
- [ ] Add convergence diagnostics and residual telemetry channels
- [ ] Add FSI benchmark tests for coupled stability

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
- [ ] Persist pacing/timeline metadata in run/replay artifacts
- [ ] Add timeline equivalence tests across pacing modes

### R7.2 — Inter-module orchestration contracts
- [ ] Define versioned inter-module schema contracts for cross-domain exchange
- [ ] Implement unit/frame validation at module boundaries
- [ ] Implement deterministic scheduler-order metadata and enforcement
- [ ] Implement explicit fault-propagation event contracts across domains
- [ ] Implement distributed logical tick/barrier compatibility checks
- [ ] Add integration tests for causal ordering and audit-grade replay reconstruction

### R8 — Visualization and dashboards
- [ ] Implement mission-control dashboard backend/view models
- [ ] Implement onboard spacecraft dashboard backend/view models
- [ ] Implement 3D state/damage/leak overlays and event timeline integration
- [ ] Add operator workflow acceptance tests (latency + usability gates)

### R8.1 — 3D rendering core
- [ ] Implement render scene graph assembly from simulation state
- [ ] Implement BVH acceleration structures for dynamic geometry
- [ ] Implement ray-marching-capable volumetric rendering pipeline (plume/field views)
- [ ] Implement rendering profiles (operational fast mode vs analysis mode)
- [ ] Implement deterministic replay camera/timeline synchronization
- [ ] Add rendering V&V tests (frame-time budgets, temporal stability, BVH update costs)

## Design, verification, and validation documentation gaps (reviewed)
- [x] Finalize initial numeric latency/SLO targets per deployment/render profile (`docs/PERFORMANCE_SLOS.md`)
- [x] Document automatic scaling mode-selection thresholds (single-node vs partitioned vs hybrid)
- [x] Document persistence durability policy per artifact class (events/telemetry/checkpoints)
- [x] Document coupling fallback/degraded-mode hierarchy under load
- [x] Add dedicated `VALIDATION.md` for benchmark datasets, acceptance scenarios, and operator workflow criteria
- [x] Add distributed execution protocol spec (`docs/DISTRIBUTED_PROTOCOL.md`) for tick/barrier/commit semantics
- [x] Add performance and pacing SLO doc (`docs/PERFORMANCE_SLOS.md`) tied to NR-018..NR-024, NR-029..NR-031

## Documentation and traceability
- [ ] Keep requirement-to-design matrix current as architecture evolves
- [ ] Keep V&V traceability matrix current with new evidence
- [ ] Keep VALIDATION scenario/benchmark registry current with new acceptance evidence
- [ ] Keep inline API docs complete for all new public modules
- [ ] Maintain release notes for each semver milestone
