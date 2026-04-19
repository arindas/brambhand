#pragma once

#include <memory>
#include <string>

#include "brambhand/client/common/render_config.hpp"

namespace brambhand::client::common {

enum class BodyRenderRole {
  Generic,
  Sun,
  Planet,
  Probe,
};

class ReplayRenderSemantics {
 public:
  virtual ~ReplayRenderSemantics() = default;

  [[nodiscard]] virtual bool is_dim_trajectory_body(const std::string& body_id) const = 0;
  [[nodiscard]] virtual BodyRenderRole role_for(const std::string& body_id) const = 0;
};

[[nodiscard]] std::unique_ptr<ReplayRenderSemantics> create_replay_render_semantics(
    const ReplayRenderConfig& render_config);

}  // namespace brambhand::client::common
