#include "brambhand/client/desktop/trajectory_infographic.hpp"

namespace brambhand::client::desktop {
namespace {

constexpr const char* kCurrentTrajectoryName = "current_trajectory";
constexpr const char* kPlannedTrajectoryName = "planned_trajectory";
constexpr const char* kCurrentVehicleName = "current_vehicle";
constexpr const char* kPlannedVehicleName = "planned_vehicle";

constexpr const char* kCurrentTrajectoryColor = "#00E5FF";
constexpr const char* kPlannedTrajectoryColor = "#C77DFF";
constexpr const char* kCurrentIconColor = "#FFFFFF";
constexpr const char* kPlannedIconColor = "#9AA4B2";

const brambhand::client::common::BodyState* find_body_by_id(
    const brambhand::client::common::SimulationFrame& frame,
    const std::string& body_id) {
  for (const auto& body : frame.bodies) {
    if (body.body_id == body_id) {
      return &body;
    }
  }
  return nullptr;
}

void append_point_if_body_present(
    std::vector<TrajectoryPoint2D>& points,
    const brambhand::client::common::BodyState* body) {
  if (body == nullptr) {
    return;
  }

  points.push_back(TrajectoryPoint2D{.x_m = body->position_m.x, .y_m = body->position_m.y});
}

}  // namespace

TrajectoryInfographicPanel build_trajectory_infographic_panel(
    const std::vector<brambhand::client::common::SimulationFrame>& frames) {
  std::vector<TrajectoryPoint2D> current_points;
  std::vector<TrajectoryPoint2D> planned_points;

  for (const auto& frame : frames) {
    const auto* current_named = find_body_by_id(frame, kCurrentVehicleName);
    const auto* current_fallback = frame.bodies.empty() ? nullptr : &frame.bodies.front();
    append_point_if_body_present(
        current_points,
        current_named != nullptr ? current_named : current_fallback);

    const auto* planned = find_body_by_id(frame, kPlannedVehicleName);
    append_point_if_body_present(planned_points, planned);
  }

  TrajectoryInfographicPanel panel{};
  panel.curve_layers = {
      TrajectoryCurveLayer{
          .name = kCurrentTrajectoryName,
          .color_hex = kCurrentTrajectoryColor,
          .points = current_points,
      },
      TrajectoryCurveLayer{
          .name = kPlannedTrajectoryName,
          .color_hex = kPlannedTrajectoryColor,
          .points = planned_points,
      },
  };

  if (!current_points.empty()) {
    const auto& point = current_points.back();
    panel.object_icons.push_back(TrajectoryObjectIcon{
        .name = kCurrentVehicleName,
        .icon = "ship",
        .color_hex = kCurrentIconColor,
        .x_m = point.x_m,
        .y_m = point.y_m,
    });
  }

  if (!planned_points.empty()) {
    const auto& point = planned_points.back();
    panel.object_icons.push_back(TrajectoryObjectIcon{
        .name = kPlannedVehicleName,
        .icon = "ghost_ship",
        .color_hex = kPlannedIconColor,
        .x_m = point.x_m,
        .y_m = point.y_m,
    });
  }

  return panel;
}

}  // namespace brambhand::client::desktop
