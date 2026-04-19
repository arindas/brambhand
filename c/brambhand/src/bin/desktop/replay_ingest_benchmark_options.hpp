#pragma once

#include <cstddef>
#include <string>
#include <vector>

namespace brambhand::client::desktop {

struct ReplayIngestBenchmarkOptions {
  std::string replay_path;
  std::vector<std::size_t> chunk_frames_candidates;
  std::vector<std::size_t> queue_max_chunks_candidates;
  std::size_t iterations{3};
  std::size_t consumer_delay_ms{0};
  bool include_sequential_baseline{true};
  bool show_help{false};
};

struct ReplayIngestBenchmarkOptionsReport {
  ReplayIngestBenchmarkOptions options;
  std::string error;

  [[nodiscard]] bool ok() const { return error.empty(); }
};

[[nodiscard]] ReplayIngestBenchmarkOptionsReport parse_replay_ingest_benchmark_options(
    int argc,
    char** argv);

[[nodiscard]] std::string replay_ingest_benchmark_usage();

}  // namespace brambhand::client::desktop
