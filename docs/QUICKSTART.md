# Quickstart

## Prerequisites

- Python 3.12+
- `uv`

## Setup

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e './python/brambhand[dev]'
```

## Run quality checks

```bash
ruff check python/brambhand
mypy python/brambhand/src python/brambhand/tests
pytest python/brambhand/tests
```

## Create a minimal scenario file

Create `scenario.json`:

```json
{
  "schema_version": "1.0",
  "metadata": {"name": "quickstart"},
  "bodies": [
    {
      "name": "earth",
      "mass": 5.972e24,
      "state": {"position": [0, 0, 0], "velocity": [0, 0, 0]}
    },
    {
      "name": "sat",
      "mass": 1000,
      "state": {"position": [7000000, 0, 0], "velocity": [0, 7500, 0]}
    }
  ]
}
```

## Validate scenario

```bash
brambhand validate scenario.json
```

## Run simulation and save replay

```bash
brambhand run scenario.json --dt 10 --steps 30 --replay-out replay.jsonl
```

## Inspect replay events

```bash
brambhand replay replay.jsonl --kind step_completed --start-time 0 --end-time 300
```
