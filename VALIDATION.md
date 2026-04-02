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
- Fracture initiation/propagation mission consequences
- FSI coupled stability and plausibility scenarios

## R5 (geometry pipeline)
- STL-to-physics consistency scenarios (mass/inertia/contact/FEM)
- Geometry-anchored damage/leak overlay consistency

## R6 / R7 / R7.1 / R7.2 (persistence + distributed + pacing)
- Distributed barrier-commit equivalence with single-node baseline
- Retry/recovery scenarios without partial divergence
- Replay reconstruction from committed tick order/provenance
- Pacing-mode timeline equivalence (real-time vs accelerated vs offline)

## R8 / R8.1 (dashboards + rendering)
- Mission-control workflow acceptance (alerts/timeline/commands)
- Onboard workflow acceptance (subsystem status readability)
- Rendering profile acceptance (operational vs analysis)
- Replay camera/timeline deterministic synchronization

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

## 6) Governance

- Validation criteria updates must reference requirements IDs.
- Validation results must be reproducible from persisted metadata.
- Failed validation scenarios block corresponding milestone gate.