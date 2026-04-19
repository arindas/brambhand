#include "brambhand/client/common/render_semantics.hpp"

#include <unordered_set>

namespace brambhand::client::common {
namespace {

class ConfigReplayRenderSemantics final : public ReplayRenderSemantics {
 public:
  explicit ConfigReplayRenderSemantics(const ReplayRenderConfig& config)
      : dim_body_ids_(config.dim_trajectory_body_ids.begin(), config.dim_trajectory_body_ids.end()),
        sun_body_ids_(config.sun_body_ids.begin(), config.sun_body_ids.end()),
        planet_body_ids_(config.planet_body_ids.begin(), config.planet_body_ids.end()),
        probe_body_ids_(config.probe_body_ids.begin(), config.probe_body_ids.end()) {}

  [[nodiscard]] bool is_dim_trajectory_body(const std::string& body_id) const override {
    return dim_body_ids_.contains(body_id);
  }

  [[nodiscard]] BodyRenderRole role_for(const std::string& body_id) const override {
    if (sun_body_ids_.contains(body_id)) {
      return BodyRenderRole::Sun;
    }
    if (probe_body_ids_.contains(body_id)) {
      return BodyRenderRole::Probe;
    }
    if (planet_body_ids_.contains(body_id)) {
      return BodyRenderRole::Planet;
    }
    return BodyRenderRole::Generic;
  }

 private:
  std::unordered_set<std::string> dim_body_ids_;
  std::unordered_set<std::string> sun_body_ids_;
  std::unordered_set<std::string> planet_body_ids_;
  std::unordered_set<std::string> probe_body_ids_;
};

}  // namespace

std::unique_ptr<ReplayRenderSemantics> create_replay_render_semantics(
    const ReplayRenderConfig& render_config) {
  return std::make_unique<ConfigReplayRenderSemantics>(render_config);
}

}  // namespace brambhand::client::common
