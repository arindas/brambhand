#include "renderer_capability_profile.hpp"

namespace brambhand::client::desktop {
namespace {

class Quicklook2DCapabilityProfile final : public DesktopRendererCapabilityProfile {
 public:
  [[nodiscard]] DesktopRendererMode renderer_mode() const override {
    return DesktopRendererMode::Quicklook2D;
  }

  [[nodiscard]] std::unique_ptr<QuicklookUILayoutPolicy> create_ui_layout_policy() const override {
    return create_default_quicklook_ui_layout_policy();
  }

  [[nodiscard]] std::unique_ptr<QuicklookTracePolicy> create_trace_policy() const override {
    return create_default_quicklook_trace_policy();
  }

  [[nodiscard]] std::unique_ptr<QuicklookSidebarPolicy> create_sidebar_policy() const override {
    return create_default_quicklook_sidebar_policy();
  }
};

class Vulkan3DPlannedCapabilityProfile final : public DesktopRendererCapabilityProfile {
 public:
  [[nodiscard]] DesktopRendererMode renderer_mode() const override {
    return DesktopRendererMode::Vulkan3D;
  }

  [[nodiscard]] std::unique_ptr<QuicklookUILayoutPolicy> create_ui_layout_policy() const override {
    return create_default_quicklook_ui_layout_policy();
  }

  [[nodiscard]] std::unique_ptr<QuicklookTracePolicy> create_trace_policy() const override {
    return create_default_quicklook_trace_policy();
  }

  [[nodiscard]] std::unique_ptr<QuicklookSidebarPolicy> create_sidebar_policy() const override {
    return create_default_quicklook_sidebar_policy();
  }
};

}  // namespace

std::unique_ptr<DesktopRendererCapabilityProfile> create_renderer_capability_profile(
    DesktopRendererMode mode) {
  switch (mode) {
    case DesktopRendererMode::Quicklook2D:
      return std::make_unique<Quicklook2DCapabilityProfile>();
    case DesktopRendererMode::Vulkan3D:
      return std::make_unique<Vulkan3DPlannedCapabilityProfile>();
  }
  return nullptr;
}

}  // namespace brambhand::client::desktop
