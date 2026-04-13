#include <iostream>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include "brambhand/client/common/render_config.hpp"
#include "brambhand/client/common/replay_ingest.hpp"
#include "brambhand/client/common/runtime_frame.hpp"
#include "brambhand/client/desktop/replay_quicklook_workflow.hpp"
#include "brambhand/client/desktop/shell.hpp"
#include "brambhand/client/desktop/trajectory_infographic.hpp"
#include "replay_window.hpp"

int main(int argc, char** argv) {
  std::optional<std::string> replay_path;
  std::optional<std::string> render_config_path;
  bool no_window = false;
  bool strict_render_config = false;

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
    if (arg == "--render-config" && i + 1 < argc) {
      render_config_path = argv[++i];
      continue;
    }
    if (arg == "--no-window") {
      no_window = true;
      continue;
    }
    if (arg == "--strict-render-config") {
      strict_render_config = true;
      continue;
    }
  }

  if (!replay_path.has_value() || !render_config_path.has_value()) {
    std::cerr
        << "usage: brambhand_desktop --replay <replay.jsonl> --render-config <render-config.json> [--no-window] [--strict-render-config]\n";
    return 2;
  }

  const auto replay_report = brambhand::client::common::load_replay_jsonl(*replay_path);
  const auto render_config_report =
      brambhand::client::common::load_replay_render_config_json(*render_config_path);
  if (!render_config_report.ok()) {
    std::cerr << "render config ingest failed: " << render_config_report.error << "\n";
    return 1;
  }
  if (!replay_report.ok()) {
    std::cerr << "replay ingest failed: " << replay_report.error << "\n";
    return 1;
  }

  std::set<std::string> replay_body_ids;
  for (const auto& replay_frame : replay_report.frames) {
    for (const auto& body : replay_frame.bodies) {
      replay_body_ids.insert(body.body_id);
    }
  }

  const auto collect_missing_ids = [&](const std::vector<std::string>& configured_ids) {
    std::vector<std::string> missing;
    for (const auto& id : configured_ids) {
      if (!replay_body_ids.contains(id)) {
        missing.push_back(id);
      }
    }
    return missing;
  };

  const auto missing_dim_ids = collect_missing_ids(render_config_report.config.dim_trajectory_body_ids);
  const auto missing_sun_ids = collect_missing_ids(render_config_report.config.sun_body_ids);
  const auto missing_planet_ids = collect_missing_ids(render_config_report.config.planet_body_ids);
  const auto missing_probe_ids = collect_missing_ids(render_config_report.config.probe_body_ids);

  bool missing_focus_id = false;
  if (render_config_report.config.focus_body_id.has_value()) {
    missing_focus_id = !replay_body_ids.contains(*render_config_report.config.focus_body_id);
  }

  const bool has_missing =
      !missing_dim_ids.empty() || !missing_sun_ids.empty() || !missing_planet_ids.empty() ||
      !missing_probe_ids.empty() || missing_focus_id;

  if (has_missing) {
    std::cerr << "render config validation: replay is missing configured body ids\n";
    const auto print_missing = [&](const char* key, const std::vector<std::string>& ids) {
      if (ids.empty()) {
        return;
      }
      std::cerr << "  " << key << " missing:";
      for (const auto& id : ids) {
        std::cerr << " " << id;
      }
      std::cerr << "\n";
    };

    print_missing("dim_trajectory_body_ids", missing_dim_ids);
    print_missing("sun_body_ids", missing_sun_ids);
    print_missing("planet_body_ids", missing_planet_ids);
    print_missing("probe_body_ids", missing_probe_ids);

    if (missing_focus_id) {
      std::cerr << "  focus_body_id missing: " << *render_config_report.config.focus_body_id << "\n";
    }

    if (strict_render_config) {
      std::cerr << "strict render config validation enabled; aborting.\n";
      return 1;
    }
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
    if (!brambhand::client::desktop::run_replay_window(
            workflow,
            replay_report.frames,
            render_config_report.config)) {
      std::cerr << "failed to open replay window\n";
      return 1;
    }
  }

  return 0;
}
