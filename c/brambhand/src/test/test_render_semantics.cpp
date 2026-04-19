#include <gtest/gtest.h>

#include "brambhand/client/common/render_semantics.hpp"

TEST(RenderSemantics, MapsConfiguredRolesAndDimTrajectoryMembership) {
  brambhand::client::common::ReplayRenderConfig config{};
  config.dim_trajectory_body_ids = {"sun", "earth", "mars"};
  config.sun_body_ids = {"sun"};
  config.planet_body_ids = {"earth", "mars"};
  config.probe_body_ids = {"probe"};

  const auto semantics = brambhand::client::common::create_replay_render_semantics(config);

  EXPECT_TRUE(semantics->is_dim_trajectory_body("earth"));
  EXPECT_FALSE(semantics->is_dim_trajectory_body("probe"));

  EXPECT_EQ(semantics->role_for("sun"), brambhand::client::common::BodyRenderRole::Sun);
  EXPECT_EQ(semantics->role_for("earth"), brambhand::client::common::BodyRenderRole::Planet);
  EXPECT_EQ(semantics->role_for("probe"), brambhand::client::common::BodyRenderRole::Probe);
  EXPECT_EQ(semantics->role_for("unknown"), brambhand::client::common::BodyRenderRole::Generic);
}
