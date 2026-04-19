#include <chrono>
#include <cstddef>
#include <iostream>
#include <limits>
#include <thread>
#include <vector>

#include "brambhand/client/desktop/replay_quicklook_workflow.hpp"
#include "replay_ingest_benchmark_options.hpp"
#include "replay_ingest_pipeline.hpp"

namespace {

struct SampleRow {
  std::string mode;
  std::size_t chunk_frames{};
  std::size_t queue_max_chunks{};
  std::size_t iteration{};
  double elapsed_ms{};
  std::size_t chunks_processed{};
  std::size_t queue_high_watermark{};
  std::size_t producer_wait_count{};
  std::size_t frame_count{};
};

}  // namespace

int main(int argc, char** argv) {
  const auto opts_report =
      brambhand::client::desktop::parse_replay_ingest_benchmark_options(argc, argv);
  if (!opts_report.ok()) {
    std::cerr << opts_report.error << "\n";
    std::cerr << brambhand::client::desktop::replay_ingest_benchmark_usage() << "\n";
    return 2;
  }

  const auto& opts = opts_report.options;
  if (opts.show_help) {
    std::cout << brambhand::client::desktop::replay_ingest_benchmark_usage() << "\n";
    return 0;
  }

  std::vector<SampleRow> rows;

  if (opts.include_sequential_baseline) {
    for (std::size_t i = 0; i < opts.iterations; ++i) {
      const auto t0 = std::chrono::steady_clock::now();
      const auto output = brambhand::client::desktop::ingest_replay_for_desktop(
          opts.replay_path,
          brambhand::client::desktop::DesktopReplayIngestOptions{
              .concurrent = false,
              .chunk_size_frames = 256,
              .queue_max_chunks = 8,
          },
          brambhand::client::desktop::DesktopReplayFramesUpdatedCallback{});
      const auto t1 = std::chrono::steady_clock::now();

      if (!output.report.ok()) {
        std::cerr << "sequential ingest failed: " << output.report.error << "\n";
        return 1;
      }

      (void)brambhand::client::desktop::build_replay_quicklook_workflow(output.report.frames);

      rows.push_back(SampleRow{
          .mode = "sequential",
          .chunk_frames = 0,
          .queue_max_chunks = 0,
          .iteration = i + 1,
          .elapsed_ms = std::chrono::duration<double, std::milli>(t1 - t0).count(),
          .chunks_processed = output.telemetry.chunks_processed,
          .queue_high_watermark = output.telemetry.queue_high_watermark,
          .producer_wait_count = output.telemetry.producer_wait_count,
          .frame_count = output.report.frames.size(),
      });
    }
  }

  for (const auto chunk_frames : opts.chunk_frames_candidates) {
    for (const auto queue_max_chunks : opts.queue_max_chunks_candidates) {
      for (std::size_t i = 0; i < opts.iterations; ++i) {
        const auto t0 = std::chrono::steady_clock::now();
        const auto output = brambhand::client::desktop::ingest_replay_for_desktop(
            opts.replay_path,
            brambhand::client::desktop::DesktopReplayIngestOptions{
                .concurrent = true,
                .chunk_size_frames = chunk_frames,
                .queue_max_chunks = queue_max_chunks,
            },
            brambhand::client::desktop::DesktopReplayFramesUpdatedCallback{
                [&opts](
                    const std::vector<brambhand::client::common::SimulationFrame>& frames,
                    const std::vector<std::string>&) {
                  (void)brambhand::client::desktop::build_replay_quicklook_workflow(frames);
                  if (opts.consumer_delay_ms > 0) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(opts.consumer_delay_ms));
                  }
                }});
        const auto t1 = std::chrono::steady_clock::now();

        if (!output.report.ok()) {
          std::cerr << "concurrent ingest failed (chunk=" << chunk_frames
                    << ", queue=" << queue_max_chunks
                    << "): " << output.report.error << "\n";
          return 1;
        }

        rows.push_back(SampleRow{
            .mode = "concurrent",
            .chunk_frames = chunk_frames,
            .queue_max_chunks = queue_max_chunks,
            .iteration = i + 1,
            .elapsed_ms = std::chrono::duration<double, std::milli>(t1 - t0).count(),
            .chunks_processed = output.telemetry.chunks_processed,
            .queue_high_watermark = output.telemetry.queue_high_watermark,
            .producer_wait_count = output.telemetry.producer_wait_count,
            .frame_count = output.report.frames.size(),
        });
      }
    }
  }

  std::cout << "mode,chunk_frames,queue_max_chunks,iteration,elapsed_ms,chunks_processed,queue_high_watermark,producer_wait_count,frame_count\n";
  for (const auto& row : rows) {
    std::cout << row.mode << ","
              << row.chunk_frames << ","
              << row.queue_max_chunks << ","
              << row.iteration << ","
              << row.elapsed_ms << ","
              << row.chunks_processed << ","
              << row.queue_high_watermark << ","
              << row.producer_wait_count << ","
              << row.frame_count << "\n";
  }

  double best_elapsed_ms = std::numeric_limits<double>::max();
  std::size_t best_chunk_frames = 0;
  std::size_t best_queue_max_chunks = 0;
  bool found_best = false;
  for (const auto& row : rows) {
    if (row.mode != "concurrent") {
      continue;
    }
    if (row.elapsed_ms < best_elapsed_ms) {
      best_elapsed_ms = row.elapsed_ms;
      best_chunk_frames = row.chunk_frames;
      best_queue_max_chunks = row.queue_max_chunks;
      found_best = true;
    }
  }

  if (found_best) {
    std::cerr << "best_concurrent_pair chunk_frames=" << best_chunk_frames
              << " queue_max_chunks=" << best_queue_max_chunks
              << " elapsed_ms=" << best_elapsed_ms << "\n";
  }

  return 0;
}
