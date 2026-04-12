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
  - added sparse assembly path (`COO->CSR`) and structural `nnz` telemetry in solve results
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
- C++ test/CI baseline update:
  - integrated GoogleTest in CMake build for native client-side tests (`src/test/*`, `gtest_discover_tests`)
  - added initial runtime-frame unit tests on C++ side (`brambhand_client_tests`)
  - updated CI to build and run C++ tests via CMake/CTest alongside Python quality gates
  - updated repository conventions and docs for nested `python/brambhand` and `c/brambhand` layouts with standard C++ include/src/lib/src/bin organization
- Visualization architecture decision update:
  - fixed desktop visualization stack to SDL3/GLFW platform layer + Dear ImGui docking UI + Vulkan renderer backend
  - fixed Python integration baseline to process-decoupled live gRPC stream bridge plus replay JSONL offline path
  - synchronized `REQUIREMENTS.md`, `DESIGN.md`, `TODO.md`, `VERIFICATION.md`, `VALIDATION.md`, and `docs/PERFORMANCE_SLOS.md` with concrete desktop-renderer/bridge contracts and V&V expectations
- R8.0 quicklook telemetry contract baseline:
  - added `visualization/quicklook_contracts.py` with versioned minimal trajectory/event extraction contract (`QuicklookTelemetryContract`)
  - added replay-to-quicklook extraction helper (`extract_quicklook_telemetry`) with deterministic ordering
  - added `visualization/quicklook_pipeline.py` headless trajectory quicklook pipeline (2D/3D) from replay JSONL (`build_headless_quicklook_output`, `load_headless_quicklook_output`)
  - added quicklook contract/pipeline tests for extraction behavior, JSONL load path, and schema-version validation
- R8.0 quicklook event-marker output baseline:
  - extended headless quicklook outputs with deterministic event markers (`QuicklookEventMarker`) and optional trajectory anchors
  - event markers now map each replay event to latest known trajectory position for timeline/trajectory overlay use
  - expanded quicklook tests to cover marker extraction/anchoring behavior and JSONL load-path marker presence
- R8.0 quicklook severity-contract baseline:
  - added versioned severity contract (`QUICKLOOK_SEVERITY_SCHEMA_VERSION`) and deterministic event-kind mapping table (`QUICKLOOK_EVENT_SEVERITY_MAP`)
  - extended `QuicklookEvent` with `severity` (`info|warning|critical`) using deterministic mapping and `info` fallback for unknown event kinds
  - added severity mapping helper (`event_kind_to_severity`) and schema-validation tests
- R8.0 quicklook severity styling baseline:
  - added style schema version (`QUICKLOOK_STYLE_SCHEMA_VERSION`) and deterministic 3-color severity palette (`QUICKLOOK_SEVERITY_COLOR_MAP`)
  - extended `QuicklookEventMarker` with `color_hex` resolved via `severity_to_color_hex(...)`
  - added style mapping tests and pipeline assertions for style-schema/versioned marker coloring
- R8.0 current-vs-planned trajectory overlay baseline:
  - extended quicklook telemetry extraction with optional `planned_trajectory` samples from replay payload key `planned_position_m`
  - added deterministic trace-alignment utilities in `visualization/trajectory_overlay.py` (`build_current_planned_overlay`)
  - extended headless quicklook output with planned 2D/3D traces and aligned current-vs-planned overlay samples
  - added tests for planned-trace extraction, overlay alignment, and missing-planned fallback behavior
- R8.0 3D trajectory render contract baseline:
  - added `visualization/trajectory_render_contracts.py` with versioned renderer-facing contract (`TrajectoryRenderContract3D`)
  - exposes deterministic 3D current/planned polyline curves plus moving object markers sampled along curves at requested simulation time
  - added renderer contract tests for curve generation, marker sampling semantics, and schema-version validation
- R8.0 deterministic quicklook snapshot coverage:
  - added golden snapshot fixtures for quicklook telemetry extraction ordering and headless output rendering (`tests/snapshots/quicklook_telemetry_snapshot.json`, `tests/snapshots/quicklook_output_snapshot.json`)
  - added regression tests in `tests/test_quicklook_contracts.py` to enforce deterministic quicklook extraction/ordering against intentionally unordered replay inputs
- R8.0 compact trajectory-widget contract baseline:
  - added `visualization/trajectory_widget_contracts.py` with versioned compact infographic contract (`TrajectoryWidgetContract`) for curve layers + object-icon markers
  - implemented `build_trajectory_widget_contract(...)` to derive widget payloads directly from shared `TrajectoryRenderContract3D` inputs (no duplicate extraction path)
  - added tests in `tests/test_trajectory_widget_contracts.py` for curve/icon mapping semantics and schema-version validation
- Traceability update for dual trajectory presentation modes:
  - updated `REQUIREMENTS.md` with explicit compact-infographic + rich-3D trajectory-view requirements and shared-contract parity constraints (`FR-146..FR-148`, `NR-065`)
  - updated `DESIGN.md`, `TODO.md`, `VERIFICATION.md`, and `VALIDATION.md` to plan/verify/validate both trajectory presentation paths on shared semantics
- R3.1 assembly-topology state graph baseline:
  - added `mission/assembly_topology.py` with deterministic attachment-graph contracts (`AssemblyTopologyState`, `AttachmentInterface`) and revisioned attach/detach transitions
  - added deterministic connected-component extraction and body-interface query helpers for disjoint-body connectivity state
  - added fracture-driven split transition baseline with deterministic child-body IDs/provenance (`apply_fracture_split_transition`, `FractureSplitProvenance`) and deterministic interface rewiring policy
  - added baseline dock/undock topology transitions with constraint/contact handoff provenance (`apply_docking_attach_transition`, `apply_docking_detach_transition`, `DockingTransitionProvenance`)
  - defined versioned topology-transition payload contract for FSI/leak-boundary consumers (`TOPOLOGY_TRANSITION_PAYLOAD_SCHEMA_VERSION`, `TopologyTransitionPayload`) and mapping helper (`build_topology_transition_payload`)
  - added graph-level topology effect derivation (`derive_topology_propagation_effects`, `TopologyPropagationEffects`) to target downstream mass-property, constraint/contact-manifold, and control-authority updates
  - added contract tests covering attach/detach transitions, deterministic canonical ordering, connectivity decomposition, invalid-graph rejection, split-transition provenance behavior, and replay reconstruction/determinism checks with downstream propagation-continuity assertions
- R4 two-way FSI coupler baseline:
  - added `coupling/fsi_coupler.py` with deterministic partitioned two-way coupling iterations (`couple_fsi_two_way`)
  - added convergence controls/telemetry contracts (`FSICouplingParams`, `FSICouplingIterationTelemetry`, `FSICouplingResult`) with residual tracking and termination reasons
  - added baseline interface displacement feedback contract (`InterfaceDisplacement`) and provider protocols for fluid/structural iteration wiring
  - added tests in `tests/test_fsi_coupler.py` for convergence behavior, max-iteration failure behavior, deterministic interface ordering, and parameter validation guards
- R3 fracture/damage baseline:
  - added `structures/fracture.py` with deterministic fracture-initiation thresholds (`FractureInitiationParams`) and per-element damage-state evaluation
  - added FEM-linked fracture evaluation helpers for 2D/3D solve outputs
  - added baseline damage propagation modifiers for mass/stiffness/contact behavior plus leak-path indicator contract (`propagate_damage_effects`)
  - added connected-topology damage payload contract for leak/FSI consumers (`CONNECTED_TOPOLOGY_DAMAGE_PAYLOAD_SCHEMA_VERSION`, `ConnectedTopologyDamagePayload`, `build_connected_topology_damage_payload`) covering holes/crack-network evolution without disjoint split
  - exported fracture contracts via `brambhand.structures`
  - added structural contract tests for damage progression, FEM-linked fracture evaluation, propagated behavior modifiers, structural-failure leak-path scenario coverage, and an asteroid-impact connected-topology fault-chain scenario (damage/hole progression -> depressurization -> alarm propagation)
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
- Coverage hardening updates:
  - expanded CLI command-path tests to cover validate/run/replay main flows and invalid run-argument guards
  - expanded propulsion contract/error-path tests for validation guards and zero-flow/no-leak edge paths
  - expanded constellation validation tests for empty/duplicate-name/duplicate-slot rejection
- Visualization planning/design expansion:
  - added explicit numbered visualization milestones `R8.0..R8.5` in `DESIGN.md` with authoritative interleave order across core milestones
  - documented baseline mission-control/onboard layout contracts and explicit visualization unknown/decision log items
  - extended `VERIFICATION.md` with `R8.0..R8.5` evidence gates (quicklook determinism, schema contracts, replay-control equivalence, full dashboard/render gates)
  - extended `VALIDATION.md` with `R8.0..R8.5` acceptance suites (trajectory overlays, baseline layout usability, replay-control behavior, full rendering acceptance)
  - expanded `TODO.md` with actionable `R8.0..R8.5` work items and explicit interleave placement
- Simulation-fidelity planning expansion for requested domains:
  - added new requirements `FR-132..FR-134` and `NR-057` for chamber-internal flow simulation, leak-jet momentum/thermal dynamics with 6-DOF coupling, and explicit assembly-topology transition simulation across fracture and dock/undock events
  - added matching design surfaces (`propulsion/chamber_flow.py`, `propulsion/leak_jet_dynamics.py`, `mission/assembly_topology.py`) and traceability mapping
  - added roadmap/TODO milestones `R2.2` and `R3.1`, plus R10 topology-integration task
  - extended V&V/validation plans with chamber-flow, leak-jet disturbance, and topology-transition evidence scenarios
- Roadmap consistency hardening:
  - standardized anti-derailment execution policy across `TODO.md`, `DESIGN.md`, and `README.md`
  - made the core delivery lane explicit and locked post-core (`R9+`) milestones behind completion of `R2.2..R8.5` unless explicitly reprioritized
  - relabeled advanced/niche mission-analysis phases as post-core to reduce planning drift
- R8.0 scope refinement:
  - un-deferred minimal severity styling for quicklook markers using an extensible deterministic baseline contract (`info|warning|critical` + 3-color mapping)
- R2.2 chamber-flow baseline:
  - added reduced-order chamber-flow model under `fluid/reduced/chamber_flow.py`
  - added chamber diagnostics (`pressure`, `temperature`, `mixing_quality`, stoichiometric error, chamber O/F proxy)
  - added deterministic coupling contract `ChamberThrustCouplingParams` and `estimate_nozzle_thrust_from_chamber_flow(...)` in `propulsion/thrust_estimator.py`
  - coupled chamber-flow state into nozzle thrust path (including geometry-correction compatibility)
  - added reduced-order leak-jet dynamics model under `fluid/reduced/leak_jet_dynamics.py` (mass-flow, exit velocity, thermal proxy, reaction force/torque)
  - added `propulsion/leak_jet_coupling.py` to propagate leak-jet reaction wrench into 6-DOF body-frame dynamics
  - added versioned leak-jet boundary payload contract in `fluid/contracts.py` and mapping helper for FSI exchange integration
  - added analytical consistency tests for leak-jet force decomposition and leak mass-flow vs compartment mass-loss envelope
  - added reduced-order propulsion latency benchmark helpers (`propulsion/performance.py`) with cadence-guard mode/fallback trigger accounting
  - added benchmark tests for latency summaries, cadence-guard behavior, and validation paths
  - exported chamber/leak-jet contracts via `brambhand.propulsion`
  - added propulsion contract tests for chamber-flow dynamics, leak-jet dynamics behavior, off-stoich quality degradation, thrust-coupling determinism, and input validation
- R2.3 slosh model baseline:
  - implemented deterministic lumped spring-mass slosh state update in `fluid/reduced/slosh_model.py`
  - added `SloshModelParams`, `SloshState`, `SloshStepResult`, and `step_slosh_state(...)`
  - added geometry-aware slosh parameter hooks (`SloshGeometryDescriptor`, `SloshFallbackParams`, `derive_slosh_model_params(...)`) with fallback behavior for non-STL configuration paths
  - defined versioned slosh boundary payload contract in `fluid/contracts.py` (`SLOSH_BOUNDARY_PAYLOAD_SCHEMA_VERSION`, `SloshBoundaryPayload`) with backend-neutral mapping support
  - added `propulsion/slosh_coupling.py` helper to build FSI/coupling slosh payloads from reduced-order slosh loads
  - added `propulsion/slosh_6dof_coupling.py` to propagate slosh force/torque plus effective CoM offsets into rigid-body 6-DOF updates
  - extended reduced-order performance helpers with slosh latency/cadence benchmarks and explicit degraded-mode control mapping (`benchmark_reduced_order_slosh_latency`, `apply_slosh_degraded_mode`)
  - exported slosh contracts and helpers through `fluid/reduced/__init__.py`, `fluid/__init__.py`, and `brambhand.propulsion`
  - added propulsion contract tests for slosh restoring-response behavior, attitude disturbance/coupling response, energy sanity envelope checks, geometry-hook behavior, payload schema/version checks, and slosh latency/degraded-mode controls
- Slosh + CFD planning extension with performance safeguards:
  - added requirements `FR-135` (propellant slosh simulation), `FR-136` (optional CFD-coupled adapter contracts), and `FR-137` (FSI integration of topology/leak/slosh boundary exchanges) plus `NR-058` (latency/cadence/fallback safeguards)
  - clarified backend-neutral FSI contract policy: reduced-order and CFD fluid providers share the same FSI-facing boundary interface; R4.1 extends providers only and does not duplicate coupling-controller logic
  - refactored fluid architecture toward that contract model:
    - introduced `fluid/` namespace (`contracts.py`, `reduced/*`, `cfd/contracts.py`, `cfd/adapters/*` placeholders)
    - removed propulsion shim modules and migrated canonical imports to `fluid/reduced/*`
  - added design roadmap milestones `R2.3` (reduced-order slosh, core lane) and `R4.1` (optional CFD adapters, post-R8.5)
  - updated `TODO.md` interleaving with `R2.3` before `R3` and `R4.1` between `R8.5` and `R9`
  - clarified topology semantics across requirements/design/TODO/V&V: connected-topology damage evolution (holes/crack-network without split) is owned under structures/R3; disjoint-body connectivity transitions are owned under assembly-topology/R3.1
  - added explicit model-graph DAG planning (`FR-138`, `NR-059`) with deterministic topological scheduling and mutation transactions at tick boundaries
  - updated design runtime/concurrency sections with box-drawing diagrams and explicit note that text definitions are normative while diagrams are supplemental
  - extended `VERIFICATION.md`/`VALIDATION.md` for slosh and CFD-coupled evidence plans
  - updated `docs/PERFORMANCE_SLOS.md` with propulsion flow/slosh SLOs and CFD fallback observability metrics

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
