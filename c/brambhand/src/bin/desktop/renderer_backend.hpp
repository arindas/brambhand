#pragma once

#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <vector>

#include "brambhand/client/common/render_config.hpp"
#include "brambhand/client/common/runtime_frame.hpp"
#include "brambhand/client/desktop/replay_quicklook_workflow.hpp"
#include "renderer_mode.hpp"

namespace brambhand::client::desktop {

struct DesktopReplayFrameStreamState {
  std::mutex mutex;
  ReplayQuicklookWorkflowOutput workflow;
  std::vector<brambhand::client::common::SimulationFrame> frames;
  std::vector<std::string> body_ids;
  bool ingest_complete{false};
  std::size_t version{0};
};

class DesktopReplayRenderer {
 public:
  virtual ~DesktopReplayRenderer() = default;

  [[nodiscard]] virtual DesktopRendererMode mode() const = 0;
  [[nodiscard]] virtual bool run(
      const std::shared_ptr<DesktopReplayFrameStreamState>& stream_state,
      const brambhand::client::common::ReplayRenderConfig& render_config) = 0;
};

[[nodiscard]] std::unique_ptr<DesktopReplayRenderer> create_desktop_replay_renderer(
    DesktopRendererMode mode);

}  // namespace brambhand::client::desktop
