#include <filesystem>
#include <fstream>

#include <gtest/gtest.h>

#include "brambhand/client/common/replay_ingest.hpp"

namespace {

std::filesystem::path write_temp_file(const std::string& name, const std::string& content) {
  const auto path = std::filesystem::temp_directory_path() / name;
  std::ofstream out(path);
  out << content;
  return path;
}

}  // namespace

TEST(ReplayIngest, LoadsSimulationFramesFromJsonl) {
  const auto path = write_temp_file(
      "brambhand_replay_ingest_ok.jsonl",
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":10,\"sim_time_s\":1.5,\"sequence\":100,\"bodies\":[{\"body_id\":\"current_vehicle\",\"position_m\":{\"x\":1.0,\"y\":2.0,\"z\":3.0}}]}\n"
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":11,\"sim_time_s\":2.0,\"sequence\":101,\"bodies\":[{\"body_id\":\"planned_vehicle\",\"position_m\":{\"x\":4.0,\"y\":5.0,\"z\":6.0}}]}\n");

  const auto report = brambhand::client::common::load_replay_jsonl(path.string());
  ASSERT_TRUE(report.ok()) << report.error;
  ASSERT_EQ(report.frames.size(), 2u);

  EXPECT_EQ(report.frames[0].run_id, "run-a");
  EXPECT_EQ(report.frames[0].tick_id, 10u);
  EXPECT_DOUBLE_EQ(report.frames[0].sim_time_s, 1.5);
  EXPECT_EQ(report.frames[0].sequence, 100u);

  EXPECT_EQ(report.frames[1].tick_id, 11u);
  EXPECT_EQ(report.frames[1].sequence, 101u);
  ASSERT_EQ(report.frames[0].bodies.size(), 1u);
  EXPECT_EQ(report.frames[0].bodies[0].body_id, "current_vehicle");
  EXPECT_DOUBLE_EQ(report.frames[0].bodies[0].position_m.x, 1.0);
  EXPECT_DOUBLE_EQ(report.frames[0].bodies[0].position_m.y, 2.0);
  EXPECT_DOUBLE_EQ(report.frames[0].bodies[0].position_m.z, 3.0);
}

TEST(ReplayIngest, RejectsNonMonotonicSequence) {
  const auto path = write_temp_file(
      "brambhand_replay_ingest_non_monotonic.jsonl",
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":10,\"sim_time_s\":1.5,\"sequence\":100}\n"
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":11,\"sim_time_s\":2.0,\"sequence\":100}\n");

  const auto report = brambhand::client::common::load_replay_jsonl(path.string());
  EXPECT_FALSE(report.ok());
  EXPECT_TRUE(report.frames.empty());
}

TEST(ReplayIngest, RejectsRunIdMismatch) {
  const auto path = write_temp_file(
      "brambhand_replay_ingest_runid_mismatch.jsonl",
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":10,\"sim_time_s\":1.5,\"sequence\":100}\n"
      "{\"schema_version\":1,\"run_id\":\"run-b\",\"tick_id\":11,\"sim_time_s\":2.0,\"sequence\":101}\n");

  const auto report = brambhand::client::common::load_replay_jsonl(path.string());
  EXPECT_FALSE(report.ok());
  EXPECT_TRUE(report.frames.empty());
}
