# Runtime interfaces (Python simulation <-> native desktop client)

This document defines the concrete runtime bridge contract for the desktop client stack.

## Contract source of truth

- Protobuf: `interfaces/runtime_bridge.proto`
- Package: `brambhand.runtime.v1`
- Service: `RuntimeBridge.StreamSimulation`

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
