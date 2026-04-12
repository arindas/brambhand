#include <iostream>
#include <optional>
#include <string>

#include "brambhand/client/common/replay_ingest.hpp"
#include "brambhand/client/common/runtime_frame.hpp"
#include "brambhand/client/desktop/replay_quicklook_workflow.hpp"
#include "brambhand/client/desktop/shell.hpp"
#include "brambhand/client/desktop/trajectory_infographic.hpp"
#include "replay_window.hpp"

int main(int argc, char** argv) {
  std::optional<std::string> replay_path;
  bool no_window = false;

  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--live") {
      std::cerr << "live visualization is not supported in R8.05; use --replay <path>\n";
      return 2;
    }
    if (arg == "--replay" && i + 1 < argc) {
      replay_path = argv[++i];
      continue;
    }
    if (arg == "--no-window") {
      no_window = true;
      continue;
    }
  }

  if (!replay_path.has_value()) {
    std::cerr << "usage: brambhand_desktop --replay <replay.jsonl> [--no-window]\n";
    return 2;
  }

  const auto replay_report = brambhand::client::common::load_replay_jsonl(*replay_path);
  if (!replay_report.ok()) {
    std::cerr << "replay ingest failed: " << replay_report.error << "\n";
    return 1;
  }

  brambhand::client::common::SimulationFrame frame{};
  frame.run_id = replay_report.frames.empty() ? "empty_replay" : replay_report.frames.back().run_id;
  const auto workflow =
      brambhand::client::desktop::build_replay_quicklook_workflow(replay_report.frames);

  brambhand::client::desktop::DesktopShellConfig config{};
  config.backend = brambhand::client::desktop::DesktopPlatformBackend::SDL3;
  config.imgui_docking_enabled = true;

  brambhand::client::desktop::DesktopShell shell(config);
  if (!shell.initialize()) {
    std::cerr << "desktop shell initialization failed: " << shell.telemetry().last_error << "\n";
    return 1;
  }
  (void)shell.pump_frame();
  shell.shutdown();

  std::cout << "brambhand_desktop replay mode, run_id=" << frame.run_id
            << ", loaded_frames=" << replay_report.frames.size() << "\n";
  std::cout << "desktop shell backend="
            << brambhand::client::desktop::backend_name(shell.telemetry().backend)
            << ", imgui_docking=" << (shell.telemetry().imgui_docking_enabled ? "on" : "off")
            << ", status=" << brambhand::client::desktop::status_name(shell.telemetry().status)
            << ", frames=" << shell.telemetry().frames_pumped << "\n";
  std::cout << "trajectory_panel schema=" << workflow.trajectory_panel.schema_version
            << ", curve_layers=" << workflow.trajectory_panel.curve_layers.size()
            << ", object_icons=" << workflow.trajectory_panel.object_icons.size() << "\n";
  std::cout << "event_markers=" << workflow.event_markers.size();
  if (!workflow.event_markers.empty()) {
    const auto& first = workflow.event_markers.front();
    std::cout << ", first_event={sequence:" << first.sequence << ", kind:" << first.kind
              << ", severity:" << first.severity << ", color:" << first.color_hex << "}";
  }
  std::cout << "\n";

  if (!no_window) {
    if (!brambhand::client::desktop::run_replay_window(workflow, replay_report.frames)) {
      std::cerr << "failed to open replay window\n";
      return 1;
    }
  }

  return 0;
}
