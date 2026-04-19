#include <vector>

#include <gtest/gtest.h>

#include "../bin/desktop/replay_ingest_benchmark_options.hpp"

TEST(ReplayIngestBenchmarkOptions, AppliesProfileDefaults) {
  const std::vector<char*> args{
      const_cast<char*>("bench"),
      const_cast<char*>("--replay"),
      const_cast<char*>("/tmp/replay.jsonl"),
      const_cast<char*>("--profile"),
      const_cast<char*>("interactive"),
  };

  auto report = brambhand::client::desktop::parse_replay_ingest_benchmark_options(
      static_cast<int>(args.size()),
      const_cast<char**>(args.data()));

  ASSERT_TRUE(report.ok()) << report.error;
  EXPECT_EQ(report.options.chunk_frames_candidates, (std::vector<std::size_t>{64, 128, 256}));
  EXPECT_EQ(report.options.queue_max_chunks_candidates, (std::vector<std::size_t>{1, 2, 4}));
  EXPECT_EQ(report.options.iterations, 3u);
}

TEST(ReplayIngestBenchmarkOptions, ParsesCustomListsAndFlags) {
  const std::vector<char*> args{
      const_cast<char*>("bench"),
      const_cast<char*>("--replay"),
      const_cast<char*>("/tmp/replay.jsonl"),
      const_cast<char*>("--chunk-frames-list"),
      const_cast<char*>("300,600"),
      const_cast<char*>("--queue-max-chunks-list"),
      const_cast<char*>("2,9"),
      const_cast<char*>("--iterations"),
      const_cast<char*>("5"),
      const_cast<char*>("--consumer-delay-ms"),
      const_cast<char*>("7"),
      const_cast<char*>("--no-sequential-baseline"),
  };

  auto report = brambhand::client::desktop::parse_replay_ingest_benchmark_options(
      static_cast<int>(args.size()),
      const_cast<char**>(args.data()));

  ASSERT_TRUE(report.ok()) << report.error;
  EXPECT_EQ(report.options.chunk_frames_candidates, (std::vector<std::size_t>{300, 600}));
  EXPECT_EQ(report.options.queue_max_chunks_candidates, (std::vector<std::size_t>{2, 9}));
  EXPECT_EQ(report.options.iterations, 5u);
  EXPECT_EQ(report.options.consumer_delay_ms, 7u);
  EXPECT_FALSE(report.options.include_sequential_baseline);
}

TEST(ReplayIngestBenchmarkOptions, RejectsInvalidCsv) {
  const std::vector<char*> args{
      const_cast<char*>("bench"),
      const_cast<char*>("--replay"),
      const_cast<char*>("/tmp/replay.jsonl"),
      const_cast<char*>("--chunk-frames-list"),
      const_cast<char*>("200,0"),
  };

  auto report = brambhand::client::desktop::parse_replay_ingest_benchmark_options(
      static_cast<int>(args.size()),
      const_cast<char**>(args.data()));

  EXPECT_FALSE(report.ok());
  EXPECT_NE(report.error.find("--chunk-frames-list"), std::string::npos);
}
