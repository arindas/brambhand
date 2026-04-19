#include <gtest/gtest.h>

#include "brambhand/client/common/plot_geometry.hpp"

TEST(PlotGeometry, BoundsFinalizeAndMapPoint) {
  brambhand::client::common::PlotBounds bounds{};
  bool initialized = false;

  brambhand::client::common::include_plot_point(bounds, -10.0, -5.0, initialized);
  brambhand::client::common::include_plot_point(bounds, 20.0, 15.0, initialized);

  const auto finalized = brambhand::client::common::finalize_plot_bounds(bounds, initialized);
  ASSERT_TRUE(finalized.has_value());

  const auto view = brambhand::client::common::make_view_bounds(*finalized, 1.0, 0.0, 0.0);
  const auto mapped = brambhand::client::common::map_plot_point(
      0.0,
      0.0,
      view,
      brambhand::client::common::ViewRect{.x = 0.0F, .y = 0.0F, .w = 100.0F, .h = 100.0F});

  EXPECT_GE(mapped.x, 0.0F);
  EXPECT_LE(mapped.x, 100.0F);
  EXPECT_GE(mapped.y, 0.0F);
  EXPECT_LE(mapped.y, 100.0F);
}
