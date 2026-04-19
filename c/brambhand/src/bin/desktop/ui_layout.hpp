#pragma once

#include <memory>

namespace brambhand::client::desktop {

struct QuicklookPanelRect {
  float x{};
  float y{};
  float w{};
  float h{};
};

struct QuicklookUIPanels {
  QuicklookPanelRect viewport;
  QuicklookPanelRect sidebar;
};

class QuicklookUILayoutPolicy {
 public:
  virtual ~QuicklookUILayoutPolicy() = default;

  [[nodiscard]] virtual QuicklookUIPanels compute(
      int window_width,
      int window_height) const = 0;
};

[[nodiscard]] std::unique_ptr<QuicklookUILayoutPolicy> create_default_quicklook_ui_layout_policy();

}  // namespace brambhand::client::desktop
