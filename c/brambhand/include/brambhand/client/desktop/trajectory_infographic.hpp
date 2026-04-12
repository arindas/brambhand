#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "brambhand/client/common/runtime_frame.hpp"

namespace brambhand::client::desktop {

inline constexpr std::uint32_t kTrajectoryInfographicSchemaVersion = 1;

struct TrajectoryPoint2D {
  double x_m{};
  double y_m{};
};

struct TrajectoryCurveLayer {
  std::string name;
  std::string color_hex;
  std::vector<TrajectoryPoint2D> points;
};

struct TrajectoryObjectIcon {
  std::string name;
  std::string icon;
  std::string color_hex;
  double x_m{};
  double y_m{};
};

struct TrajectoryInfographicPanel {
  std::uint32_t schema_version{kTrajectoryInfographicSchemaVersion};
  std::vector<TrajectoryCurveLayer> curve_layers;
  std::vector<TrajectoryObjectIcon> object_icons;
};

[[nodiscard]] TrajectoryInfographicPanel build_trajectory_infographic_panel(
    const std::vector<brambhand::client::common::SimulationFrame>& frames);

}  // namespace brambhand::client::desktop
