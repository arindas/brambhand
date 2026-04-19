#include "replay_ingest_pipeline.hpp"

#include <algorithm>
#include <condition_variable>
#include <deque>
#include <iterator>
#include <mutex>
#include <thread>

namespace brambhand::client::desktop {

DesktopReplayIngestOutput ingest_replay_for_desktop(
    const std::string& replay_path,
    const DesktopReplayIngestOptions& options,
    const DesktopReplayFramesUpdatedCallback& on_frames_updated) {
  DesktopReplayIngestOutput output{};

  if (!options.concurrent) {
    output.report = brambhand::client::common::load_replay_jsonl(replay_path);
    if (output.report.ok() && on_frames_updated) {
      on_frames_updated(output.report.frames, output.report.body_ids);
    }
    return output;
  }

  if (options.chunk_size_frames == 0 || options.queue_max_chunks == 0) {
    output.report.error =
        "concurrent ingest requires positive chunk_size_frames and queue_max_chunks";
    return output;
  }

  struct SharedQueueState {
    std::deque<brambhand::client::common::ReplayIngestChunk> chunks;
    bool ingest_done{false};
  };

  std::mutex queue_mu;
  std::condition_variable queue_cv;
  SharedQueueState queue_state{};
  std::vector<brambhand::client::common::SimulationFrame> streamed_frames;

  std::thread ingest_thread([&]() {
    output.report = brambhand::client::common::load_replay_jsonl_incremental(
        replay_path,
        options.chunk_size_frames,
        [&](brambhand::client::common::ReplayIngestChunk&& chunk) {
          std::unique_lock<std::mutex> lock(queue_mu);
          while (queue_state.chunks.size() >= options.queue_max_chunks) {
            output.telemetry.producer_wait_count += 1;
            queue_cv.wait(lock);
          }

          queue_state.chunks.push_back(std::move(chunk));
          output.telemetry.queue_high_watermark =
              std::max(output.telemetry.queue_high_watermark, queue_state.chunks.size());

          lock.unlock();
          queue_cv.notify_all();
          return true;
        });

    {
      std::lock_guard<std::mutex> lock(queue_mu);
      queue_state.ingest_done = true;
    }
    queue_cv.notify_all();
  });

  while (true) {
    brambhand::client::common::ReplayIngestChunk chunk{};
    {
      std::unique_lock<std::mutex> lock(queue_mu);
      queue_cv.wait(lock, [&]() {
        return queue_state.ingest_done || !queue_state.chunks.empty();
      });

      if (queue_state.chunks.empty() && queue_state.ingest_done) {
        break;
      }

      chunk = std::move(queue_state.chunks.front());
      queue_state.chunks.pop_front();
    }
    queue_cv.notify_all();

    output.telemetry.chunks_processed += 1;
    streamed_frames.insert(
        streamed_frames.end(),
        std::make_move_iterator(chunk.frames.begin()),
        std::make_move_iterator(chunk.frames.end()));

    if (on_frames_updated) {
      on_frames_updated(streamed_frames, chunk.cumulative_body_ids);
    }
  }

  ingest_thread.join();
  return output;
}

}  // namespace brambhand::client::desktop
