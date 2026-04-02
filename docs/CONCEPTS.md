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

- Cartesian <-> Keplerian conversions
- forward prediction using current integrator

These support orbit analysis and mission planning workflows.

## 6) Spacecraft control

Spacecraft control is split into:

- `MassModel` (dry + propellant bookkeeping)
- `PropulsionSystem` (thrust, mass flow, delta-v)
- `CommandModel` (time-window burn execution)

## 7) Communication model

Communication currently provides:

- line-of-sight checks with spherical occluders
- link availability and light-time delay
- delayed delivery channels for uplink/downlink modeling

## 8) Operations layer

Operations APIs handle mission-level behavior:

- rendezvous relative metrics
- docking envelope/state checks
- satellite constellation grouping
- orbital station docking/resource interfaces

## 9) Scenario model

Scenarios are versioned JSON documents (`schema_version = "1.0"`) with:

- metadata
- initial bodies

`scenario_loader` handles load/save; schema validation is performed in parsing.
