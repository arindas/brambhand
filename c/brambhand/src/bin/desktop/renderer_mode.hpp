#pragma once

#include <optional>
#include <string>

namespace brambhand::client::desktop {

enum class DesktopRendererMode {
  Quicklook2D,
  Vulkan3D,
};

enum class DesktopRendererAvailability {
  Available,
  Planned,
  Unplanned,
};

[[nodiscard]] const char* renderer_mode_name(DesktopRendererMode mode);
[[nodiscard]] std::optional<DesktopRendererMode> parse_renderer_mode(const std::string& mode);
[[nodiscard]] DesktopRendererAvailability renderer_mode_availability(DesktopRendererMode mode);

struct RendererModeResolution {
  DesktopRendererMode requested{DesktopRendererMode::Quicklook2D};
  DesktopRendererMode effective{DesktopRendererMode::Quicklook2D};
  bool used_fallback{false};
  std::string message;

  [[nodiscard]] bool ok() const { return message.empty(); }
};

[[nodiscard]] RendererModeResolution resolve_renderer_mode(
    DesktopRendererMode requested,
    bool allow_fallback);

}  // namespace brambhand::client::desktop
