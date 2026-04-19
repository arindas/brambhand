#pragma once

#include <cstddef>
#include <functional>
#include <string>
#include <vector>

#include "brambhand/client/common/replay_ingest.hpp"
#include "brambhand/client/common/runtime_frame.hpp"

namespace brambhand::client::desktop {

struct DesktopReplayIngestOptions {
  bool concurrent{false};
  std::size_t chunk_size_frames{256};
  std::size_t queue_max_chunks{8};
};

struct DesktopReplayIngestTelemetry {
  std::size_t chunks_processed{};
  std::size_t queue_high_watermark{};
  std::size_t producer_wait_count{};
};

using DesktopReplayFramesUpdatedCallback =
    std::function<void(
        const std::vector<brambhand::client::common::SimulationFrame>& frames,
        const std::vector<std::string>& body_ids)>;

struct DesktopReplayIngestOutput {
  brambhand::client::common::ReplayIngestReport report;
  DesktopReplayIngestTelemetry telemetry;
};

[[nodiscard]] DesktopReplayIngestOutput ingest_replay_for_desktop(
    const std::string& replay_path,
    const DesktopReplayIngestOptions& options,
    const DesktopReplayFramesUpdatedCallback& on_frames_updated);

}  // namespace brambhand::client::desktop
