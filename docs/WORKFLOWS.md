# Workflows

## A. User workflow: `validate -> run -> replay`

1. Validate scenario:

```bash
brambhand validate scenario.json
```

2. Run deterministic propagation:

```bash
brambhand run scenario.json --dt 10 --steps 100 --replay-out replay.jsonl
```

3. Inspect replay stream:

```bash
brambhand replay replay.jsonl --kind step_completed --start-time 100 --end-time 500
```

## B. Physics workflow: model and verify an orbit

1. Define bodies in scenario JSON (e.g., Earth + satellite).
2. Run with appropriate `dt` and total steps.
3. Use replay and final output to verify expected behavior (e.g., bounded radius drift).
4. Add/update tests for the scenario in `tests/`.

## C. Spacecraft burn workflow

1. Build `MassModel` and `PropulsionSystem`.
2. Apply a burn directly (`apply_burn`) or through `CommandModel.apply_window`.
3. Validate:
   - propellant consumed
   - burn duration achieved
   - expected delta-v direction and magnitude
4. Add unit/integration tests for burn behavior.

## D. Communication delay workflow

1. Compute link availability with `LinkModel.evaluate(...)`.
2. Enqueue command/telemetry in `DelayChannel.send(...)` with evaluated delay.
3. Poll `receive_ready(...)` at simulation times to model delayed arrival.

## E. Rendezvous and docking workflow

1. Compute relative metrics via `compute_rendezvous_metrics`.
2. Evaluate `DockingModel` against configured capture thresholds.
3. Handle outcomes:
   - `APPROACH`
   - `FAILED` (+ reason)
   - `DOCKED`

## F. Scenario management workflow

1. Build or load `Scenario` (`scenario_loader`).
2. Save scenario snapshots in source control.
3. Record mission events using `ReplayLog` for reproducibility/regression checks.

## G. Propulsion geometry-sensitivity workflow (R2.1)

1. Build `NozzleParams` baseline inputs (exit area, ambient pressure, exhaust velocity).
2. Optionally provide `NozzleGeometryCorrection` (throat area, contour loss factor).
3. Estimate thrust via `estimate_nozzle_thrust(...)` with/without geometry correction.
4. Validate expected sensitivity:
   - increasing area ratio should increase thrust estimate (within model bounds)
   - decreasing contour-loss factor should reduce thrust estimate
5. Add or update tests in `tests/test_propulsion_r2_contracts.py`.

## H. Structural solver workflow (R3 scaling)

1. Start from a structural case and classify it as:
   - 2D validity envelope candidate, or
   - 3D required case (`select_structural_model_dimension(...)`).
2. Build either `FEMModel2D` or `FEMModel3D` and select structural backend profile (`dense`, `sparse_direct`, `sparse_iterative`, matrix-free for 2D when available).
3. Execute solve (`solve_linear_static_fem(...)` or `solve_linear_static_fem_3d(...)`) and capture telemetry:
   - assembly time
   - solve time
   - iterations/residuals
   - matrix nonzero metrics (`nnz`).
4. Validate output equivalence/tolerance against reference backend for the same case.
5. Add/update deterministic and performance tests for selected dimensionality/profile.

## I. Contributor workflow

1. Start from `TODO.md` milestone/action items.
2. Implement with tests in the same change.
3. Run local quality gates:

```bash
ruff check .
mypy src tests
pytest
```

4. Open PR using `.github/pull_request_template.md`.
