# Agent memory guide

This is the canonical memory protocol for coding agents.

## Location and scope

Working memory is local runtime state under:

```text
.agent/memory/
  0-memory-summary.md
  entry-0000000000.md
  entry-0000000001.md
  ...
```

`.agent/` is intentionally gitignored. Memory files are local and not committed.

## Session read rule

Before implementation:
1. Read `.agent/memory/0-memory-summary.md` (if present)
2. Read the last 10 `.agent/memory/entry-*.md` files (if present)

If the directory is missing, create it and continue.

## Entry format

Each entry should start with:

```md
tags: <comma-separated-tags>

- What changed
- Why
- Validation evidence (`ruff` / `mypy` / `pytest`)
- Follow-up items
```

Keep entries short and implementation-focused.

## Compaction rule

Every 10 new entries:
- fold key outcomes into `0-memory-summary.md`
- keep summary current and concise
- keep entries as chronological history

## Bootstrap (new environment)

```bash
mkdir -p .agent/memory
```

Optional starter files:

```bash
touch .agent/memory/0-memory-summary.md
```
