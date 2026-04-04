# Distributed Tick/Commit Protocol (no partition replicas)

This document specifies distributed execution semantics for `brambhand`.

## 1) Scope and assumptions

- Single-authority partition ownership (no partition replicas in current scope)
- Deterministic logical tick progression
- Barrier-based global commit semantics

## 2) Entities

- **Coordinator**: run-level scheduler and barrier manager
- **Partition owner**: authoritative worker for one partition
- **Persistence layer**: idempotent commit sink keyed by `(run_id, partition_id, tick_id)`

## 3) Tick lifecycle

For logical tick transition `k -> k+1`:

1. `LOCAL_COMPUTE`
   - each partition computes tentative next state
2. `BOUNDARY_EXCHANGE`
   - owners exchange required boundary/coupling payloads
3. `RECONCILE`
   - apply received payloads and coupling constraints
4. `PREPARE`
   - partition reports ready status + state digest
5. `GLOBAL_COMMIT`
   - coordinator commits tick only if all required partitions prepared
6. `PERSIST_EMIT`
   - commit-grade artifacts written idempotently

## 4) Atomicity rule

A tick is committed only when all required partitions for that run/tick
are ready. No partial tick commit is allowed.

## 5) Retry and recovery

If a partition misses deadline:
- deterministic retry window
- optional reassignment/repartition
- or controlled run pause

Recovery policy must not create duplicate commit semantics.

## 6) Contract payload requirements

Cross-partition payloads must include:
- schema version
- units/frames metadata
- source partition id
- source tick id
- payload timestamp/logical tick

## 7) Coupling fallback/degraded-mode hierarchy

When coupling or barrier pressure exceeds policy thresholds:
1. reduce visualization workload (quality/frequency)
2. reduce non-critical telemetry sampling frequency
3. switch to slower pacing target
4. controlled pause if commit safety cannot be guaranteed

All fallback transitions must emit explicit operator-visible events.

## 8) Persistence/provenance requirements

For each committed partition tick, persist:
- run_id, partition_id, tick_id
- worker_id
- scheduler order info
- pacing mode/sim time metadata
- state digest/checkpoint reference
- event/telemetry references

Replay reconstruction must follow committed logical tick order.

## 9) Persistence durability policy (initial)

- `events`: durable commit-level writes (required for replay correctness)
- `tick metadata/provenance`: durable commit-level writes
- `telemetry_samples`: durable batched writes with bounded-loss policy configurable by profile
- `checkpoints`: durable and versioned; restart-safe

## 10) Determinism constraints

- deterministic scheduler order per tick
- deterministic serialization for contract payloads
- deterministic retry policy

## 11) Validation hooks

Protocol metrics to emit:
- barrier wait time
- commit skew across partitions
- retry counts/timeouts
- commit latency to persistence
