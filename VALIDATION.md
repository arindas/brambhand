# VALIDATION

This document defines system-level validation criteria for `brambhand`.

Where `VERIFICATION.md` answers “did we implement it correctly?”, this file
answers “is the system fit for intended mission and operator use?”.

## 1) Validation scope

Validation covers:
- physics realism against benchmark references
- integrated mission workflows
- distributed runtime behavior and recovery
- operator usability of mission-control/onboard visualization

## 2) Validation evidence classes

1. **Analytical benchmarks**
   - closed-form orbital and rigid-body sanity cases
   - reduced-order propulsion consistency checks

2. **Reference dataset benchmarks**
   - engine/nozzle maps (including geometry-sensitive behavior)
   - structural/FEM/fracture reference cases

3. **Scenario acceptance suites**
   - docking and contact outcome envelopes
   - leak/fault propagation scenarios
   - checkpoint/restart and replay audits

4. **Operator workflow acceptance**
   - mission-control incident review
   - onboard instrumentation interpretation
   - timeline/camera synchronized replay

## 3) Validation suites by roadmap phase

## R1 (6-DOF + mechanisms + docking contact)
- Attitude/translation control sanity scenarios
- Contact/capture/rejection envelope scenarios
- Mechanism limit and rate behavior in mission sequences

## R2 / R2.1 / R2.2 / R2.3 (propulsion + nozzle geometry + chamber/leak-jet/slosh fidelity)
- Feed/combustion/thrust chain scenarios
- Nozzle shape sensitivity scenarios (throat/exit/area-ratio/contour)
- Chamber internal-flow plausibility scenarios (injector-to-throat state evolution and thrust coupling)
- Leak fault impact on delivered thrust and mission outcomes
- Leak-jet disturbance scenarios (unintended force/moment and trajectory/attitude impact)
- Slosh-induced attitude disturbance scenarios (maneuver transients and damping behavior)
- Propulsion/slosh latency-budget and fallback-trigger scenarios by profile

## R3 / R3.1 / R4 (structures + topology transitions + FSI)
- Structural loading progression scenarios
- Connected-topology damage scenarios (hole/crack-network growth without body split)
- 2D validity-envelope scenarios and 2D-vs-3D model-selection scenarios
- Structural backend comparison scenarios (dense vs sparse vs matrix-free where available)
- Structural latency/memory envelope scenarios by profile (operational vs analysis)
- Fracture initiation/propagation mission consequences
- Disjoint-topology transition scenarios (fracture separation into distinct bodies with contact/constraint updates)
- FSI coupled stability and plausibility scenarios
- FSI failure/recovery scenarios (partitioned coupling instability triggers and controlled fallback/escalation)
- End-to-end impact-fault scenario: `stray asteroid impact -> localized structural damage -> leak-path creation -> unintended leak thrust/moment contribution -> crew-cabin depressurization progression and alarms`

## R5 (geometry pipeline)
- STL-to-physics consistency scenarios (mass/inertia/contact/FEM)
- Geometry-anchored damage/leak overlay consistency

## R6 / R7 / R7.1 / R7.2 (persistence + distributed + pacing)
- Distributed barrier-commit equivalence with single-node baseline
- Retry/recovery scenarios without partial divergence
- Replay reconstruction from committed tick order/provenance
- Model-graph DAG validation scenarios (cycle rejection + deterministic mutation transactions at tick boundaries)
- Pacing-mode timeline equivalence (real-time vs accelerated vs offline)

## Mission transfer logistics suite (cross-phase)
- Dock/undock lifecycle acceptance (`approach->capture->hard-dock->detach->clearance`)
- Orbital-booster payload transfer acceptance (launch-to-UEO assembly and staged transfer burns)
- Planetary sphere-of-influence handoff acceptance for interplanetary delivery missions
- Hohmann-transfer acceptance scenarios (co-planar baseline transfers)
- Gravity-assist acceptance scenarios (swing-by deflection and downstream trajectory verification)

## R8.0 / R8.1 / R8.2 / R8.3 (interleaved early visual-feedback track)
- Replay-driven trajectory quicklook acceptance (`current` path + event markers)
- Quicklook severity readability acceptance using baseline `info|warning|critical` marker styling
- `Current` vs `planned` overlay interpretability acceptance for planning/what-if review
- Mission-control baseline layout acceptance (top bar, command panel, main viewport, telemetry rail, alarm timeline)
- Onboard baseline layout acceptance (flight strip, instrument cluster, caution/warning rail, recent-events strip)
- View-model schema compatibility acceptance across revisions (backward-compatible evolution checks)
- Geometry-region overlay continuity acceptance for crack/fracture/leak markers once R5 metadata is available
- Replay-control acceptance (play/pause/scrub/rate) with deterministic seek/timeline behavior

## R8.4 / R8.5 (dashboards + rendering)
- Native desktop shell acceptance (SDL3/GLFW lifecycle + Dear ImGui docking workflow behavior)
- Mission-control workflow acceptance (alerts/timeline/commands)
- Onboard workflow acceptance (subsystem status readability)
- Live Python-stream ingestion acceptance (gRPC baseline, bounded-buffer/backpressure policy observability)
- Replay-vs-live parity acceptance for timeline/event ordering and view-model continuity
- Rendering profile acceptance (operational vs analysis)
- Replay camera/timeline deterministic synchronization
- Geometry-change visualization acceptance for damage/deformation overlays after impact events
- Crack/fracture/leak-source visualization acceptance under evolving structural damage
- Volumetric plume/leak acceptance for nominal engine exhaust and off-nominal leak emissions

## R4.1 (optional CFD-coupled fluid/combustion adapters, post-R8.5)
- CFD-coupled plausibility scenarios against reduced-order baselines and references
- Cadence-guard/fallback scenarios (`CFD-coupled -> reduced-order`) under runtime pressure
- CFD adapter provenance/replay reconstruction scenarios

## R9 (debris and compounding accretion prediction)
- Debris population and fragment-cloud evolution scenarios
- Secondary-collision/fragment feedback scenarios for compounding risk growth
- Breakup-assumption sensitivity scenarios with casualty-risk uncertainty bands
- `Asteroid-impact -> leak/depressurization -> debris-evolution` end-to-end scenarios

## R10 / R11 / R12 (transfer logistics + trajectory optimization + advanced mission analysis)
- Dock/undock lifecycle and booster transfer mission-phase scenarios (including safety-zone/hold-point and collision-avoidance cases)
- Hohmann/Lambert transfer workflow validation scenarios
- Gravity-assist encounter/deflection validation scenarios
- Adapter-backend swap reproducibility scenarios (same mission intent across different OSS/in-house backends)
- Seed-sensitivity and convergence-basin scenarios (Lambert-seeded vs alternate initializations)
- Campaign/window-sweep trade-study validation with provenance checks
- Orbit-determination/covariance/dispersion validation scenarios (including covariance-consistency checks)
- Operational-constraint and finite-burn realism validation scenarios
- Mission-analysis product acceptance and interactive-session reproducibility scenarios

## R13 (atmospheric launch/ascent + aero-structural behavior)
- Atmosphere-profile and aerodynamic-load plausibility scenarios across ascent altitude bands
- Launch event-sequence acceptance scenarios (liftoff, max-q, staging, MECO, atmospheric exit)
- Atmospheric-exit and apogee prediction acceptance scenarios with propagated-truth tolerance checks
- Ascent guidance/attitude profile-following scenarios with disturbance/drag sensitivity checks
- Buckling/fatigue risk progression scenarios and fracture-seeding alarm/event propagation checks

## R14 (advanced structural fidelity stack)
- Nonlinear structural response validation scenarios against trusted references (large-deformation baseline)
- Material nonlinearity/plastic-response validation scenarios with profile-specific tolerances
- Transient structural dynamics validation scenarios (modal/direct integration) and replay consistency checks
- Buckling and post-buckling progression validation scenarios for critical load cases
- Fatigue accumulation and crack-growth coupling validation scenarios across mission-phase duty cycles
- Thermo-structural coupling validation scenarios (temperature-dependent material properties and thermal-load influence)
- Adaptive remesh/refinement provenance and acceptance scenarios under deterministic replay constraints

## Baseline continuity suite (cross-phase)
- Orbital baseline continuity checks against earlier deterministic scenarios
- Communication visibility/occlusion continuity checks
- Delayed command/telemetry workflow continuity checks
- Scenario validate/run/replay CLI continuity checks

## 4) Benchmark and fixture registry policy

Validation inputs should be versioned and traceable:
- STL fixture registry: `assets/stl/metadata/fixtures.json`
- Scenario references: versioned under scenario assets
- Benchmark metadata: versioned dataset descriptors with provenance

## 5) Acceptance criteria format

Each validation scenario must define:
- objective
- inputs/configuration versions
- execution profile/mode
- pass/fail quantitative criteria
- generated artifacts (logs, replay, snapshots, renders)

## 6) Requirement linkage (validation scope)

Validation suites in this document cover the following requirement groups:
- FR-001..FR-005, FR-067..FR-071: dynamics/control and baseline mission continuity
- FR-006..FR-010, FR-031, FR-132..FR-133, FR-135..FR-137: propulsion/combustion/nozzle behavior, chamber-internal flow, leak-jet/slosh dynamics, FSI-linked boundary exchange, and optional CFD-coupled workflows
- FR-139..FR-145: desktop visualization stack, Vulkan rendering architecture, Dear ImGui UI integration, Python live-stream bridge contracts, and replay/live parity behaviors
- FR-011..FR-015, FR-072..FR-073, FR-074..FR-080, FR-081..FR-083, FR-134: structures/fracture/FSI, severe topology-change events, assembly-topology transitions, and structural scalability paths (including matrix-free acceptance)
- FR-016..FR-018, FR-032..FR-037: geometry ingestion and geometry-to-physics consistency
- FR-019..FR-021, FR-064..FR-066: persistence/checkpoint/replay auditability
- FR-022..FR-024, FR-059..FR-063: distributed synchronization, barrier commit, and recovery semantics
- FR-025..FR-028, FR-038..FR-043: dashboards and rendering validation
- FR-044..FR-048, FR-049..FR-058, FR-138: pacing, scheduler ordering, model-graph DAG orchestration, and inter-module contracts
- FR-084..FR-085: debris population, fragment generation, and compounding accretion prediction use cases
- FR-086..FR-090: dock/undock lifecycle, booster-assisted payload transfer, planetary handoff mission phases, Hohmann-transfer, and gravity-assist workflows
- FR-091..FR-102: trajectory optimization + interplanetary mission-analysis adapter workflows and campaign orchestration
- FR-103..FR-114: OD/uncertainty/dispersion/ops-constraint/mission-product/interactive-analysis parity workflows
- FR-115..FR-118: architecture decoupling integrity and shared frame/time service consistency workflows
- FR-119..FR-124: atmospheric launch/ascent, aerodynamic loading, ascent-event sequencing, apogee prediction, and buckling/fatigue-to-fracture workflows
- FR-125..FR-131: advanced structural fidelity workflows (nonlinear/material/transient/buckling/fatigue-growth/thermal coupling/adaptive remeshing)
- FR-029..FR-030: diagnostics and reproducibility metadata channels

Non-functional validation intent in this document aligns with NR-001..NR-064, with specific SLO-aligned targets governed by `docs/PERFORMANCE_SLOS.md`.

## 7) Current validation-progress snapshot (2026-04-02)

- R1 validation-prep evidence available via deterministic docking/rigid-body contract tests.
- R2 validation-prep evidence available for propulsion chain and leakage scenarios.
- R2.1 validation-prep evidence available for nozzle geometry sensitivity (area ratio and contour loss).
- R3 validation-prep evidence available for linear-static 2D FEM baseline contracts.
- Matrix-free acceptance-threshold evaluation evidence is available for operational/analysis profiles (including strict-threshold failure-path checks).
- Structural latency/memory benchmark-prep evidence is available for 2D-vs-3D profile comparisons (P50/P95 solve timing and `nnz`-based sparse storage estimates).
- Full benchmark-grade validation suites remain milestone-gated and are tracked in `TODO.md`.
- R8.0..R8.3 suites are now defined for incremental operator feedback prior to full R8.4/R8.5 dashboard+rendering delivery.

## 8) Governance

- Validation criteria updates must reference requirements IDs.
- Validation results must be reproducible from persisted metadata.
- Failed validation scenarios block corresponding milestone gate.