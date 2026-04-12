#include "brambhand/client/desktop/replay_quicklook_workflow.hpp"

#include <algorithm>

namespace brambhand::client::desktop {
namespace {

const char* severity_color(const std::string& severity) {
  if (severity == "critical") {
    return "#FF4D4D";
  }
  if (severity == "warning") {
    return "#FFC107";
  }
  return "#4DA3FF";
}

}  // namespace

ReplayQuicklookWorkflowOutput build_replay_quicklook_workflow(
    const std::vector<brambhand::client::common::SimulationFrame>& frames) {
  ReplayQuicklookWorkflowOutput output{};
  output.trajectory_panel = build_trajectory_infographic_panel(frames);

  for (const auto& frame : frames) {
    for (const auto& event : frame.events) {
      output.event_markers.push_back(QuicklookEventMarker{
          .sequence = event.sequence,
          .sim_time_s = event.sim_time_s,
          .kind = event.kind,
          .severity = event.severity,
          .color_hex = severity_color(event.severity),
      });
    }
  }

  std::stable_sort(
      output.event_markers.begin(),
      output.event_markers.end(),
      [](const QuicklookEventMarker& a, const QuicklookEventMarker& b) {
        if (a.sequence != b.sequence) {
          return a.sequence < b.sequence;
        }
        if (a.sim_time_s != b.sim_time_s) {
          return a.sim_time_s < b.sim_time_s;
        }
        return a.kind < b.kind;
      });

  return output;
}

}  // namespace brambhand::client::desktop
