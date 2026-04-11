# Performance and Pacing SLOs

This document defines initial SLOs for runtime pacing, distributed synchronization,
and rendering responsiveness.

> These are initial engineering targets and may be revised with benchmark evidence.

## 1) Execution profiles

- **Operational profile**: near-real-time decision support
- **Analysis profile**: higher fidelity, may be slower than real-time
- **Throughput profile**: max simulation throughput (offline)

## 2) Runtime pacing SLOs

| Metric | Operational | Analysis | Throughput |
|---|---:|---:|---:|
| Cadence error (P95) | <= 5% target tick period | <= 15% | N/A (unpaced) |
| Scheduler jitter (P95) | <= 10 ms | <= 30 ms | N/A |
| Tick drift over 10 min | <= 0.5% | <= 2% | N/A |

## 3) Distributed synchronization SLOs

| Metric | Target |
|---|---:|
| Barrier commit skew (P95) | <= 20 ms |
| Barrier timeout rate | < 0.1% ticks |
| Deterministic retry success | >= 99.9% within policy window |

## 4) Persistence SLOs

| Metric | Target |
|---|---:|
| Tick commit persistence latency (P95) | <= 50 ms |
| Tick commit persistence latency (P99) | <= 120 ms |
| Idempotent duplicate-commit conflict rate | 0 tolerated semantic duplicates |

## 5) Visualization SLOs

| Metric | Operational | Analysis |
|---|---:|---:|
| Frame time (P95) | <= 33 ms (~30 FPS) | <= 100 ms (~10 FPS) |
| Replay camera sync error | <= 1 simulation tick | <= 1 simulation tick |
| Temporal instability alarms | none persistent > 3 s window | bounded within configured threshold |

## 6) Structural solver SLOs (initial)

| Metric | 2D baseline (operational) | 3D coarse (operational) | 3D analysis |
|---|---:|---:|---:|
| Structural solve latency per update (P95) | <= 20 ms | <= 60 ms | <= 250 ms |
| Structural memory growth target | nnz-based sparse scaling | nnz-based sparse scaling | nnz-based sparse scaling |
| Backend switch determinism drift | <= configured tolerance | <= configured tolerance | <= configured tolerance |

## 6.1) Propulsion flow/slosh SLOs (initial)

| Metric | Reduced-order operational | Reduced-order analysis | CFD-coupled analysis (optional) |
|---|---:|---:|---:|
| Chamber/flow+slosh update latency per tick (P95) | <= 10 ms | <= 30 ms | <= 150 ms |
| Cadence-guard fallback trigger | N/A | N/A | required (`CFD -> reduced-order`) |
| Coupling determinism drift (fallback transition) | <= configured tolerance | <= configured tolerance | <= configured tolerance |

## 6.2) Desktop UI/render + Python bridge SLOs (initial)

| Metric | Operational | Analysis |
|---|---:|---:|
| Vulkan render frame time (P95) | <= 16.6 ms (~60 FPS target) | <= 50 ms (~20 FPS) |
| UI input-to-present latency (P95) | <= 50 ms | <= 120 ms |
| Live stream ingest lag vs latest committed sim tick (P95) | <= 2 ticks | <= 5 ticks |
| Stream reorder/drop semantic violations | 0 tolerated | 0 tolerated |
| Backpressure degraded-mode activation visibility | required | required |

## 7) Mode-selection thresholds (initial policy)

Suggested automatic mode selection:
- choose **single-node operational** when projected partition count <= 1 and operational latency SLO is active.
- choose **single-node throughput** when no wall-clock pacing target is required.
- choose **distributed partitioned** when projected partition count > 1 or estimated tick budget exceeds 80% of operational target on single node.
- choose **hybrid portfolio** when both many-run throughput and large-run partitioning are simultaneously scheduled.

## 8) Backpressure policy

If SLO violations persist:
1. reduce render quality/frequency
2. reduce non-critical telemetry sampling
3. switch pacing mode (e.g., `real-time -> slowed`)
4. controlled pause for operator action

## 9) Mapping to requirements

- NR-018..NR-021: rendering and ray-marching quality/perf controls
- NR-022..NR-024: pacing and timeline-equivalence controls
- NR-029..NR-031: distributed barrier and persistence stability
- NR-032..NR-036: structural solver scalability/determinism/fallback observability, including production matrix-free stability expectations
- NR-058: slosh/CFD cadence-budget controls and explicit fallback behavior
- NR-060..NR-064: desktop render/input latency, Python-bridge backpressure, stream-ordering parity, Vulkan hazard/fallback observability, and UI/renderer responsiveness targets

## 10) Observability metrics to publish

- cadence error series
- scheduler jitter/drift
- barrier wait/skew
- commit latency percentiles
- render frame-time percentiles
- degraded-mode activation events
- structural iterative convergence series (iterations/residuals)
- matrix-free mode stability/failure-rate metrics by profile
- propulsion chamber/slosh update latency percentiles by profile
- CFD-coupled fallback activation counts and transition durations
- desktop input-to-present latency percentiles
- live bridge ingest lag and buffer depth percentiles
- stream continuity/reorder/drop counters
