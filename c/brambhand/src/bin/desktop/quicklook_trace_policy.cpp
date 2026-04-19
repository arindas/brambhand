#include "quicklook_trace_policy.hpp"

#include <algorithm>

namespace brambhand::client::desktop {
namespace {

class DefaultQuicklookTracePolicy final : public QuicklookTracePolicy {
 public:
  [[nodiscard]] bool should_draw_segment(
      double step_distance_m,
      std::optional<double> previous_step_distance_m) const override {
    constexpr double kJumpDiscontinuityFactor = 6.0;
    constexpr double kMinReferenceDistanceM = 1.0;

    if (!previous_step_distance_m.has_value()) {
      return true;
    }

    const double reference_m = std::max(*previous_step_distance_m, kMinReferenceDistanceM);
    return step_distance_m <= (kJumpDiscontinuityFactor * reference_m);
  }

  [[nodiscard]] std::uint8_t active_trace_alpha() const override {
    return 180;
  }

  [[nodiscard]] std::uint8_t dim_trace_alpha() const override {
    return 85;
  }
};

}  // namespace

std::unique_ptr<QuicklookTracePolicy> create_default_quicklook_trace_policy() {
  return std::make_unique<DefaultQuicklookTracePolicy>();
}

}  // namespace brambhand::client::desktop
