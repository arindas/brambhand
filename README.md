# brambhand

A scientifically accurate spaceflight sandbox.

<!-- Read this README at the start of every session for project context. -->

`brambhand` aims to simulate the following:
- orbital dynamics
- spacecraft control and dynamics
- spacecraft trajectory control
- navigation and guidance
- datalink and communication
- spacecraft rendezvous and docking
- satellite constellation
- space stations
- infrastructure in LEO and UEO
- interplanetary satellite systems
- interplanetary payload transfer systems
- asteroid trajectory modification
- asteroid minding

## Session restart checklist (read first)

When starting a new agent session, do this in order:

1. Read `README.md` (this file), `SKILLS.md`, and `TODO.md`.
2. Read memory summary and recent entries:
   - `.agent/memory/0-memory-summary.md`
   - latest `.agent/memory/entry-*.md` files
3. Re-read planning docs before implementation changes:
   - `REQUIREMENTS.md`
   - `DESIGN.md`
   - `VERIFICATION.md`
   - `VALIDATION.md`
4. Re-establish environment:

```bash
source .venv/bin/activate
ruff check .
mypy src tests
pytest -q
```

5. Continue from `TODO.md` roadmap sections (R1..R8.1, R7.2 etc.).

## Development quickstart

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
pytest
ruff check .
mypy src tests
```

## CLI runner

Validate a scenario file:

```bash
brambhand validate path/to/scenario.json
```

Run a scenario JSON file with fixed-step propagation:

```bash
brambhand run path/to/scenario.json --dt 10 --steps 100 --replay-out replay.jsonl
```

Inspect replay output with filters:

```bash
brambhand replay replay.jsonl --kind step_completed --start-time 100 --end-time 500
```

## Documentation

- Docs index: [`docs/README.md`](./docs/README.md)
- Quickstart: [`docs/QUICKSTART.md`](./docs/QUICKSTART.md)
- Concepts: [`docs/CONCEPTS.md`](./docs/CONCEPTS.md)
- Workflows: [`docs/WORKFLOWS.md`](./docs/WORKFLOWS.md)
- Tutorials: [`docs/TUTORIALS.md`](./docs/TUTORIALS.md)
- API reference: [`docs/API_REFERENCE.md`](./docs/API_REFERENCE.md)
- Distributed protocol: [`docs/DISTRIBUTED_PROTOCOL.md`](./docs/DISTRIBUTED_PROTOCOL.md)
- Performance SLOs: [`docs/PERFORMANCE_SLOS.md`](./docs/PERFORMANCE_SLOS.md)
- Validation criteria: [`VALIDATION.md`](./VALIDATION.md)

<!--

For the files mentioned below, always check contents before overwriting.

See agent skills in ./SKILLS.md

See todo list in ./TODO.md. Avoid creating additional files for tracking action items.

Ensure you see SKILLS and TODO before requirements. Ensure that SKILLS are completely supported before anything else.

See requirements in ./REQUIREMENTS.md.

Manage project developement workflow and project structure in ./CONTRIBUTING.md.

-->
