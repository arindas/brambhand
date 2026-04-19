#include "quicklook_sidebar_policy.hpp"

namespace brambhand::client::desktop {
namespace {

class DefaultQuicklookSidebarPolicy final : public QuicklookSidebarPolicy {
 public:
  [[nodiscard]] std::string title() const override {
    return "Replay Quicklook";
  }

  [[nodiscard]] std::string simulation_section_title() const override {
    return "Simulation";
  }

  [[nodiscard]] std::string events_section_title() const override {
    return "Mission Events";
  }

  [[nodiscard]] std::string legend_section_title() const override {
    return "Body Legend";
  }

  [[nodiscard]] bool show_events_section() const override {
    return true;
  }

  [[nodiscard]] bool show_legend_section() const override {
    return true;
  }
};

}  // namespace

std::unique_ptr<QuicklookSidebarPolicy> create_default_quicklook_sidebar_policy() {
  return std::make_unique<DefaultQuicklookSidebarPolicy>();
}

}  // namespace brambhand::client::desktop
