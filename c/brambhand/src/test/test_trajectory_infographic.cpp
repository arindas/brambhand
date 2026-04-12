#include <gtest/gtest.h>

#include "brambhand/client/desktop/trajectory_infographic.hpp"

namespace {

brambhand::client::common::BodyState make_body(
    const std::string& id,
    double x,
    double y,
    double z) {
  brambhand::client::common::BodyState body{};
  body.body_id = id;
  body.position_m = brambhand::client::common::Vector3{.x = x, .y = y, .z = z};
  return body;
}

brambhand::client::common::SimulationFrame make_frame(
    std::uint64_t sequence,
    std::initializer_list<brambhand::client::common::BodyState> bodies) {
  brambhand::client::common::SimulationFrame frame{};
  frame.schema_version = 1;
  frame.run_id = "run-a";
  frame.tick_id = sequence;
  frame.sequence = sequence;
  frame.sim_time_s = static_cast<double>(sequence);
  frame.bodies.assign(bodies.begin(), bodies.end());
  return frame;
}

}  // namespace

TEST(TrajectoryInfographic, BuildsCurrentAndPlannedLayersAndIcons) {
  const std::vector<brambhand::client::common::SimulationFrame> frames = {
      make_frame(10, {make_body("current_vehicle", 1.0, 2.0, 0.0),
                      make_body("planned_vehicle", 3.0, 4.0, 0.0)}),
      make_frame(11, {make_body("current_vehicle", 2.0, 3.0, 0.0),
                      make_body("planned_vehicle", 5.0, 6.0, 0.0)}),
  };

  const auto panel = brambhand::client::desktop::build_trajectory_infographic_panel(frames);

  ASSERT_EQ(panel.schema_version, brambhand::client::desktop::kTrajectoryInfographicSchemaVersion);
  ASSERT_EQ(panel.curve_layers.size(), 2u);
  EXPECT_EQ(panel.curve_layers[0].name, "current_trajectory");
  EXPECT_EQ(panel.curve_layers[1].name, "planned_trajectory");
  ASSERT_EQ(panel.curve_layers[0].points.size(), 2u);
  ASSERT_EQ(panel.curve_layers[1].points.size(), 2u);
  EXPECT_DOUBLE_EQ(panel.curve_layers[0].points.back().x_m, 2.0);
  EXPECT_DOUBLE_EQ(panel.curve_layers[0].points.back().y_m, 3.0);
  EXPECT_DOUBLE_EQ(panel.curve_layers[1].points.back().x_m, 5.0);
  EXPECT_DOUBLE_EQ(panel.curve_layers[1].points.back().y_m, 6.0);

  ASSERT_EQ(panel.object_icons.size(), 2u);
  EXPECT_EQ(panel.object_icons[0].name, "current_vehicle");
  EXPECT_EQ(panel.object_icons[0].icon, "ship");
  EXPECT_EQ(panel.object_icons[1].name, "planned_vehicle");
  EXPECT_EQ(panel.object_icons[1].icon, "ghost_ship");
}

TEST(TrajectoryInfographic, FallsBackToFirstBodyForCurrentLayer) {
  const std::vector<brambhand::client::common::SimulationFrame> frames = {
      make_frame(20, {make_body("vehicle_a", 9.0, 1.0, 0.0)}),
  };

  const auto panel = brambhand::client::desktop::build_trajectory_infographic_panel(frames);

  ASSERT_EQ(panel.curve_layers.size(), 2u);
  ASSERT_EQ(panel.curve_layers[0].points.size(), 1u);
  EXPECT_DOUBLE_EQ(panel.curve_layers[0].points[0].x_m, 9.0);
  EXPECT_DOUBLE_EQ(panel.curve_layers[0].points[0].y_m, 1.0);
  EXPECT_TRUE(panel.curve_layers[1].points.empty());
  ASSERT_EQ(panel.object_icons.size(), 1u);
  EXPECT_EQ(panel.object_icons[0].name, "current_vehicle");
}
