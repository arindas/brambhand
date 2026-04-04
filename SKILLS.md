# SKILLS

## Session continuity (must-do at session start)

`AGENT.md` is the canonical, strict runbook. This file is supporting detail.

Use this sequence every new session:

1. Read `README.md` then `SKILLS.md` then `TODO.md`.
2. Load memory context from:
   - `.agent/memory/0-memory-summary.md`
   - most recent `.agent/memory/entry-*.md` files
3. Reconcile planning docs in order:
   - `REQUIREMENTS.md -> DESIGN.md -> VERIFICATION.md -> VALIDATION.md`
4. Run environment sanity checks:

```bash
source .venv/bin/activate
ruff check .
mypy src tests
pytest -q
```

5. Continue implementation from existing roadmap in `TODO.md`.

## Agent Memory

Memory system to keep track of project work progress.
See `docs/AGENT_MEMORY.md` for the exact read/write/compaction protocol.

```
.agent/
└── memory
    ├── 0-memory-summary.md
    └── entry-0000000000.md
    ... more entries ...
```

`0-memory-summary.md` keeps a running summary.

`entry-N.md` logs individual memory entries. Each entry should start with:

```text
tags: <comma-separated-tags>
```

Memory compaction policy:
- keep active context as: summary + last 10 entries
- every 10 new entries, merge key outcomes into `0-memory-summary.md`
- keep entries concise and implementation-focused (what changed, where, evidence)


## Research skills (use only when needed)

These are **optional** skills. They are necessary only when local project docs/tests
are insufficient (e.g., solver methods, physics references, standards).

Default priority:
1. Local project docs (`REQUIREMENTS`, `DESIGN`, `VERIFICATION`, `VALIDATION`, `TODO`)
2. Existing code/tests in this repository
3. External research (web/PDF/offline library)

### Web research

Use `bash` + `curl` for targeted lookups.

Guidelines:
- Start with a specific query and shortlist sources by title/reputation.
- Read table of contents/section headers first.
- Extract only sections relevant to the active requirement.
- Record source URL/title in notes when findings affect design/validation.

### PDF research

Use `bash` + `pdftotext` for scoped extraction from PDFs.

Guidelines:
- Do not extract full documents by default.
- Locate TOC/chapter first, then extract only relevant pages.
- Account for page-number offsets (front matter vs numbered chapters).
- Capture citation details for any benchmark/validation assumption.

### Offline knowledge base (optional)

An optional SSH-accessible knowledge-base host may contain additional technical PDFs.
Use only when needed for benchmarks or domain references.

Connection parameters should come from environment variables:

```bash
# expected environment variables
# KB_SSH_USER
# KB_SSH_HOST
# KB_ROOT_DIR

ssh "${KB_SSH_USER}@${KB_SSH_HOST}"
cd "${KB_ROOT_DIR}"
# expected layout: <discipline>/<subtopic>/<specialization-or-doc-type>/<document>
```

If any parameter is missing, ask interactively before accessing the host.

When using offline sources:
- apply the PDF research workflow above
- cite source metadata in design/validation notes
- keep extracted material tightly scoped to current requirements
