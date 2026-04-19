#include <iterator>

#include <gtest/gtest.h>

#include "brambhand/client/common/desktop_cli_options.hpp"

TEST(DesktopCliOptions, ParsesRequiredAndOptionalFlags) {
  const char* argv[] = {
      "brambhand_desktop",
      "--replay",
      "demo.jsonl",
      "--render-config",
      "demo.render.json",
      "--renderer",
      "quicklook_2d",
      "--allow-renderer-fallback",
      "--concurrent-ingest",
      "--ingest-chunk-frames",
      "16",
      "--ingest-queue-max-chunks",
      "3",
      "--no-window",
      "--strict-render-config",
  };

  const auto report = brambhand::client::common::parse_desktop_cli_options(
      static_cast<int>(std::size(argv)),
      const_cast<char**>(argv));

  ASSERT_TRUE(report.ok()) << report.error;
  ASSERT_TRUE(report.options.replay_path.has_value());
  ASSERT_TRUE(report.options.render_config_path.has_value());
  EXPECT_EQ(*report.options.replay_path, "demo.jsonl");
  EXPECT_EQ(*report.options.render_config_path, "demo.render.json");
  EXPECT_EQ(report.options.renderer_mode_arg, "quicklook_2d");
  EXPECT_TRUE(report.options.allow_renderer_fallback);
  EXPECT_TRUE(report.options.concurrent_ingest);
  EXPECT_EQ(report.options.ingest_chunk_frames, 16u);
  EXPECT_EQ(report.options.ingest_queue_max_chunks, 3u);
  EXPECT_TRUE(report.options.no_window);
  EXPECT_TRUE(report.options.strict_render_config);
}

TEST(DesktopCliOptions, RejectsUnknownFlag) {
  const char* argv[] = {
      "brambhand_desktop",
      "--replay",
      "demo.jsonl",
      "--render-config",
      "demo.render.json",
      "--wat",
  };

  const auto report = brambhand::client::common::parse_desktop_cli_options(
      static_cast<int>(std::size(argv)),
      const_cast<char**>(argv));

  EXPECT_FALSE(report.ok());
  EXPECT_NE(report.error.find("unsupported argument"), std::string::npos);
}

TEST(DesktopCliOptions, RejectsInvalidNumericValue) {
  const char* argv[] = {
      "brambhand_desktop",
      "--replay",
      "demo.jsonl",
      "--render-config",
      "demo.render.json",
      "--ingest-chunk-frames",
      "abc",
  };

  const auto report = brambhand::client::common::parse_desktop_cli_options(
      static_cast<int>(std::size(argv)),
      const_cast<char**>(argv));

  EXPECT_FALSE(report.ok());
  EXPECT_NE(report.error.find("invalid numeric value"), std::string::npos);
}
