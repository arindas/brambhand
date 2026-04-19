#pragma once

#include <cstddef>
#include <optional>
#include <string>

namespace brambhand::client::common {

struct DesktopCliOptions {
  std::optional<std::string> replay_path;
  std::optional<std::string> render_config_path;
  bool no_window{false};
  bool strict_render_config{false};
  bool allow_renderer_fallback{false};
  bool concurrent_ingest{false};
  std::size_t ingest_chunk_frames{256};
  std::size_t ingest_queue_max_chunks{8};
  std::string renderer_mode_arg{"quicklook_2d"};
};

struct DesktopCliOptionsParseReport {
  DesktopCliOptions options;
  std::string error;

  [[nodiscard]] bool ok() const { return error.empty(); }
};

[[nodiscard]] DesktopCliOptionsParseReport parse_desktop_cli_options(int argc, char** argv);

[[nodiscard]] std::string desktop_cli_usage();

}  // namespace brambhand::client::common
