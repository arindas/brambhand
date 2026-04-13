#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace brambhand::client::common {

struct ReplayRenderConfig {
  std::uint32_t schema_version{1};
  std::vector<std::string> dim_trajectory_body_ids;
  std::optional<std::string> focus_body_id;
  std::vector<std::string> sun_body_ids;
  std::vector<std::string> planet_body_ids;
  std::vector<std::string> probe_body_ids;
};

struct ReplayRenderConfigReport {
  ReplayRenderConfig config;
  std::string error;

  [[nodiscard]] bool ok() const { return error.empty(); }
};

[[nodiscard]] ReplayRenderConfigReport load_replay_render_config_json(const std::string& path);

}  // namespace brambhand::client::common
