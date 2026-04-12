#include <gtest/gtest.h>

#include "brambhand/client/desktop/replay_quicklook_workflow.hpp"

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

brambhand::client::common::EventFrame make_event(
    std::uint64_t sequence,
    double sim_time_s,
    const std::string& kind,
    const std::string& severity) {
  brambhand::client::common::EventFrame event{};
  event.sequence = sequence;
  event.sim_time_s = sim_time_s;
  event.kind = kind;
  event.severity = severity;
  return event;
}

brambhand::client::common::SimulationFrame make_frame(
    std::uint64_t sequence,
    std::initializer_list<brambhand::client::common::BodyState> bodies,
    std::initializer_list<brambhand::client::common::EventFrame> events) {
  brambhand::client::common::SimulationFrame frame{};
  frame.schema_version = 1;
  frame.run_id = "run-a";
  frame.tick_id = sequence;
  frame.sequence = sequence;
  frame.sim_time_s = static_cast<double>(sequence);
  frame.bodies.assign(bodies.begin(), bodies.end());
  frame.events.assign(events.begin(), events.end());
  return frame;
}

}  // namespace

TEST(ReplayQuicklookWorkflow, BuildsTrajectoryAndDeterministicEventOrdering) {
  const std::vector<brambhand::client::common::SimulationFrame> frames = {
      make_frame(
          10,
          {make_body("current_vehicle", 1.0, 2.0, 0.0), make_body("planned_vehicle", 3.0, 4.0, 0.0)},
          {make_event(300, 3.0, "alarm_raised", "critical"),
           make_event(200, 2.0, "step_completed", "info")}),
      make_frame(
          11,
          {make_body("current_vehicle", 2.0, 3.0, 0.0), make_body("planned_vehicle", 5.0, 6.0, 0.0)},
          {make_event(250, 2.5, "threshold_crossed", "warning")}),
  };

  const auto output = brambhand::client::desktop::build_replay_quicklook_workflow(frames);

  ASSERT_EQ(output.trajectory_panel.curve_layers.size(), 2u);
  ASSERT_EQ(output.trajectory_panel.object_icons.size(), 2u);

  ASSERT_EQ(output.event_markers.size(), 3u);
  EXPECT_EQ(output.event_markers[0].sequence, 200u);
  EXPECT_EQ(output.event_markers[1].sequence, 250u);
  EXPECT_EQ(output.event_markers[2].sequence, 300u);

  EXPECT_EQ(output.event_markers[0].color_hex, "#4DA3FF");
  EXPECT_EQ(output.event_markers[1].color_hex, "#FFC107");
  EXPECT_EQ(output.event_markers[2].color_hex, "#FF4D4D");
}
