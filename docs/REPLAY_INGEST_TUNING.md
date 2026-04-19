# Replay ingest tuning guide (desktop quicklook)

This guide documents chunk-size and queue-depth tuning for desktop replay ingest (`--concurrent-ingest`) and the benchmark harness used to measure tradeoffs.

## Why tune

Concurrent ingest performance depends on workload shape:
- replay file size / frame count
- callback/render-side work per update (workflow extraction, UI refresh)
- storage throughput and CPU availability

Two knobs dominate behavior:
- `chunk_size_frames`: larger chunks reduce callback overhead but increase update latency
- `queue_max_chunks`: larger queues improve producer throughput under heavy callback cost but increase memory pressure

## Profile presets

Use these as starting points before custom sweeps:

- `interactive` (lower update latency):
  - chunk candidates: `64,128,256`
  - queue candidates: `1,2,4`
- `balanced` (default):
  - chunk candidates: `128,256,512`
  - queue candidates: `2,4,8`
- `throughput` (higher ingest throughput):
  - chunk candidates: `512,1024,2048`
  - queue candidates: `4,8,16`
- `all` (broad sweep):
  - chunk candidates: `64,128,256,512,1024`
  - queue candidates: `1,2,4,8,16`

## Benchmark harness

Native binary:

```bash
./c/brambhand/build/brambhand_replay_ingest_benchmark --replay replay.jsonl --profile balanced
```

### Important options

- `--replay <path>` (required)
- `--profile interactive|balanced|throughput|all`
- `--chunk-frames-list <csv>` override profile chunk candidates
- `--queue-max-chunks-list <csv>` override profile queue candidates
- `--iterations <N>` number of runs per candidate pair
- `--consumer-delay-ms <N>` emulate callback/render cost
- `--no-sequential-baseline` skip sequential baseline rows

### Example sweeps

```bash
# Balanced preset with callback pressure simulation
./c/brambhand/build/brambhand_replay_ingest_benchmark \
  --replay replay.jsonl \
  --profile balanced \
  --iterations 5 \
  --consumer-delay-ms 1

# Targeted custom sweep
./c/brambhand/build/brambhand_replay_ingest_benchmark \
  --replay replay.jsonl \
  --chunk-frames-list 128,256,384,512 \
  --queue-max-chunks-list 2,4,6,8 \
  --iterations 4
```

Harness output is CSV rows with elapsed time and queue/backpressure telemetry fields:
- `elapsed_ms`
- `chunks_processed`
- `queue_high_watermark`
- `producer_wait_count`

`producer_wait_count` rising with low queue depths indicates backpressure from the consumer callback path.

## Practical selection rules

1. Start from profile preset matching operator goal (`interactive` vs `throughput`).
2. Keep smallest chunk that avoids excessive callback overhead.
3. Increase queue depth until `producer_wait_count` stabilizes near zero (or acceptable).
4. Re-test with realistic callback cost (`--consumer-delay-ms`) and representative large replays.
5. Lock selected pair into desktop invocation flags:
   - `--ingest-chunk-frames <N>`
   - `--ingest-queue-max-chunks <N>`
