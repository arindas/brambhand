#include <gtest/gtest.h>

#include "brambhand/client/common/runtime_frame.hpp"

TEST(RuntimeFrame, DefaultsAreDeterministic) {
  brambhand::client::common::SimulationFrame frame{};

  EXPECT_EQ(frame.schema_version, 1u);
  EXPECT_EQ(frame.tick_id, 0u);
  EXPECT_DOUBLE_EQ(frame.sim_time_s, 0.0);
  EXPECT_EQ(frame.sequence, 0u);
  EXPECT_TRUE(frame.bodies.empty());
  EXPECT_TRUE(frame.events.empty());
}

TEST(RuntimeFrame, LinkAnchorSymbolIsAvailable) {
  EXPECT_EQ(brambhand::client::common::brambhand_client_link_anchor(), 0);
}
