#include "brambhand/client/common/plot_geometry.hpp"

#include <algorithm>
#include <cmath>

namespace brambhand::client::common {

void include_plot_point(PlotBounds& bounds, double x, double y, bool& initialized) {
  if (!initialized) {
    bounds.min_x = x;
    bounds.max_x = x;
    bounds.min_y = y;
    bounds.max_y = y;
    initialized = true;
  }

  bounds.min_x = std::min(bounds.min_x, x);
  bounds.max_x = std::max(bounds.max_x, x);
  bounds.min_y = std::min(bounds.min_y, y);
  bounds.max_y = std::max(bounds.max_y, y);
}

std::optional<PlotBounds> finalize_plot_bounds(
    const PlotBounds& bounds,
    bool initialized,
    double min_span,
    double pad_fraction) {
  if (!initialized) {
    return std::nullopt;
  }

  PlotBounds adjusted = bounds;
  if (std::abs(adjusted.max_x - adjusted.min_x) < 1e-9) {
    adjusted.max_x += min_span;
    adjusted.min_x -= min_span;
  }
  if (std::abs(adjusted.max_y - adjusted.min_y) < 1e-9) {
    adjusted.max_y += min_span;
    adjusted.min_y -= min_span;
  }

  const double pad_x = pad_fraction * (adjusted.max_x - adjusted.min_x);
  const double pad_y = pad_fraction * (adjusted.max_y - adjusted.min_y);
  adjusted.min_x -= pad_x;
  adjusted.max_x += pad_x;
  adjusted.min_y -= pad_y;
  adjusted.max_y += pad_y;
  return adjusted;
}

PlotBounds make_view_bounds(
    const PlotBounds& base,
    double zoom,
    double pan_x,
    double pan_y) {
  const double base_span_x = base.max_x - base.min_x;
  const double base_span_y = base.max_y - base.min_y;
  const double cx = 0.5 * (base.min_x + base.max_x) + pan_x;
  const double cy = 0.5 * (base.min_y + base.max_y) + pan_y;
  const double half_x = 0.5 * base_span_x / zoom;
  const double half_y = 0.5 * base_span_y / zoom;
  return PlotBounds{
      .min_x = cx - half_x,
      .max_x = cx + half_x,
      .min_y = cy - half_y,
      .max_y = cy + half_y,
  };
}

ViewPoint map_plot_point(
    double x,
    double y,
    const PlotBounds& bounds,
    const ViewRect& viewport) {
  const double span_x = bounds.max_x - bounds.min_x;
  const double span_y = bounds.max_y - bounds.min_y;
  const double scale = std::min(viewport.w / span_x, viewport.h / span_y);
  const double center_x = 0.5 * (bounds.min_x + bounds.max_x);
  const double center_y = 0.5 * (bounds.min_y + bounds.max_y);

  return ViewPoint{
      .x = static_cast<float>(viewport.x + (0.5F * viewport.w) + ((x - center_x) * scale)),
      .y = static_cast<float>(viewport.y + (0.5F * viewport.h) - ((y - center_y) * scale)),
  };
}

}  // namespace brambhand::client::common
