# Contributing to brambhand

Thanks for contributing to **brambhand** — a scientifically grounded spaceflight sandbox.

This guide reflects the current repository layout, Python tooling, and development workflow.

## Project workflow

For human and AI contributors, `AGENT.md` defines the canonical session runbook
(memory handling, planning order, execution loop, and closeout checklist).

Follow this order for all substantial work:

1. Review project context in `README.md`
2. Check skills/process notes in `SKILLS.md`
3. Review and update `REQUIREMENTS.md`
4. Reflect design decisions in `DESIGN.md`
5. Update execution plan in `TODO.md`
6. Implement code + tests
7. Update `VERIFICATION.md`, `VALIDATION.md`, and docs as needed

## Current repository structure

```text
.
├── .agent/                # memory summary + session entries
├── .github/               # issue templates, PR template, CI workflows
├── assets/                # STL fixtures and metadata manifests
├── docs/                  # quickstart, concepts, workflows, tutorials, API reference
├── pyproject.toml
├── README.md
├── AGENT.md             # canonical agent runbook (session + memory protocol)
├── CLAUDE.md            # Claude-facing mirror of AGENT.md
├── REQUIREMENTS.md
├── DESIGN.md
├── VERIFICATION.md
├── VALIDATION.md
├── TODO.md
├── RELEASE_NOTES.md
├── CONTRIBUTING.md
├── SKILLS.md
├── .agent/memory/README.md  # memory entry/compaction protocol
├── src/
│   └── brambhand/
│       ├── cli.py
│       ├── core/
│       ├── physics/
│       ├── spacecraft/
│       ├── guidance/
│       ├── communication/
│       ├── operations/
│       ├── infrastructure/
│       ├── dynamics/      # R1: rigid-body 6-DOF, mechanisms, docking contact
│       ├── propulsion/    # R2/R2.1: fluids, combustion, thrust, leakage, geometry correction
│       ├── structures/    # R3: baseline FEM structural evaluation
│       └── scenario/
└── tests/
```

## Python environment and tooling

This project uses **uv** + `pyproject.toml`.

### Setup

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
```

### Required local checks before commit

```bash
ruff check .
mypy src tests
pytest
```

All three should pass before opening a PR.

## CLI usage (for manual verification)

Entry point is `brambhand`.

```bash
# validate scenario
brambhand validate path/to/scenario.json

# run simulation
brambhand run path/to/scenario.json --dt 10 --steps 100 --replay-out replay.jsonl

# inspect replay log
brambhand replay replay.jsonl --kind step_completed --start-time 100 --end-time 500
```

## Coding standards

- Use Python 3.12+ compatible code.
- Use `snake_case` for modules, functions, and variables.
- Keep modules focused and cohesive.
- Prefer immutable dataclasses (`frozen=True`) for state records where practical.
- Add/maintain type hints for public APIs.
- Add tests with every behavior change.

## Testing expectations

- Add unit tests for new modules/functions.
- Add integration tests for cross-module behavior (simulation flows, command delays, docking scenarios, etc.).
- Keep deterministic behavior where expected (especially replay/event ordering).

## Documentation expectations

When behavior changes, update relevant docs in the same PR:

- `REQUIREMENTS.md` (what the system must do)
- `DESIGN.md` (how it is structured)
- `VERIFICATION.md` (verification strategy and traceability)
- `VALIDATION.md` (benchmark/acceptance validation criteria)
- `TODO.md` (execution tracking)
- `README.md` (user/developer entry points)

## Issues and pull requests

Use the GitHub issue templates in `.github/ISSUE_TEMPLATE/` when opening bugs,
feature requests, or documentation updates.

## Pull request guidelines

PRs should include:

- Purpose and scope
- Requirement/design linkage (FR/NR or milestone items)
- Test evidence (`ruff`, `mypy`, `pytest` results)
- Notable risks/assumptions

Keep commits/PRs focused and reviewable.

Use the PR checklist in `.github/pull_request_template.md`.

## See also

- [README.md](./README.md)
- [REQUIREMENTS.md](./REQUIREMENTS.md)
- [DESIGN.md](./DESIGN.md)
- [VERIFICATION.md](./VERIFICATION.md)
- [VALIDATION.md](./VALIDATION.md)
- [TODO.md](./TODO.md)
- [SKILLS.md](./SKILLS.md)
