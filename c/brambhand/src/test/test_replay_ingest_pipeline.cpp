#include <chrono>
#include <filesystem>
#include <fstream>
#include <thread>

#include <gtest/gtest.h>

#include "brambhand/client/common/replay_ingest.hpp"
#include "brambhand/client/desktop/replay_quicklook_workflow.hpp"
#include "../bin/desktop/replay_ingest_pipeline.hpp"

namespace {

std::filesystem::path write_temp_file(const std::string& name, const std::string& content) {
  const auto path = std::filesystem::temp_directory_path() / name;
  std::ofstream out(path);
  out << content;
  return path;
}

}  // namespace

TEST(ReplayIngestPipeline, ConcurrentIngestMatchesSequentialOrdering) {
  std::string jsonl;
  jsonl.reserve(4096);
  for (int i = 0; i < 30; ++i) {
    std::string catalog = "{\"schema_version\":1";
    if (i == 0) {
      catalog += ",\"initial_body_ids\":[\"probe\"]";
    }
    catalog += ",\"created_body_ids\":[],\"destroyed_body_ids\":[]}";

    jsonl +=
        "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":" + std::to_string(i) +
        ",\"sim_time_s\":" + std::to_string(0.25 * static_cast<double>(i)) +
        ",\"sequence\":" + std::to_string(100 + i) +
        ",\"body_id_catalog\":" + catalog +
        ",\"bodies\":[{\"body_id\":\"probe\",\"position_m\":{\"x\":" + std::to_string(i) +
        ",\"y\":0.0,\"z\":0.0}}],\"events\":[{\"sequence\":" +
        std::to_string(500 + i) +
        ",\"sim_time_s\":0.0,\"kind\":\"step_completed\",\"severity\":\"info\"}]}\n";
  }

  const auto path = write_temp_file("brambhand_replay_ingest_pipeline_concurrent.jsonl", jsonl);

  const auto baseline = brambhand::client::common::load_replay_jsonl(path.string());
  ASSERT_TRUE(baseline.ok()) << baseline.error;
  const auto baseline_workflow =
      brambhand::client::desktop::build_replay_quicklook_workflow(baseline.frames);

  std::size_t callback_count = 0;
  auto output = brambhand::client::desktop::ingest_replay_for_desktop(
      path.string(),
      brambhand::client::desktop::DesktopReplayIngestOptions{
          .concurrent = true,
          .chunk_size_frames = 4,
          .queue_max_chunks = 1,
      },
      [&](const std::vector<brambhand::client::common::SimulationFrame>& frames,
          const std::vector<std::string>& body_ids) {
        callback_count += 1;
        EXPECT_FALSE(body_ids.empty());
        (void)brambhand::client::desktop::build_replay_quicklook_workflow(frames);
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      });

  ASSERT_TRUE(output.report.ok()) << output.report.error;
  ASSERT_EQ(output.report.frames.size(), baseline.frames.size());

  for (std::size_t i = 0; i < output.report.frames.size(); ++i) {
    EXPECT_EQ(output.report.frames[i].sequence, baseline.frames[i].sequence);
    EXPECT_EQ(output.report.frames[i].tick_id, baseline.frames[i].tick_id);
  }

  const auto workflow = brambhand::client::desktop::build_replay_quicklook_workflow(output.report.frames);
  ASSERT_EQ(workflow.event_markers.size(), baseline_workflow.event_markers.size());
  for (std::size_t i = 0; i < workflow.event_markers.size(); ++i) {
    EXPECT_EQ(workflow.event_markers[i].sequence, baseline_workflow.event_markers[i].sequence);
  }

  EXPECT_GT(callback_count, 0u);
  EXPECT_GT(output.telemetry.chunks_processed, 0u);
  EXPECT_EQ(output.telemetry.queue_high_watermark, 1u);
}

TEST(ReplayIngestPipeline, RejectsInvalidConcurrentSizing) {
  const auto output = brambhand::client::desktop::ingest_replay_for_desktop(
      "/tmp/does-not-matter.jsonl",
      brambhand::client::desktop::DesktopReplayIngestOptions{
          .concurrent = true,
          .chunk_size_frames = 0,
          .queue_max_chunks = 1,
      },
      brambhand::client::desktop::DesktopReplayFramesUpdatedCallback{});

  EXPECT_FALSE(output.report.ok());
  EXPECT_NE(output.report.error.find("positive"), std::string::npos);
}
