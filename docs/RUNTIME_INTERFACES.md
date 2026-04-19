# Runtime interfaces (Python simulation <-> native desktop client)

This document defines the concrete runtime bridge contract for the desktop client stack.

## Contract source of truth

- Protobuf: `interfaces/runtime_bridge.proto`
- Package: `brambhand.runtime.v1`
- Service: `RuntimeBridge.StreamSimulation`
- Key message parity:
  - `SimulationFrame.body_id_catalog` uses the same init+diff lifecycle contract as replay JSONL

## Transport modes

1. **Live mode**
   - Python runtime publishes `SimulationFrame` over gRPC server stream.
   - Desktop client consumes from `from_sequence` and applies bounded buffering.

2. **Replay mode**
   - Desktop client ingests JSONL replay and maps to the same in-memory frame model used in live mode.
   - Ordering and sequencing semantics must match live mode behavior.

## Ordering and determinism

- `SimulationFrame.sequence` is monotonic and gap-free per run unless explicit drop policy metadata says otherwise.
- `tick_id` is authoritative simulation ordering for physics state.
- `events.sequence` preserves original event ordering within and across frames.
- `body_id_catalog` is the canonical simulation-exported body-ID lifecycle contract:
  - first frame: `initial_body_ids`
  - subsequent frames: `created_body_ids` / `destroyed_body_ids` diffs
- Clients must maintain body-ID catalogs from `body_id_catalog` init+diff metadata (no per-frame body-array scans for ID discovery).
- `schema_version` must be checked by clients before frame acceptance.

## Backpressure policy (baseline)

- Client uses bounded ring buffer.
- On sustained overload, client applies explicit degraded policy:
  - drop oldest non-critical visualization-only frames,
  - never reorder accepted frames,
  - emit operator-visible degraded-mode telemetry.

## Bridge ownership

- Python process remains authoritative for physics and replay persistence.
- Native desktop client is authoritative for rendering and UI interaction only.

## Renderer contract split (2D now, 3D later)

To keep R8.05 replay quicklook and future R8.5 Vulkan rendering compatible, rendering is split into explicit layers:

1. **Ingest contracts** (`client/common/replay_ingest.*`, runtime bridge frames)
   - source-normalized replay/live frame model
2. **View contracts** (`trajectory infographic` / `replay quicklook workflow` payloads)
   - renderer-agnostic event + trajectory semantics
3. **Render configuration contract** (`client/common/render_config.*`)
   - body-role/group policy (`sun`, `planet`, `probe`, dimmed orbits, focus)
3.5 **Render semantics interface** (`client/common/render_semantics.*`)
   - renderer-agnostic interpretation of config into body roles and trajectory-dimming membership
   - concrete config-driven implementation is swappable without changing renderer interfaces
4. **Renderer implementation**
   - current: SDL quicklook 2D (`Quicklook2DReplayRenderer`)
   - planned: Vulkan 3D scene graph/BVH/ray-march path (R8.5)
5. **UI layout policy interfaces** (`src/bin/desktop/ui_layout.*`)
   - renderer-capability-aware panel/layout policies (viewport/sidebar contracts)
   - concrete layout implementations are swappable without changing renderer bootstrap contracts
6. **Quicklook UI/trace policy interfaces** (`src/bin/desktop/quicklook_*_policy.*`)
   - trace continuity/filter + alpha policy and sidebar section/content policy are abstracted from renderer loop
   - concrete quicklook implementations can be replaced per renderer capability profile without changing bootstrap/ingest contracts
7. **Renderer capability profile interface** (`src/bin/desktop/renderer_capability_profile.*`)
   - binds renderer mode to default UI layout/trace/sidebar policy bundles
   - allows future 3D backends to ship capability-specific policy stacks while keeping renderer selection/bootstrap contracts stable
8. **Canvas drawing abstraction** (`src/bin/desktop/quicklook_canvas.hpp` + backend adapters)
   - draw functions use renderer-agnostic canvas primitives (`line`, `rect`, `fill`, `text`, `clip`) instead of direct framework APIs
   - current backend adapter: SDL (`sdl_quicklook_canvas.*`)
   - future backends (e.g., GTK) can reimplement canvas adapter without changing quicklook draw logic
9. **Window/runtime abstraction** (`src/bin/desktop/quicklook_runtime.hpp` + backend adapters)
   - event polling, timing, window size, present/delay are abstracted behind runtime interface
   - current backend adapter: SDL (`sdl_quicklook_runtime.cpp`)
   - future GTK runtime adapters can replace SDL loop wiring without changing quicklook renderer draw logic
10. **Shared plot geometry helpers** (`client/common/plot_geometry.*`)
   - bounds accumulation/finalization, view-bounds transform, and world->viewport mapping are centralized in common module
   - quicklook and future renderers reuse the same coordinate/fit behavior contracts

Rule: layers 1-3 are stable shared contracts; only layer 4 should change across renderer backends.

## Desktop flags relevant to backend evolution

Current `brambhand_desktop` flags:
- `--replay <path>` and `--render-config <path>` (required)
- `--renderer quicklook_2d|vulkan_3d`
  - `quicklook_2d`: available now
  - `vulkan_3d`: reserved/guarded until R8.5
- `--allow-renderer-fallback`
  - allows `--renderer vulkan_3d` requests to fall back to `quicklook_2d`
- `--concurrent-ingest`
  - enables chunked replay ingestion while incrementally refreshing the active quicklook renderer playback state (or workflow-prep path when `--no-window`)
  - emits ingest telemetry (`chunk_frames`, `queue_max_chunks`, `chunks_processed`, `queue_high_watermark`)
- `--ingest-chunk-frames <N>`
  - max frames per ingest chunk in concurrent mode
- `--ingest-queue-max-chunks <N>`
  - bounded producer/consumer queue depth for concurrent ingest mode

Tuning harness:
- `brambhand_replay_ingest_benchmark`
  - sweeps chunk-size/queue-depth candidate pairs and emits CSV telemetry rows
  - supports preset profiles (`interactive|balanced|throughput|all`) and custom candidate lists
  - see `docs/REPLAY_INGEST_TUNING.md`
- `--strict-render-config`
  - fails if configured body IDs are missing from replay
- `--no-window`
  - runs ingest/contract path without opening a renderer window
