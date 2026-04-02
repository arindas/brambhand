# SKILLS

## Session continuity (must-do at session start)

Use this sequence every new session:

1. Read `README.md` then `SKILLS.md` then `TODO.md`.
2. Load memory context from:
   - `.agent/memory/0-memory-summary.md`
   - most recent `.agent/memory/entry-*.md` files
3. Reconcile planning docs in order:
   - `REQUIREMENTS.md` -> `DESIGN.md` -> `VERIFICATION.md` -> `VALIDATION.md`
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

```
.agent/
└── memory
    ├── 0-memory-summary.md
    └── entry-0000000000.md
    ... more entries ...
```

`0-memory-summary.md` keeps a running summary.

`entry-N.md` logs individual memory entiries. Each memory entry is prefaced with a set of tags to faciliate searching
Memory compaction happens every 10 entries into the running summary. So working memory should be summary and last
10 entries with optional tag based keyword search or regular search for looking up specific entries


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

A local-network SSH host contains additional technical PDFs.
Use only when needed for benchmarks or domain references.

```bash
ssh arindas@192.168.1.2
cd ebooks
# layout: <discipline>/<subtopic>/<specialization-or-doc-type>/<document>
```

When using offline sources:
- apply the PDF research workflow above
- cite source metadata in design/validation notes
- keep extracted material tightly scoped to current requirements
