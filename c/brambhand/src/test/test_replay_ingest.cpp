#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <mutex>
#include <sstream>
#include <thread>

#include <gtest/gtest.h>

#include "brambhand/client/common/replay_ingest.hpp"
#include "brambhand/client/desktop/replay_quicklook_workflow.hpp"

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
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":10,\"sim_time_s\":1.5,\"sequence\":100,\"body_id_catalog\":{\"schema_version\":1,\"initial_body_ids\":[\"current_vehicle\",\"planned_vehicle\"],\"created_body_ids\":[],\"destroyed_body_ids\":[]},\"bodies\":[{\"body_id\":\"current_vehicle\",\"visualization_role\":\"vehicle\",\"position_m\":{\"x\":1.0,\"y\":2.0,\"z\":3.0}}],\"events\":[{\"sequence\":1000,\"sim_time_s\":1.5,\"kind\":\"step_completed\",\"severity\":\"info\"}]}\n"
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":11,\"sim_time_s\":2.0,\"sequence\":101,\"body_id_catalog\":{\"schema_version\":1,\"created_body_ids\":[],\"destroyed_body_ids\":[]},\"bodies\":[{\"body_id\":\"planned_vehicle\",\"position_m\":{\"x\":4.0,\"y\":5.0,\"z\":6.0}}],\"events\":[{\"sequence\":1001,\"sim_time_s\":2.0,\"kind\":\"alarm_raised\",\"severity\":\"critical\"}]}\n");

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
  EXPECT_EQ(report.frames[0].bodies[0].visualization_role, "vehicle");
  EXPECT_DOUBLE_EQ(report.frames[0].bodies[0].position_m.x, 1.0);
  EXPECT_DOUBLE_EQ(report.frames[0].bodies[0].position_m.y, 2.0);
  EXPECT_DOUBLE_EQ(report.frames[0].bodies[0].position_m.z, 3.0);
  ASSERT_EQ(report.frames[0].events.size(), 1u);
  EXPECT_EQ(report.frames[0].events[0].kind, "step_completed");
  EXPECT_EQ(report.frames[0].events[0].severity, "info");
}

TEST(ReplayIngest, TracksBodyCatalogFromInitAndDiffsWithoutBodyScan) {
  const auto path = write_temp_file(
      "brambhand_replay_ingest_body_catalog_diffs.jsonl",
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":10,\"sim_time_s\":1.5,\"sequence\":100,\"body_id_catalog\":{\"schema_version\":1,\"initial_body_ids\":[\"current_vehicle\"],\"created_body_ids\":[\"detached_panel\"],\"destroyed_body_ids\":[]},\"bodies\":[{\"body_id\":\"current_vehicle\",\"position_m\":{\"x\":1.0,\"y\":2.0,\"z\":3.0}}]}\n"
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":11,\"sim_time_s\":2.0,\"sequence\":101,\"body_id_catalog\":{\"schema_version\":1,\"created_body_ids\":[\"probe\"],\"destroyed_body_ids\":[\"detached_panel\"]}}\n");

  const auto report = brambhand::client::common::load_replay_jsonl(path.string());
  ASSERT_TRUE(report.ok()) << report.error;
  ASSERT_EQ(report.frames.size(), 2u);
  ASSERT_EQ(report.body_ids.size(), 3u);
  EXPECT_EQ(report.body_ids[0], "current_vehicle");
  EXPECT_EQ(report.body_ids[1], "detached_panel");
  EXPECT_EQ(report.body_ids[2], "probe");
}

TEST(ReplayIngest, RejectsNonMonotonicSequence) {
  const auto path = write_temp_file(
      "brambhand_replay_ingest_non_monotonic.jsonl",
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":10,\"sim_time_s\":1.5,\"sequence\":100,\"body_id_catalog\":{\"schema_version\":1,\"initial_body_ids\":[\"a\"],\"created_body_ids\":[],\"destroyed_body_ids\":[]}}\n"
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":11,\"sim_time_s\":2.0,\"sequence\":100,\"body_id_catalog\":{\"schema_version\":1,\"created_body_ids\":[],\"destroyed_body_ids\":[]}}\n");

  const auto report = brambhand::client::common::load_replay_jsonl(path.string());
  EXPECT_FALSE(report.ok());
  EXPECT_TRUE(report.frames.empty());
}

TEST(ReplayIngest, IncrementalChunkCallbackReceivesDeterministicChunks) {
  const auto path = write_temp_file(
      "brambhand_replay_ingest_incremental_chunks.jsonl",
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":10,\"sim_time_s\":1.5,\"sequence\":100,\"body_id_catalog\":{\"schema_version\":1,\"initial_body_ids\":[\"b0\"],\"created_body_ids\":[],\"destroyed_body_ids\":[]},\"bodies\":[{\"body_id\":\"b0\",\"position_m\":{\"x\":1.0,\"y\":2.0,\"z\":3.0}}]}\n"
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":11,\"sim_time_s\":2.0,\"sequence\":101,\"body_id_catalog\":{\"schema_version\":1,\"created_body_ids\":[\"b1\"],\"destroyed_body_ids\":[]},\"bodies\":[{\"body_id\":\"b1\",\"position_m\":{\"x\":4.0,\"y\":5.0,\"z\":6.0}}]}\n"
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":12,\"sim_time_s\":2.5,\"sequence\":102,\"body_id_catalog\":{\"schema_version\":1,\"created_body_ids\":[\"b2\"],\"destroyed_body_ids\":[]}}\n");

  std::vector<std::size_t> chunk_sizes;
  std::vector<std::vector<std::string>> chunk_catalogs;
  std::vector<bool> chunk_final_flags;

  const auto report = brambhand::client::common::load_replay_jsonl_incremental(
      path.string(),
      2,
      [&](brambhand::client::common::ReplayIngestChunk&& chunk) {
        chunk_sizes.push_back(chunk.frames.size());
        chunk_catalogs.push_back(chunk.cumulative_body_ids);
        chunk_final_flags.push_back(chunk.is_final_chunk);
        return true;
      });

  ASSERT_TRUE(report.ok()) << report.error;
  ASSERT_EQ(report.frames.size(), 3u);
  ASSERT_EQ(report.body_ids.size(), 3u);
  EXPECT_EQ(report.body_ids[0], "b0");
  EXPECT_EQ(report.body_ids[1], "b1");
  EXPECT_EQ(report.body_ids[2], "b2");

  ASSERT_EQ(chunk_sizes.size(), 2u);
  EXPECT_EQ(chunk_sizes[0], 2u);
  EXPECT_EQ(chunk_sizes[1], 1u);
  ASSERT_EQ(chunk_catalogs.size(), 2u);
  EXPECT_EQ(chunk_catalogs[0], (std::vector<std::string>{"b0", "b1"}));
  EXPECT_EQ(chunk_catalogs[1], (std::vector<std::string>{"b0", "b1", "b2"}));
  ASSERT_EQ(chunk_final_flags.size(), 2u);
  EXPECT_FALSE(chunk_final_flags[0]);
  EXPECT_TRUE(chunk_final_flags[1]);
}

TEST(ReplayIngest, IncrementalCallbackAbortIsDeterministic) {
  const auto path = write_temp_file(
      "brambhand_replay_ingest_incremental_abort.jsonl",
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":10,\"sim_time_s\":1.5,\"sequence\":100,\"body_id_catalog\":{\"schema_version\":1,\"initial_body_ids\":[\"a\"],\"created_body_ids\":[],\"destroyed_body_ids\":[]}}\n"
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":11,\"sim_time_s\":2.0,\"sequence\":101,\"body_id_catalog\":{\"schema_version\":1,\"created_body_ids\":[],\"destroyed_body_ids\":[]}}\n"
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":12,\"sim_time_s\":2.5,\"sequence\":102,\"body_id_catalog\":{\"schema_version\":1,\"created_body_ids\":[],\"destroyed_body_ids\":[]}}\n");

  std::size_t callback_count = 0;
  const auto report = brambhand::client::common::load_replay_jsonl_incremental(
      path.string(),
      1,
      [&](brambhand::client::common::ReplayIngestChunk&&) {
        callback_count += 1;
        return callback_count < 2;
      });

  EXPECT_FALSE(report.ok());
  EXPECT_TRUE(report.frames.empty());
  EXPECT_EQ(callback_count, 2u);
  EXPECT_NE(report.error.find("aborted"), std::string::npos);
}

TEST(ReplayIngest, ConcurrentIngestConsumerPreservesOrderingWithBoundedQueue) {
  std::ostringstream jsonl;
  for (int i = 0; i < 24; ++i) {
    jsonl << "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":" << i
          << ",\"sim_time_s\":" << (0.5 * static_cast<double>(i))
          << ",\"sequence\":" << (100 + i)
          << ",\"body_id_catalog\":{\"schema_version\":1";
    if (i == 0) {
      jsonl << ",\"initial_body_ids\":[\"probe\"]";
    }
    jsonl << ",\"created_body_ids\":[],\"destroyed_body_ids\":[]}"
          << ",\"bodies\":[{\"body_id\":\"probe\",\"position_m\":{\"x\":" << i
          << ",\"y\":0.0,\"z\":0.0}}]"
          << ",\"events\":[{\"sequence\":" << (2000 + i)
          << ",\"sim_time_s\":" << (0.5 * static_cast<double>(i))
          << ",\"kind\":\"step_completed\",\"severity\":\"info\"}]}\n";
  }
  const auto path = write_temp_file(
      "brambhand_replay_ingest_concurrent_ordering.jsonl",
      jsonl.str());

  const auto baseline = brambhand::client::common::load_replay_jsonl(path.string());
  ASSERT_TRUE(baseline.ok()) << baseline.error;
  const auto baseline_workflow =
      brambhand::client::desktop::build_replay_quicklook_workflow(baseline.frames);

  std::mutex queue_mu;
  std::condition_variable queue_cv;
  std::deque<brambhand::client::common::ReplayIngestChunk> queue;
  bool ingest_done = false;
  std::size_t queue_high_watermark = 0;
  std::size_t producer_wait_count = 0;
  constexpr std::size_t kQueueMax = 1;

  brambhand::client::common::ReplayIngestReport ingest_report{};
  std::thread producer([&]() {
    ingest_report = brambhand::client::common::load_replay_jsonl_incremental(
        path.string(),
        3,
        [&](brambhand::client::common::ReplayIngestChunk&& chunk) {
          std::unique_lock<std::mutex> lock(queue_mu);
          while (queue.size() >= kQueueMax) {
            producer_wait_count += 1;
            queue_cv.wait(lock);
          }
          queue.push_back(std::move(chunk));
          queue_high_watermark = std::max(queue_high_watermark, queue.size());
          lock.unlock();
          queue_cv.notify_all();
          return true;
        });

    {
      std::lock_guard<std::mutex> lock(queue_mu);
      ingest_done = true;
    }
    queue_cv.notify_all();
  });

  std::this_thread::sleep_for(std::chrono::milliseconds(10));

  std::vector<brambhand::client::common::SimulationFrame> consumed_frames;
  while (true) {
    brambhand::client::common::ReplayIngestChunk chunk{};
    {
      std::unique_lock<std::mutex> lock(queue_mu);
      queue_cv.wait(lock, [&]() { return ingest_done || !queue.empty(); });
      if (queue.empty() && ingest_done) {
        break;
      }
      chunk = std::move(queue.front());
      queue.pop_front();
    }
    queue_cv.notify_all();

    consumed_frames.insert(
        consumed_frames.end(),
        std::make_move_iterator(chunk.frames.begin()),
        std::make_move_iterator(chunk.frames.end()));
  }

  producer.join();
  ASSERT_TRUE(ingest_report.ok()) << ingest_report.error;

  ASSERT_EQ(consumed_frames.size(), baseline.frames.size());
  for (std::size_t i = 0; i < consumed_frames.size(); ++i) {
    EXPECT_EQ(consumed_frames[i].sequence, baseline.frames[i].sequence);
    EXPECT_EQ(consumed_frames[i].tick_id, baseline.frames[i].tick_id);
  }

  const auto consumed_workflow =
      brambhand::client::desktop::build_replay_quicklook_workflow(consumed_frames);
  ASSERT_EQ(
      consumed_workflow.event_markers.size(),
      baseline_workflow.event_markers.size());
  for (std::size_t i = 0; i < consumed_workflow.event_markers.size(); ++i) {
    EXPECT_EQ(consumed_workflow.event_markers[i].sequence, baseline_workflow.event_markers[i].sequence);
    EXPECT_EQ(consumed_workflow.event_markers[i].kind, baseline_workflow.event_markers[i].kind);
    EXPECT_EQ(consumed_workflow.event_markers[i].severity, baseline_workflow.event_markers[i].severity);
  }

  EXPECT_EQ(queue_high_watermark, kQueueMax);
  EXPECT_GT(producer_wait_count, 0u);
}

TEST(ReplayIngest, RejectsMissingBodyIdCatalog) {
  const auto path = write_temp_file(
      "brambhand_replay_ingest_missing_body_id_catalog.jsonl",
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":10,\"sim_time_s\":1.5,\"sequence\":100}\n");

  const auto report = brambhand::client::common::load_replay_jsonl(path.string());
  EXPECT_FALSE(report.ok());
  EXPECT_TRUE(report.frames.empty());
  EXPECT_NE(report.error.find("body_id_catalog"), std::string::npos);
}

TEST(ReplayIngest, RejectsRunIdMismatch) {
  const auto path = write_temp_file(
      "brambhand_replay_ingest_runid_mismatch.jsonl",
      "{\"schema_version\":1,\"run_id\":\"run-a\",\"tick_id\":10,\"sim_time_s\":1.5,\"sequence\":100,\"body_id_catalog\":{\"schema_version\":1,\"initial_body_ids\":[\"a\"],\"created_body_ids\":[],\"destroyed_body_ids\":[]}}\n"
      "{\"schema_version\":1,\"run_id\":\"run-b\",\"tick_id\":11,\"sim_time_s\":2.0,\"sequence\":101,\"body_id_catalog\":{\"schema_version\":1,\"created_body_ids\":[],\"destroyed_body_ids\":[]}}\n");

  const auto report = brambhand::client::common::load_replay_jsonl(path.string());
  EXPECT_FALSE(report.ok());
  EXPECT_TRUE(report.frames.empty());
}
