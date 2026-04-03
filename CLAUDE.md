# CLAUDE.md

This file is a Claude-facing mirror of `AGENT.md`.

For this repository, follow `AGENT.md` as the canonical operating procedure.

## Quick runbook

1. Read first:
   - `AGENT.md`
   - `README.md`
   - `SKILLS.md`
   - `TODO.md`
2. Load memory:
   - `.agent/memory/0-memory-summary.md`
   - last 10 `.agent/memory/entry-*.md`
3. Reconcile planning docs:
   - `REQUIREMENTS.md` -> `DESIGN.md` -> `VERIFICATION.md` -> `VALIDATION.md`
4. Run baseline checks:

```bash
source .venv/bin/activate
ruff check .
mypy src tests
pytest -q
```

## Work protocol

- Pick next unchecked item from `TODO.md`.
- If scope/contracts change, update docs first:
  `REQUIREMENTS` -> `DESIGN` -> `TODO` -> `VERIFICATION`.
- Implement with tests.
- Re-run quality gates.
- Sync docs + release notes.

## Memory protocol

At end of meaningful work, add one new memory entry:

```md
tags: <comma-separated-tags>

- What changed
- Why
- Validation evidence
- Follow-ups
```

Compaction: every 10 new entries, fold key context into `0-memory-summary.md`.

## Canonical FEM imports

Use:
- `brambhand.structures.fem.contracts`
- `brambhand.structures.fem.geometry`
- `brambhand.structures.fem.backends`
- `brambhand.structures.fem.selection`
- `brambhand.structures.fem.solver`

Avoid legacy `fem_*` paths.
