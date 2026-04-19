#include "replay_ingest_benchmark_options.hpp"

#include <charconv>
#include <string>
#include <string_view>
#include <vector>

#include "brambhand/client/common/cli_parse.hpp"

namespace brambhand::client::desktop {
namespace {

std::vector<std::size_t> profile_chunk_candidates(const std::string& profile) {
  if (profile == "interactive") {
    return {64, 128, 256};
  }
  if (profile == "throughput") {
    return {512, 1024, 2048};
  }
  if (profile == "all") {
    return {64, 128, 256, 512, 1024};
  }
  return {128, 256, 512};  // balanced default
}

std::vector<std::size_t> profile_queue_candidates(const std::string& profile) {
  if (profile == "interactive") {
    return {1, 2, 4};
  }
  if (profile == "throughput") {
    return {4, 8, 16};
  }
  if (profile == "all") {
    return {1, 2, 4, 8, 16};
  }
  return {2, 4, 8};  // balanced default
}

bool parse_size_t(std::string_view token, std::size_t& out) {
  if (token.empty()) {
    return false;
  }

  std::size_t value = 0;
  const auto* begin = token.data();
  const auto* end = token.data() + token.size();
  const auto res = std::from_chars(begin, end, value);
  if (res.ec != std::errc{} || res.ptr != end) {
    return false;
  }

  out = value;
  return true;
}

bool parse_size_list(const std::string& csv, std::vector<std::size_t>& out) {
  out.clear();
  std::size_t start = 0;
  while (start < csv.size()) {
    const auto comma = csv.find(',', start);
    const auto end = (comma == std::string::npos) ? csv.size() : comma;
    const auto token = std::string_view(csv).substr(start, end - start);

    std::size_t value = 0;
    if (!parse_size_t(token, value) || value == 0) {
      return false;
    }
    out.push_back(value);

    if (comma == std::string::npos) {
      break;
    }
    start = comma + 1;
  }

  return !out.empty();
}

}  // namespace

ReplayIngestBenchmarkOptionsReport parse_replay_ingest_benchmark_options(
    int argc,
    char** argv) {
  ReplayIngestBenchmarkOptionsReport report{};

  const auto parsed = brambhand::client::common::parse_cli_tokens(
      argc,
      argv,
      {
          brambhand::client::common::CliOptionSpec{"--replay", brambhand::client::common::CliOptionKind::Value},
          brambhand::client::common::CliOptionSpec{"--profile", brambhand::client::common::CliOptionKind::Value},
          brambhand::client::common::CliOptionSpec{"--chunk-frames-list", brambhand::client::common::CliOptionKind::Value},
          brambhand::client::common::CliOptionSpec{"--queue-max-chunks-list", brambhand::client::common::CliOptionKind::Value},
          brambhand::client::common::CliOptionSpec{"--iterations", brambhand::client::common::CliOptionKind::Value},
          brambhand::client::common::CliOptionSpec{"--consumer-delay-ms", brambhand::client::common::CliOptionKind::Value},
          brambhand::client::common::CliOptionSpec{"--no-sequential-baseline", brambhand::client::common::CliOptionKind::Flag},
          brambhand::client::common::CliOptionSpec{"--help", brambhand::client::common::CliOptionKind::Flag},
      });

  if (!parsed.ok()) {
    report.error = parsed.error;
    return report;
  }

  report.options.show_help = parsed.flags.contains("--help");
  if (report.options.show_help) {
    return report;
  }

  const auto schema_validation = brambhand::client::common::validate_cli_schema(
      parsed,
      brambhand::client::common::CliSchemaValidationRules{
          .required_sets = {
              brambhand::client::common::CliRequiredOptionSet{.option_names = {"--replay"}},
          },
      });
  if (!schema_validation.ok()) {
    report.error = schema_validation.error;
    return report;
  }

  report.options.replay_path = parsed.values.at("--replay");

  std::string profile = "balanced";
  const auto profile_it = parsed.values.find("--profile");
  if (profile_it != parsed.values.end()) {
    profile = profile_it->second;
    if (profile != "interactive" && profile != "balanced" &&
        profile != "throughput" && profile != "all") {
      report.error = "unsupported --profile value: " + profile +
                     " (expected interactive|balanced|throughput|all)";
      return report;
    }
  }

  report.options.chunk_frames_candidates = profile_chunk_candidates(profile);
  report.options.queue_max_chunks_candidates = profile_queue_candidates(profile);

  const auto chunk_list_it = parsed.values.find("--chunk-frames-list");
  if (chunk_list_it != parsed.values.end()) {
    if (!parse_size_list(chunk_list_it->second, report.options.chunk_frames_candidates)) {
      report.error = "invalid --chunk-frames-list (expected comma-separated positive integers)";
      return report;
    }
  }

  const auto queue_list_it = parsed.values.find("--queue-max-chunks-list");
  if (queue_list_it != parsed.values.end()) {
    if (!parse_size_list(queue_list_it->second, report.options.queue_max_chunks_candidates)) {
      report.error = "invalid --queue-max-chunks-list (expected comma-separated positive integers)";
      return report;
    }
  }

  if (!brambhand::client::common::cli_assign_transformed_value(
          parsed,
          "--iterations",
          report.options.iterations,
          report.error,
          "numeric")) {
    return report;
  }
  if (report.options.iterations == 0) {
    report.error = "invalid --iterations value (expected positive integer)";
    return report;
  }

  if (!brambhand::client::common::cli_assign_transformed_value(
          parsed,
          "--consumer-delay-ms",
          report.options.consumer_delay_ms,
          report.error,
          "numeric")) {
    return report;
  }

  report.options.include_sequential_baseline =
      !parsed.flags.contains("--no-sequential-baseline");

  return report;
}

std::string replay_ingest_benchmark_usage() {
  return
      "Usage: brambhand_replay_ingest_benchmark --replay <path> [options]\n"
      "\n"
      "Options:\n"
      "  --profile interactive|balanced|throughput|all  Sweep preset (default: balanced)\n"
      "  --chunk-frames-list <csv>                      Override chunk candidate list (e.g. 128,256,512)\n"
      "  --queue-max-chunks-list <csv>                  Override queue-depth candidate list (e.g. 2,4,8)\n"
      "  --iterations <N>                               Runs per candidate pair (default: 3)\n"
      "  --consumer-delay-ms <N>                        Sleep per ingest callback update to emulate renderer cost\n"
      "  --no-sequential-baseline                       Skip sequential ingest baseline rows\n"
      "  --help                                         Show this message\n";
}

}  // namespace brambhand::client::desktop
