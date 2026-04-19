#pragma once

#include <memory>

#include "quicklook_sidebar_policy.hpp"
#include "quicklook_trace_policy.hpp"
#include "renderer_backend.hpp"
#include "ui_layout.hpp"

namespace brambhand::client::desktop {

class DesktopRendererCapabilityProfile {
 public:
  virtual ~DesktopRendererCapabilityProfile() = default;

  [[nodiscard]] virtual DesktopRendererMode renderer_mode() const = 0;
  [[nodiscard]] virtual std::unique_ptr<QuicklookUILayoutPolicy> create_ui_layout_policy() const = 0;
  [[nodiscard]] virtual std::unique_ptr<QuicklookTracePolicy> create_trace_policy() const = 0;
  [[nodiscard]] virtual std::unique_ptr<QuicklookSidebarPolicy> create_sidebar_policy() const = 0;
};

[[nodiscard]] std::unique_ptr<DesktopRendererCapabilityProfile> create_renderer_capability_profile(
    DesktopRendererMode mode);

}  // namespace brambhand::client::desktop
