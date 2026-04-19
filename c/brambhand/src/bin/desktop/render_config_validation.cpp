#include "render_config_validation.hpp"

#include <unordered_set>

namespace brambhand::client::desktop {

ReplayRenderConfigValidationResult validate_replay_render_config_body_ids(
    const brambhand::client::common::ReplayRenderConfig& config,
    const std::vector<std::string>& replay_body_ids) {
  ReplayRenderConfigValidationResult result{};
  const std::unordered_set<std::string> replay_ids(replay_body_ids.begin(), replay_body_ids.end());

  const auto collect_missing = [&](const std::vector<std::string>& configured_ids) {
    std::vector<std::string> missing;
    for (const auto& id : configured_ids) {
      if (!replay_ids.contains(id)) {
        missing.push_back(id);
      }
    }
    return missing;
  };

  result.missing_dim_ids = collect_missing(config.dim_trajectory_body_ids);
  result.missing_sun_ids = collect_missing(config.sun_body_ids);
  result.missing_planet_ids = collect_missing(config.planet_body_ids);
  result.missing_probe_ids = collect_missing(config.probe_body_ids);

  if (config.focus_body_id.has_value()) {
    result.missing_focus_id = !replay_ids.contains(*config.focus_body_id);
  }

  return result;
}

}  // namespace brambhand::client::desktop
