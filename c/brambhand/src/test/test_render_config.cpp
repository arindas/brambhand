#include <filesystem>
#include <fstream>

#include <gtest/gtest.h>

#include "brambhand/client/common/render_config.hpp"

namespace {

std::filesystem::path write_temp_file(const std::string& name, const std::string& content) {
  const auto path = std::filesystem::temp_directory_path() / name;
  std::ofstream out(path);
  out << content;
  return path;
}

}  // namespace

TEST(RenderConfig, LoadsDimTrajectoryIdsAndFocusBody) {
  const auto path = write_temp_file(
      "brambhand_render_config_ok.json",
      "{\"schema_version\":1,\"dim_trajectory_body_ids\":[\"sun\",\"earth\",\"mars\"],\"focus_body_id\":\"sun\",\"sun_body_ids\":[\"sun\"],\"planet_body_ids\":[\"earth\",\"mars\"],\"probe_body_ids\":[\"mars_probe\"]}");

  const auto report = brambhand::client::common::load_replay_render_config_json(path.string());
  ASSERT_TRUE(report.ok()) << report.error;
  EXPECT_EQ(report.config.schema_version, 1u);
  ASSERT_EQ(report.config.dim_trajectory_body_ids.size(), 3u);
  EXPECT_EQ(report.config.dim_trajectory_body_ids[0], "sun");
  EXPECT_EQ(report.config.dim_trajectory_body_ids[1], "earth");
  EXPECT_EQ(report.config.dim_trajectory_body_ids[2], "mars");
  ASSERT_TRUE(report.config.focus_body_id.has_value());
  EXPECT_EQ(*report.config.focus_body_id, "sun");
  ASSERT_EQ(report.config.sun_body_ids.size(), 1u);
  ASSERT_EQ(report.config.planet_body_ids.size(), 2u);
  ASSERT_EQ(report.config.probe_body_ids.size(), 1u);
  EXPECT_EQ(report.config.sun_body_ids[0], "sun");
  EXPECT_EQ(report.config.planet_body_ids[0], "earth");
  EXPECT_EQ(report.config.probe_body_ids[0], "mars_probe");
}

TEST(RenderConfig, RejectsMissingDimTrajectoryIds) {
  const auto path = write_temp_file(
      "brambhand_render_config_missing_dim_ids.json",
      "{\"schema_version\":1,\"focus_body_id\":\"sun\"}");

  const auto report = brambhand::client::common::load_replay_render_config_json(path.string());
  EXPECT_FALSE(report.ok());
}
