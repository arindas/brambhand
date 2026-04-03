# Research notes

Date: 2026-04-03

Scope:
- quick knowledge-base scan for already implemented areas and future roadmap areas
- compare findings against `REQUIREMENTS.md`, `DESIGN.md`, `TODO.md`, `VERIFICATION.md`, `VALIDATION.md`

Knowledge-base source:
- host: `ssh ${KB_SSH_USER}@${KB_SSH_HOST}`
- root: `${KB_ROOT_DIR}`
- session values used for this run: `arindas@192.168.1.2`, `/home/arindas/ebooks`

Method:
- filename discovery via `find` + `grep`
- scoped extraction via `pdftotext` + keyword grep
- no full-document extraction

## A) Implemented items: references and notes

### A1) Structural FEM (R3)
Reference:
- `aerospace/the-finite-element-method-in-engineering.pdf`

Observed signals from extracted text:
- explicit 2D/3D element modeling discussion (triangles/quads vs tetrahedra/hexahedra)
- explicit convergence requirements and mesh-refinement convergence behavior
- explicit plane-stress / plane-strain treatment

Project comparison:
- aligns with current R3 implementation:
  - 2D validity envelope checks
  - 3D tetrahedral baseline
  - convergence/termination telemetry in solver output
- supports current TODO direction for backend-equivalence and latency/memory profiling

### A2) Propulsion/nozzle correction (R2.1)
Reference:
- `aerospace/series/cambridge-aeospace-series/rocket-propulsion.pdf`

Observed signals:
- nozzle performance framing ties thrust and specific impulse to both propellant energetics and nozzle design
- design-space discussion includes chamber pressure and nozzle expansion ratio

Project comparison:
- aligns with implemented reduced-order correction model (`NozzleGeometryCorrection`)
- confirms value of keeping nozzle geometry factors explicit and versioned for future STL-derived pipeline work (R5)

### A3) Rendezvous and docking baseline (R1/R10 precursor)
Reference:
- `aerospace/papers/guidance-and-control-for-spacecraft-rendezvous-and-docking.pdf`

Observed signals:
- final approach is precision-critical
- docking framed as controlled contact with constraints on relative position/velocity/attitude/rates
- LOS-based guidance appears in close-approach discussion

Project comparison:
- aligns with current rendezvous metrics + docking screening contracts
- supports upcoming explicit dock/undock lifecycle state-machine work in R10

## B) Future items: references and notes

### B1) FSI coupling (R4)
Reference:
- `aerospace/simulation/computational-fluid-dynamics-and-fluid-structure-interaction/computational-fluid-structure-interaction.pdf`

Observed signals:
- strong distinction between loosely coupled (staggered/partitioned) and strongly coupled (monolithic) approaches
- documented convergence/stability issues for partitioned coupling in some regimes (including added-mass sensitivity)
- repeated emphasis on coupling stability controls and convergence acceleration

Project comparison:
- strong support for planned R4 tasks:
  - two-way coupler
  - coupling controller with thresholds/fallback
  - residual telemetry channels

### B2) Trajectory optimization adapters (R11)
Reference:
- `aerospace/series/cambridge-aeospace-series/spacecraft-trajectory-optimization.pdf`

Observed signals:
- practical stack includes Lambert initialization + direct methods (collocation/transcription/NLP)
- Hohmann remains useful analytic baseline and validation anchor
- ephemeris and constraint handling are central for realistic workflows

Project comparison:
- aligns with R11 planned adapter architecture (Lambert/Hohmann/gravity-assist, campaign sweeps, backend abstraction)
- supports requirement for backend-neutral contracts and reproducible provenance

### B3) Debris and re-entry risk (R9)
Reference:
- `aerospace/simulation/papers/next-generation-reentry-aerothermodynamic-modelling-of-space-debris.pdf`

Observed signals:
- operational practice already uses breakup/fragment modeling + casualty-risk workflow
- tool ecosystems emphasize fragment-level modeling and risk-area outputs
- computational cost is a practical constraint in high-fidelity aerothermodynamic analysis

Project comparison:
- aligns with R9 decomposition (fragment generation, propagation, compounding risk)
- supports prioritizing staged fidelity + explicit uncertainty/assumption metadata

### B4) Orbit-determination and covariance workflows (R12)
Reference:
- `aerospace/series/american-institute-of-aeronautics-and-astronautics/kalman-filtering-a-practical-approach.pdf`

Observed signals:
- direct connection between batch LS and recursive/Kalman formulations
- process-noise and initial covariance choices are central to estimator behavior
- covariance reporting is not optional; it is core estimator output

Project comparison:
- aligns with FR-103..FR-104 roadmap and planned OD abstraction requirements
- supports adding explicit covariance/provenance fields in future mission-analysis outputs

## C) Cross-doc comparison summary

Against `REQUIREMENTS.md`:
- no contradictions found
- external references reinforce FR-072..FR-080, FR-084..FR-085, FR-091..FR-104 scope

Against `DESIGN.md`:
- no architecture conflicts found
- FSI notes reinforce need for explicit partitioned-vs-monolithic strategy and fallback policy in coupler design docs

Against `TODO.md`:
- active R3 tasks are consistent with FEM references
- R4/R9/R11/R12 planned tasks are well aligned with reference material

Against `VERIFICATION.md`:
- current evidence plan is directionally correct
- for future R4 and R11/R12 gates, benchmark definitions should explicitly include:
  - coupling-stability failure/recovery paths (FSI)
  - initialization sensitivity (Lambert seed vs direct solve)
  - estimator covariance consistency checks (OD)

Against `VALIDATION.md`:
- scenario families align with reference themes
- future debris validation should include explicit breakup-assumption sensitivity bands

## D) Suggested follow-up actions (doc-level)

1. Add one short R4 design note clarifying initial coupling policy:
   - start partitioned with acceleration and residual gates
   - define criteria for when monolithic path is required

2. In R11/R12 validation planning, add one benchmark category for:
   - seed sensitivity and convergence basin checks

3. In R9 validation planning, add one benchmark category for:
   - breakup model sensitivity and casualty-risk uncertainty bands
