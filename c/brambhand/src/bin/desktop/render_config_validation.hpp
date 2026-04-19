#pragma once

#include <string>
#include <vector>

#include "brambhand/client/common/render_config.hpp"

namespace brambhand::client::desktop {

struct ReplayRenderConfigValidationResult {
  std::vector<std::string> missing_dim_ids;
  std::vector<std::string> missing_sun_ids;
  std::vector<std::string> missing_planet_ids;
  std::vector<std::string> missing_probe_ids;
  bool missing_focus_id{false};

  [[nodiscard]] bool has_missing() const {
    return !missing_dim_ids.empty() || !missing_sun_ids.empty() || !missing_planet_ids.empty() ||
           !missing_probe_ids.empty() || missing_focus_id;
  }
};

[[nodiscard]] ReplayRenderConfigValidationResult validate_replay_render_config_body_ids(
    const brambhand::client::common::ReplayRenderConfig& config,
    const std::vector<std::string>& replay_body_ids);

}  // namespace brambhand::client::desktop
