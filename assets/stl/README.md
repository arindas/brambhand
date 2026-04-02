# STL test fixtures

This directory stores STL fixtures for geometry-dependent tests.

## Layout

- `idealized/`:
  analytically simple fixtures for deterministic sanity tests
  (cube, cylinder, cone, frustum, simplified nozzle, de Laval nozzle).

- `reference/`:
  reference-like fixtures for regression and validation-style tests.
  Current files are stubs and should be replaced with benchmark-derived assets.

- `metadata/fixtures.json`:
  machine-readable fixture index (purpose + provenance).

## Usage policy

- Use `idealized/` in fast unit tests.
- Use `reference/` in integration/validation suites.
- Keep fixture metadata updated when adding/replacing geometry.
