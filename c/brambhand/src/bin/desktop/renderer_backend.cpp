#include "renderer_backend.hpp"

#include "replay_window.hpp"

namespace brambhand::client::desktop {
namespace {

class Vulkan3DReplayRenderer final : public DesktopReplayRenderer {
 public:
  [[nodiscard]] DesktopRendererMode mode() const override {
    return DesktopRendererMode::Vulkan3D;
  }

  [[nodiscard]] bool run(
      const ReplayQuicklookWorkflowOutput&,
      const std::vector<brambhand::client::common::SimulationFrame>&,
      const std::vector<std::string>&,
      const brambhand::client::common::ReplayRenderConfig&) override {
    return false;
  }
};

}  // namespace

std::unique_ptr<DesktopReplayRenderer> create_desktop_replay_renderer(DesktopRendererMode mode) {
  switch (mode) {
    case DesktopRendererMode::Quicklook2D:
      return std::make_unique<Quicklook2DReplayRenderer>();
    case DesktopRendererMode::Vulkan3D:
      return std::make_unique<Vulkan3DReplayRenderer>();
  }
  return nullptr;
}

}  // namespace brambhand::client::desktop
