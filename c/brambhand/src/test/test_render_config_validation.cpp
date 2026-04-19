#include <gtest/gtest.h>

#include "../bin/desktop/render_config_validation.hpp"

TEST(RenderConfigValidation, DetectsMissingConfiguredBodyIds) {
  brambhand::client::common::ReplayRenderConfig config{};
  config.dim_trajectory_body_ids = {"sun", "earth", "mars"};
  config.sun_body_ids = {"sun"};
  config.planet_body_ids = {"earth", "mars"};
  config.probe_body_ids = {"probe_a"};
  config.focus_body_id = "sun";

  const std::vector<std::string> replay_ids = {"sun", "earth"};

  const auto result = brambhand::client::desktop::validate_replay_render_config_body_ids(
      config,
      replay_ids);

  ASSERT_TRUE(result.has_missing());
  EXPECT_EQ(result.missing_dim_ids, (std::vector<std::string>{"mars"}));
  EXPECT_TRUE(result.missing_sun_ids.empty());
  EXPECT_EQ(result.missing_planet_ids, (std::vector<std::string>{"mars"}));
  EXPECT_EQ(result.missing_probe_ids, (std::vector<std::string>{"probe_a"}));
  EXPECT_FALSE(result.missing_focus_id);
}

TEST(RenderConfigValidation, AcceptsCompleteBodyCatalog) {
  brambhand::client::common::ReplayRenderConfig config{};
  config.dim_trajectory_body_ids = {"sun", "earth", "mars"};
  config.sun_body_ids = {"sun"};
  config.planet_body_ids = {"earth", "mars"};
  config.probe_body_ids = {"probe_a"};
  config.focus_body_id = "probe_a";

  const std::vector<std::string> replay_ids = {"sun", "earth", "mars", "probe_a"};

  const auto result = brambhand::client::desktop::validate_replay_render_config_body_ids(
      config,
      replay_ids);

  EXPECT_FALSE(result.has_missing());
  EXPECT_TRUE(result.missing_dim_ids.empty());
  EXPECT_TRUE(result.missing_sun_ids.empty());
  EXPECT_TRUE(result.missing_planet_ids.empty());
  EXPECT_TRUE(result.missing_probe_ids.empty());
  EXPECT_FALSE(result.missing_focus_id);
}
