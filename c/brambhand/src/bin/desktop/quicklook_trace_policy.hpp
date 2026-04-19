#pragma once

#include <cstdint>
#include <memory>
#include <optional>

namespace brambhand::client::desktop {

class QuicklookTracePolicy {
 public:
  virtual ~QuicklookTracePolicy() = default;

  [[nodiscard]] virtual bool should_draw_segment(
      double step_distance_m,
      std::optional<double> previous_step_distance_m) const = 0;
  [[nodiscard]] virtual std::uint8_t active_trace_alpha() const = 0;
  [[nodiscard]] virtual std::uint8_t dim_trace_alpha() const = 0;
};

[[nodiscard]] std::unique_ptr<QuicklookTracePolicy> create_default_quicklook_trace_policy();

}  // namespace brambhand::client::desktop
