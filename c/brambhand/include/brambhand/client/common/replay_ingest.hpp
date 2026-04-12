#pragma once

#include <string>
#include <vector>

#include "brambhand/client/common/runtime_frame.hpp"

namespace brambhand::client::common {

struct ReplayIngestReport {
  std::vector<SimulationFrame> frames;
  std::string error;

  [[nodiscard]] bool ok() const { return error.empty(); }
};

[[nodiscard]] ReplayIngestReport load_replay_jsonl(const std::string& path);

}  // namespace brambhand::client::common
