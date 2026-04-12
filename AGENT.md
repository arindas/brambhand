# AGENT.md

Canonical runbook for coding agents in this repository.

## 1) Start of session

Read in order:
1. `README.md`
2. `TODO.md`
3. `.agent/memory/0-memory-summary.md`
4. Last 10 `.agent/memory/entry-*.md`
5. `REQUIREMENTS.md -> DESIGN.md -> VERIFICATION.md -> VALIDATION.md`

Run baseline checks:

```bash
source .venv/bin/activate
ruff check python/brambhand
mypy python/brambhand/src python/brambhand/tests
pytest -q python/brambhand/tests
cmake -S c/brambhand -B c/brambhand/build
cmake --build c/brambhand/build -j2
ctest --test-dir c/brambhand/build --output-on-failure
```

If baseline is red, fix baseline first unless task explicitly says otherwise.

## 2) Work loop

1. Pick next unchecked item from `TODO.md`.
2. If scope/contracts change, update docs first:
   - `REQUIREMENTS.md`
   - `DESIGN.md`
   - `TODO.md`
   - `VERIFICATION.md`
3. Implement smallest coherent change.
4. Add/update tests.
5. Re-run quality gates.
6. Update docs and release notes as needed.

## 3) Memory protocol

Use the canonical memory guide:
- `docs/AGENT_MEMORY.md`

At end of meaningful work, add one new memory entry and include test/lint/type-check evidence.

## 4) Research loop (optional)

Do not run research every session.

Run research only when needed, for example:
- local docs/tests are insufficient for a design or validation decision
- a new roadmap area starts (new physics domain, coupling strategy, or benchmark policy)
- assumptions need external cross-checks

Workflow:
1. use env-configured knowledge-base access from `SKILLS.md`
2. extract only relevant sections (no full-document dumps)
3. record findings in `docs/RESEARCH_NOTES.md`
4. compare against `REQUIREMENTS.md`, `DESIGN.md`, `TODO.md`, `VERIFICATION.md`, `VALIDATION.md`
5. convert actionable deltas into explicit doc/TODO updates

## 5) Done criteria

A task is done when all are true:
- code + tests updated
- `ruff`, `mypy`, `pytest` pass
- related `TODO.md` item updated
- planning/traceability docs updated if scope changed
- `RELEASE_NOTES.md` updated for notable changes
- memory entry written
