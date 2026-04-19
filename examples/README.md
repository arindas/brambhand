# Reference mission harness index

Reference harnesses use canonical IDs and naming documented in `DESIGN.md`.

| Example ID | Milestone | Script | Default `run_id` | Purpose |
|---|---|---|---|---|
| `EX-R10.5-001` | `R10.5` | `ex_r10p5_001_earth_jupiter_transfer.py` | `ex-r10p5-001-earth-jupiter-transfer` | Non-optimizer reference transfer harness for maneuver/replay continuity validation and desktop replay quicklook inputs. |

## Policy

- Add new harnesses by creating a new immutable `EX-<MILESTONE>-<NNN>` ID.
- Do not repurpose an existing ID for changed mission semantics.
- Harnesses are acceptance assets only and must consume shared contracts/modules.
