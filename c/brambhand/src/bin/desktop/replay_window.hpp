#pragma once

#include "renderer_backend.hpp"

namespace brambhand::client::desktop {

class Quicklook2DReplayRenderer final : public DesktopReplayRenderer {
 public:
  [[nodiscard]] DesktopRendererMode mode() const override;
  [[nodiscard]] bool run(
      const std::shared_ptr<DesktopReplayFrameStreamState>& stream_state,
      const brambhand::client::common::ReplayRenderConfig& render_config) override;
};

}  // namespace brambhand::client::desktop
