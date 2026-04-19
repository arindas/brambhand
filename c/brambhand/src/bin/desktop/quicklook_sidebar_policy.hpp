#pragma once

#include <memory>
#include <string>

namespace brambhand::client::desktop {

class QuicklookSidebarPolicy {
 public:
  virtual ~QuicklookSidebarPolicy() = default;

  [[nodiscard]] virtual std::string title() const = 0;
  [[nodiscard]] virtual std::string simulation_section_title() const = 0;
  [[nodiscard]] virtual std::string events_section_title() const = 0;
  [[nodiscard]] virtual std::string legend_section_title() const = 0;
  [[nodiscard]] virtual bool show_events_section() const = 0;
  [[nodiscard]] virtual bool show_legend_section() const = 0;
};

[[nodiscard]] std::unique_ptr<QuicklookSidebarPolicy> create_default_quicklook_sidebar_policy();

}  // namespace brambhand::client::desktop
