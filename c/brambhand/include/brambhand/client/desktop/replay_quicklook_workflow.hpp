#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "brambhand/client/common/runtime_frame.hpp"
#include "brambhand/client/desktop/trajectory_infographic.hpp"

namespace brambhand::client::desktop {

struct QuicklookEventMarker {
  std::uint64_t sequence{};
  double sim_time_s{};
  std::string kind;
  std::string severity;
  std::string color_hex;
};

struct ReplayQuicklookWorkflowOutput {
  TrajectoryInfographicPanel trajectory_panel;
  std::vector<QuicklookEventMarker> event_markers;
};

[[nodiscard]] ReplayQuicklookWorkflowOutput build_replay_quicklook_workflow(
    const std::vector<brambhand::client::common::SimulationFrame>& frames);

}  // namespace brambhand::client::desktop
