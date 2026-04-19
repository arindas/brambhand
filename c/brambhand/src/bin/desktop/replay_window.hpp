#pragma once

#include "renderer_backend.hpp"

namespace brambhand::client::desktop {

class Quicklook2DReplayRenderer final : public DesktopReplayRenderer {
 public:
  [[nodiscard]] DesktopRendererMode mode() const override;
  [[nodiscard]] bool run(
      const ReplayQuicklookWorkflowOutput& workflow,
      const std::vector<brambhand::client::common::SimulationFrame>& frames,
      const std::vector<std::string>& body_ids,
      const brambhand::client::common::ReplayRenderConfig& render_config) override;
};

}  // namespace brambhand::client::desktop
