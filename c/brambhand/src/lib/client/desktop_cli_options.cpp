#include "brambhand/client/common/desktop_cli_options.hpp"

#include "brambhand/client/common/cli_parse.hpp"

namespace brambhand::client::common {

DesktopCliOptionsParseReport parse_desktop_cli_options(int argc, char** argv) {
  DesktopCliOptionsParseReport report{};

  const auto parsed = parse_cli_tokens(
      argc,
      argv,
      std::vector<CliOptionSpec>{
          CliOptionSpec{.name = "--live", .kind = CliOptionKind::Flag},
          CliOptionSpec{.name = "--replay", .kind = CliOptionKind::Value},
          CliOptionSpec{.name = "--render-config", .kind = CliOptionKind::Value},
          CliOptionSpec{.name = "--renderer", .kind = CliOptionKind::Value},
          CliOptionSpec{.name = "--allow-renderer-fallback", .kind = CliOptionKind::Flag},
          CliOptionSpec{.name = "--concurrent-ingest", .kind = CliOptionKind::Flag},
          CliOptionSpec{.name = "--ingest-chunk-frames", .kind = CliOptionKind::Value},
          CliOptionSpec{.name = "--ingest-queue-max-chunks", .kind = CliOptionKind::Value},
          CliOptionSpec{.name = "--no-window", .kind = CliOptionKind::Flag},
          CliOptionSpec{.name = "--strict-render-config", .kind = CliOptionKind::Flag},
      });

  if (!parsed.ok()) {
    report.error = parsed.error;
    return report;
  }

  if (parsed.flags.contains("--live")) {
    report.error = "live visualization is not supported in R8.05; use --replay <path>";
    return report;
  }

  const auto schema_validation = validate_cli_schema(
      parsed,
      CliSchemaValidationRules{
          .required_sets = {
              CliRequiredOptionSet{.option_names = {"--replay", "--render-config"}},
          },
          .mutually_exclusive_groups = {
              CliMutuallyExclusiveGroup{.option_names = {"--live", "--replay"}, .require_one = true},
          },
      });
  if (!schema_validation.ok()) {
    report.error = schema_validation.error;
    return report;
  }

  if (const auto it = parsed.values.find("--replay"); it != parsed.values.end()) {
    report.options.replay_path = it->second;
  }
  if (const auto it = parsed.values.find("--render-config"); it != parsed.values.end()) {
    report.options.render_config_path = it->second;
  }
  if (const auto it = parsed.values.find("--renderer"); it != parsed.values.end()) {
    report.options.renderer_mode_arg = it->second;
  }

  report.options.allow_renderer_fallback = parsed.flags.contains("--allow-renderer-fallback");
  report.options.concurrent_ingest = parsed.flags.contains("--concurrent-ingest");
  report.options.no_window = parsed.flags.contains("--no-window");
  report.options.strict_render_config = parsed.flags.contains("--strict-render-config");

  if (!cli_assign_transformed_value(
          parsed,
          "--ingest-chunk-frames",
          report.options.ingest_chunk_frames,
          report.error,
          "numeric")) {
    return report;
  }

  if (!cli_assign_transformed_value(
          parsed,
          "--ingest-queue-max-chunks",
          report.options.ingest_queue_max_chunks,
          report.error,
          "numeric")) {
    return report;
  }

  return report;
}

std::string desktop_cli_usage() {
  return "usage: brambhand_desktop --replay <replay.jsonl> --render-config <render-config.json> "
         "[--renderer quicklook_2d|vulkan_3d] [--allow-renderer-fallback] "
         "[--concurrent-ingest] [--ingest-chunk-frames <N>] [--ingest-queue-max-chunks <N>] "
         "[--no-window] [--strict-render-config]";
}

}  // namespace brambhand::client::common
