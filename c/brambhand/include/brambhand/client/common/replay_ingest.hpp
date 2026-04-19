#pragma once

#include <cstdint>
#include <functional>
#include <string>
#include <vector>

#include "brambhand/client/common/runtime_frame.hpp"

namespace brambhand::client::common {

struct ReplayIngestReport {
  std::vector<SimulationFrame> frames;
  std::vector<std::string> body_ids;
  std::string error;

  [[nodiscard]] bool ok() const { return error.empty(); }
};

struct ReplayIngestChunk {
  std::uint64_t chunk_index{};
  std::uint64_t lines_processed{};
  bool is_final_chunk{false};
  std::vector<SimulationFrame> frames;
  std::vector<std::string> cumulative_body_ids;
};

using ReplayIngestChunkCallback = std::function<bool(ReplayIngestChunk&& chunk)>;

[[nodiscard]] ReplayIngestReport load_replay_jsonl(const std::string& path);

[[nodiscard]] ReplayIngestReport load_replay_jsonl_incremental(
    const std::string& path,
    std::size_t chunk_size_frames,
    const ReplayIngestChunkCallback& on_chunk);

}  // namespace brambhand::client::common
