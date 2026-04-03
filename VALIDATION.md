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

## R2 / R2.1 (propulsion + nozzle geometry)
- Feed/combustion/thrust chain scenarios
- Nozzle shape sensitivity scenarios (throat/exit/area-ratio/contour)
- Leak fault impact on delivered thrust and mission outcomes

## R3 / R4 (structures + fracture + FSI)
- Structural loading progression scenarios
- 2D validity-envelope scenarios and 2D-vs-3D model-selection scenarios
- Structural backend comparison scenarios (dense vs sparse vs matrix-free where available)
- Structural latency/memory envelope scenarios by profile (operational vs analysis)
- Fracture initiation/propagation mission consequences
- FSI coupled stability and plausibility scenarios
- End-to-end impact-fault scenario: stray asteroid impact -> localized structural damage -> leak-path creation -> unintended leak thrust/moment contribution -> crew-cabin depressurization progression and alarms

## R5 (geometry pipeline)
- STL-to-physics consistency scenarios (mass/inertia/contact/FEM)
- Geometry-anchored damage/leak overlay consistency

## R6 / R7 / R7.1 / R7.2 (persistence + distributed + pacing)
- Distributed barrier-commit equivalence with single-node baseline
- Retry/recovery scenarios without partial divergence
- Replay reconstruction from committed tick order/provenance
- Pacing-mode timeline equivalence (real-time vs accelerated vs offline)

## Mission transfer logistics suite (cross-phase)
- Dock/undock lifecycle acceptance (approach->capture->hard-dock->detach->clearance)
- Orbital-booster payload transfer acceptance (launch-to-UEO assembly and staged transfer burns)
- Planetary sphere-of-influence handoff acceptance for interplanetary delivery missions
- Hohmann-transfer acceptance scenarios (co-planar baseline transfers)
- Gravity-assist acceptance scenarios (swing-by deflection and downstream trajectory verification)

## R8 / R8.1 (dashboards + rendering)
- Mission-control workflow acceptance (alerts/timeline/commands)
- Onboard workflow acceptance (subsystem status readability)
- Rendering profile acceptance (operational vs analysis)
- Replay camera/timeline deterministic synchronization
- Geometry-change visualization acceptance for damage/deformation overlays after impact events
- Crack/fracture/leak-source visualization acceptance under evolving structural damage
- Volumetric plume/leak acceptance for nominal engine exhaust and off-nominal leak emissions

## R9 (debris and compounding accretion prediction)
- Debris population and fragment-cloud evolution scenarios
- Secondary-collision/fragment feedback scenarios for compounding risk growth
- Asteroid-impact -> leak/depressurization -> debris-evolution end-to-end scenarios

## R10 / R11 / R12 (transfer logistics + trajectory optimization + advanced mission analysis)
- Dock/undock lifecycle and booster transfer mission-phase scenarios
- Hohmann/Lambert transfer workflow validation scenarios
- Gravity-assist encounter/deflection validation scenarios
- Adapter-backend swap reproducibility scenarios (same mission intent across different OSS/in-house backends)
- Campaign/window-sweep trade-study validation with provenance checks
- Orbit-determination/covariance/dispersion validation scenarios
- Operational-constraint and finite-burn realism validation scenarios
- Mission-analysis product acceptance and interactive-session reproducibility scenarios

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
- FR-006..FR-010, FR-031: propulsion/combustion/nozzle behavior
- FR-011..FR-015, FR-072..FR-073, FR-074..FR-080, FR-081..FR-083: structures/fracture/FSI, severe topology-change events, and structural scalability paths (including matrix-free acceptance)
- FR-016..FR-018, FR-032..FR-037: geometry ingestion and geometry-to-physics consistency
- FR-019..FR-021, FR-064..FR-066: persistence/checkpoint/replay auditability
- FR-022..FR-024, FR-059..FR-063: distributed synchronization, barrier commit, and recovery semantics
- FR-025..FR-028, FR-038..FR-043: dashboards and rendering validation
- FR-044..FR-048, FR-049..FR-058: pacing, scheduler ordering, and inter-module orchestration contracts
- FR-084..FR-085: debris population, fragment generation, and compounding accretion prediction use cases
- FR-086..FR-090: dock/undock lifecycle, booster-assisted payload transfer, planetary handoff mission phases, Hohmann-transfer, and gravity-assist workflows
- FR-091..FR-102: trajectory optimization + interplanetary mission-analysis adapter workflows and campaign orchestration
- FR-103..FR-114: OD/uncertainty/dispersion/ops-constraint/mission-product/interactive-analysis parity workflows
- FR-115..FR-117: architecture decoupling integrity and shared frame/time service consistency workflows
- FR-029..FR-030: diagnostics and reproducibility metadata channels

Non-functional validation intent in this document aligns with NR-001..NR-048, with specific SLO-aligned targets governed by `docs/PERFORMANCE_SLOS.md`.

## 7) Current validation-progress snapshot (2026-04-02)

- R1 validation-prep evidence available via deterministic docking/rigid-body contract tests.
- R2 validation-prep evidence available for propulsion chain and leakage scenarios.
- R2.1 validation-prep evidence available for nozzle geometry sensitivity (area ratio and contour loss).
- R3 validation-prep evidence available for linear-static 2D FEM baseline contracts.
- Matrix-free acceptance-threshold evaluation evidence is available for operational/analysis profiles (including strict-threshold failure-path checks).
- Sparse/3D performance validation remains planned.
- Full benchmark-grade validation suites remain milestone-gated and are tracked in `TODO.md`.

## 8) Governance

- Validation criteria updates must reference requirements IDs.
- Validation results must be reproducible from persisted metadata.
- Failed validation scenarios block corresponding milestone gate.