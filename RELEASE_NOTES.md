# Release Notes

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
