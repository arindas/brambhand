# AGENT.md

Canonical operating guide for **any coding agent** working in this repository.

If this file conflicts with other guidance, follow this file for session procedure.

## 1) Session start (strict order)

1. Read, in order:
   - `AGENT.md` (this file)
   - `README.md`
   - `SKILLS.md`
   - `TODO.md`
2. Load memory context:
   - `.agent/memory/0-memory-summary.md`
   - most recent `.agent/memory/entry-*.md` files (last 10)
3. Reconcile planning docs before coding:
   - `REQUIREMENTS.md` -> `DESIGN.md` -> `VERIFICATION.md` -> `VALIDATION.md`
4. Run baseline checks:

```bash
source .venv/bin/activate
ruff check .
mypy src tests
pytest -q
```

Do not start implementation if baseline is red unless task is to fix baseline.

---

## 2) How to pick work

1. Find next unchecked item in `TODO.md`.
2. If task changes scope/contracts, update docs first in this order:
   - `REQUIREMENTS.md`
   - `DESIGN.md`
   - `TODO.md`
   - `VERIFICATION.md`
3. Implement smallest coherent change with tests.
4. Re-run quality gates.
5. Sync docs and release notes.

---

## 3) Memory system protocol (required)

Memory path:

```text
.agent/memory/
  0-memory-summary.md
  entry-0000000000.md
  ...
```

### Read protocol
- Always read summary + last 10 entries before coding.

Example:

```bash
ls .agent/memory/entry-*.md | sort | tail -n 10
```

### Write protocol (end of meaningful work)
Create one new entry with next sequence id.

Entry format:

```md
tags: <area1>, <area2>, <type>

- What changed (files/modules)
- Why (linked TODO/FR/NR if relevant)
- Validation evidence (`ruff`/`mypy`/`pytest` status)
- Any follow-up risks or next actions
```

### Compaction protocol
- After each block of 10 new entries, roll key outcomes into `0-memory-summary.md`.
- Keep summary focused on current capability and open fronts.

---

## 4) Definition of done for each task

A task is done only if all are true:

- Code implemented
- Tests added/updated
- `ruff`, `mypy`, `pytest` passing
- `TODO.md` status updated
- `REQUIREMENTS`/`DESIGN`/`VERIFICATION`/`VALIDATION` updated if scope changed
- `RELEASE_NOTES.md` updated for notable behavior/API changes
- Memory entry written

---

## 5) Structural FEM canonical paths

Use only canonical FEM module paths:

- `brambhand.structures.fem.contracts`
- `brambhand.structures.fem.geometry`
- `brambhand.structures.fem.backends`
- `brambhand.structures.fem.selection`
- `brambhand.structures.fem.solver`

Do not reintroduce legacy `fem_*` shim module imports.

---

## 6) End-of-session checklist

1. Ensure docs/code/tests are in sync.
2. Run:

```bash
ruff check .
mypy src tests
pytest -q
```

3. Update `TODO.md` checkboxes.
4. Write new `.agent/memory/entry-*.md`.
5. If compaction boundary reached, update `0-memory-summary.md`.
