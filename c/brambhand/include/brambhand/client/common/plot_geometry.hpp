#pragma once

#include <optional>

namespace brambhand::client::common {

struct alignas(32) PlotBounds {
  double min_x{};
  double max_x{};
  double min_y{};
  double max_y{};
};

struct alignas(16) ViewRect {
  float x{};
  float y{};
  float w{};
  float h{};
};

struct alignas(8) ViewPoint {
  float x{};
  float y{};
};

void include_plot_point(PlotBounds& bounds, double x, double y, bool& initialized);

std::optional<PlotBounds> finalize_plot_bounds(
    const PlotBounds& bounds,
    bool initialized,
    double min_span = 1.0,
    double pad_fraction = 0.08);

[[nodiscard]] PlotBounds make_view_bounds(
    const PlotBounds& base,
    double zoom,
    double pan_x,
    double pan_y);

[[nodiscard]] ViewPoint map_plot_point(
    double x,
    double y,
    const PlotBounds& bounds,
    const ViewRect& viewport);

static_assert(sizeof(PlotBounds) == 32, "PlotBounds should remain 32 bytes");
static_assert(sizeof(ViewRect) == 16, "ViewRect should remain 16 bytes");
static_assert(sizeof(ViewPoint) == 8, "ViewPoint should remain 8 bytes");

}  // namespace brambhand::client::common
