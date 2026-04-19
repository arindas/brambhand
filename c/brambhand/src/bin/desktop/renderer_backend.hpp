#pragma once

#include <memory>
#include <optional>
#include <string>
#include <vector>

#include "brambhand/client/common/render_config.hpp"
#include "brambhand/client/common/runtime_frame.hpp"
#include "brambhand/client/desktop/replay_quicklook_workflow.hpp"
#include "renderer_mode.hpp"

namespace brambhand::client::desktop {

class DesktopReplayRenderer {
 public:
  virtual ~DesktopReplayRenderer() = default;

  [[nodiscard]] virtual DesktopRendererMode mode() const = 0;
  [[nodiscard]] virtual bool run(
      const ReplayQuicklookWorkflowOutput& workflow,
      const std::vector<brambhand::client::common::SimulationFrame>& frames,
      const std::vector<std::string>& body_ids,
      const brambhand::client::common::ReplayRenderConfig& render_config) = 0;
};

[[nodiscard]] std::unique_ptr<DesktopReplayRenderer> create_desktop_replay_renderer(
    DesktopRendererMode mode);

}  // namespace brambhand::client::desktop
