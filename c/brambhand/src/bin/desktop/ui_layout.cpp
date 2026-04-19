#include "ui_layout.hpp"

#include <algorithm>

namespace brambhand::client::desktop {
namespace {

class DefaultQuicklookUILayoutPolicy final : public QuicklookUILayoutPolicy {
 public:
  [[nodiscard]] QuicklookUIPanels compute(
      int window_width,
      int window_height) const override {
    constexpr float kOuterMargin = 20.0F;
    constexpr float kPanelGap = 10.0F;
    constexpr float kMinViewW = 180.0F;
    constexpr float kPreferredSidebarW = 330.0F;

    float sidebar_w = std::clamp(
        kPreferredSidebarW,
        180.0F,
        std::max(180.0F, static_cast<float>(window_width) - (2.0F * kOuterMargin) - kPanelGap - kMinViewW));
    float viewport_w = static_cast<float>(window_width) - (2.0F * kOuterMargin) - kPanelGap - sidebar_w;
    if (viewport_w < kMinViewW) {
      viewport_w = kMinViewW;
      sidebar_w = std::max(180.0F, static_cast<float>(window_width) - (2.0F * kOuterMargin) - kPanelGap - viewport_w);
    }

    const QuicklookPanelRect viewport{
        .x = kOuterMargin,
        .y = kOuterMargin,
        .w = std::max(120.0F, viewport_w),
        .h = std::max(120.0F, static_cast<float>(window_height) - (2.0F * kOuterMargin)),
    };

    const QuicklookPanelRect sidebar{
        .x = viewport.x + viewport.w + kPanelGap,
        .y = kOuterMargin,
        .w = std::max(140.0F, sidebar_w),
        .h = std::max(120.0F, static_cast<float>(window_height) - (2.0F * kOuterMargin)),
    };

    return QuicklookUIPanels{
        .viewport = viewport,
        .sidebar = sidebar,
    };
  }
};

}  // namespace

std::unique_ptr<QuicklookUILayoutPolicy> create_default_quicklook_ui_layout_policy() {
  return std::make_unique<DefaultQuicklookUILayoutPolicy>();
}

}  // namespace brambhand::client::desktop
