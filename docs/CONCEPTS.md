# Concepts

## 1) Simulation state model

A simulation state is primarily a collection of `PhysicalBody` values:

- `name`
- `mass`
- inertial translational state (`position`, `velocity`)

These are advanced in fixed timesteps by the physics integrator.

## 2) Deterministic fixed-step propagation

`brambhand` uses fixed-step integration (`VelocityVerletIntegrator`) for reproducible runs.
Given identical:

- initial state
- timestep (`dt`)
- step count
- command/event stream

you should obtain deterministic event ordering and equivalent snapshots.

## 3) Gravity and units

- Gravity model: Newtonian N-body (`NBodyGravityModel`)
- Gravitational constant from `scipy.constants.G`
- Units are SI by convention (meters, seconds, kilograms)

## 4) Eventing and snapshots

- `EventBus` stores ordered events
- `StateSnapshot` captures simulation time + body state + events
- Replay logs are persisted to JSONL via `ReplayLog`

## 5) Guidance and trajectory

Guidance APIs include:

- Cartesian `<->` Keplerian conversions
- forward prediction using current integrator

These support orbit analysis and mission planning workflows.

## 6) Spacecraft control

Spacecraft control is split into:

- `MassModel` (dry + propellant bookkeeping)
- `PropulsionSystem` (thrust, mass flow, delta-v)
- `CommandModel` (time-window burn execution)

## 7) R1 dynamics contracts

R1 introduces rigid-body and docking-focused dynamics primitives:

- `RigidBody6DoFState`, `RigidBodyProperties`, `UnitQuaternion`
- frame-aware `Wrench` application (`INERTIAL` and `BODY` frames)
- deterministic 6-DOF baseline integrator with gyroscopic coupling
- mechanism joint contracts with limit clamping
- docking contact classification with impulse/restitution baseline

These provide deterministic contracts now and are designed to plug into higher-fidelity solvers later.

## 8) R2 propulsion chain

R2 introduces a reduced-order propulsion chain:

- feed network (`tank -> valve -> line`) mass-flow propagation
- ideal-gas combustion chamber pressure update
- thrust decomposition (momentum + pressure)
- leakage model for pressure-driven compartment mass loss

R2.1 extends thrust with optional nozzle-geometry corrections (area ratio + contour loss factors).

## 9) R3 structural baseline and scaling path

R3 currently provides deterministic linear-static FEM baselines for both 2D and 3D structural evaluation.

Scaling path status:
- 2D validity envelopes are implemented (plane-stress/plane-strain assumptions)
- sparse/backend-selectable solve paths are implemented for current 2D baseline (dense, sparse direct, sparse iterative, matrix-free)
- 3D tetrahedral solid baseline is implemented with dense/sparse direct/sparse iterative backends
- 2D-vs-3D model-selection policy helpers are implemented (out-of-plane span/load/constraint thresholds)
- solve telemetry is implemented (backend identity, residuals, iterations, relative residuals, termination reason, nnz/reference-delta fields)

## 10) Communication model

Communication currently provides:

- line-of-sight checks with spherical occluders
- link availability and light-time delay
- delayed delivery channels for uplink/downlink modeling

## 11) Operations layer

Operations APIs handle mission-level behavior:

- rendezvous relative metrics
- docking envelope/state checks
- satellite constellation grouping
- orbital station docking/resource interfaces

## 12) Scenario model

Scenarios are versioned JSON documents (`schema_version = "1.0"`) with:

- metadata
- initial bodies

`scenario_loader` handles load/save; schema validation is performed in parsing.
