#include "renderer_mode.hpp"

namespace brambhand::client::desktop {

const char* renderer_mode_name(DesktopRendererMode mode) {
  switch (mode) {
    case DesktopRendererMode::Quicklook2D:
      return "quicklook_2d";
    case DesktopRendererMode::Vulkan3D:
      return "vulkan_3d";
  }
  return "unknown";
}

std::optional<DesktopRendererMode> parse_renderer_mode(const std::string& mode) {
  if (mode == "quicklook_2d") {
    return DesktopRendererMode::Quicklook2D;
  }
  if (mode == "vulkan_3d") {
    return DesktopRendererMode::Vulkan3D;
  }
  return std::nullopt;
}

DesktopRendererAvailability renderer_mode_availability(DesktopRendererMode mode) {
  switch (mode) {
    case DesktopRendererMode::Quicklook2D:
      return DesktopRendererAvailability::Available;
    case DesktopRendererMode::Vulkan3D:
      return DesktopRendererAvailability::Planned;
  }
  return DesktopRendererAvailability::Unplanned;
}

RendererModeResolution resolve_renderer_mode(
    DesktopRendererMode requested,
    bool allow_fallback) {
  RendererModeResolution result{};
  result.requested = requested;
  result.effective = requested;

  const auto availability = renderer_mode_availability(requested);
  if (availability == DesktopRendererAvailability::Available) {
    return result;
  }

  if (allow_fallback) {
    result.effective = DesktopRendererMode::Quicklook2D;
    result.used_fallback = true;
    return result;
  }

  if (availability == DesktopRendererAvailability::Planned) {
    result.message =
        "renderer 'vulkan_3d' is planned for R8.5 and not available yet; "
        "use --allow-renderer-fallback to run quicklook_2d for now";
    return result;
  }

  result.message =
      "requested renderer is unavailable and unplanned in current build; "
      "use --renderer quicklook_2d or enable fallback";
  return result;
}

}  // namespace brambhand::client::desktop
