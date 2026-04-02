# DESIGN

## Architecture Principles
- Deterministic simulation core first.
- Clear module boundaries (physics, GN&C, communication, scenario, runtime).
- Data-driven scenarios.
- Test-first for each module.

## Proposed Module Layout

```
src/
  brambhand/
    core/
      simulation_clock.py
      event_bus.py
      state_snapshot.py
    physics/
      vector.py
      frames.py
      body.py
      gravity_model.py
      integrator.py
    spacecraft/
      spacecraft.py
      propulsion.py
      mass_model.py
      command_model.py
    guidance/
      orbit_elements.py
      maneuver_planner.py
      trajectory_predictor.py
    communication/
      link_model.py
      delay_channel.py
      visibility.py
    operations/
      rendezvous_metrics.py
      docking_model.py
    scenario/
      scenario_schema.py
      scenario_loader.py
      replay_log.py
```

## Data Flow
1. Scenario loader builds initial world state.
2. Simulation clock advances fixed timestep.
3. Physics integrator updates all entities from accumulated forces.
4. Command model applies delayed uplink commands.
5. Guidance/operations update targets and mission events.
6. Communication model advances links and telemetry delays.
7. Snapshot + event log emitted.

## Key Design Decisions
- **Fixed-step integration by default** for determinism (higher-order integrator optional).
- **Event-sourced mission timeline** for replay and debugging.
- **Frame conversion utilities centralized** to avoid duplicated coordinate math.
- **Scenario schema versioning** to keep backward compatibility.

## Incremental Milestones

### M1 — Orbital physics baseline
- N-body gravity
- fixed-step integrator
- state snapshot export
- deterministic replay test

### M2 — Spacecraft control baseline
- propulsion + mass depletion
- command ingestion
- impulsive and finite burns

### M3 — Guidance and communication baseline
- orbital elements + trajectory predictor
- link delay + line-of-sight
- event logging for comms

### M4 — Multi-vehicle operations
- rendezvous metrics
- docking state machine

### M5 — Extended systems
- constellation tools
- station/infrastructure operations
- interplanetary logistics and asteroid operations

## Requirements -> Design Traceability Matrix

| Requirement group | Primary modules | Design rationale |
|---|---|---|
| FR-001..FR-004 (simulation core) | `physics/vector.py`, `physics/body.py`, `physics/gravity_model.py`, `physics/integrator.py`, `core/event_bus.py`, `core/state_snapshot.py` | Deterministic fixed-step propagation with explicit state/event records. |
| FR-005..FR-008 (spacecraft control) | `spacecraft/mass_model.py`, `spacecraft/propulsion.py`, `spacecraft/command_model.py` | Separate mass bookkeeping, propulsion physics, and command scheduling for modularity and testability. |
| FR-009..FR-012 (guidance) | `guidance/orbit_elements.py`, `guidance/trajectory_predictor.py` | Convert between operational orbit descriptors and inertial state; reuse integrator for prediction consistency. |
| FR-013..FR-015 (communication) | `communication/visibility.py`, `communication/link_model.py`, `communication/delay_channel.py` | Decouple geometry/availability from delayed transport behavior. |
| FR-016..FR-018 (operations) | `operations/rendezvous_metrics.py`, `operations/docking_model.py` | Keep mission-level safety/state logic independent of low-level dynamics code. |
| FR-019..FR-021 (scenario/reproducibility) | `scenario/scenario_schema.py`, `scenario/scenario_loader.py`, `scenario/replay_log.py`, `cli.py` | Versioned scenario contracts + replay persistence for reproducible runs and tooling integration. |

## Design -> Verification linkage
Verification evidence for each requirement group is maintained in `VERIFICATION.md` via concrete test files.
