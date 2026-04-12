#include <iostream>
#include <optional>
#include <string>

#include "brambhand/client/common/replay_ingest.hpp"
#include "brambhand/client/common/runtime_frame.hpp"
#include "brambhand/client/desktop/shell.hpp"

int main(int argc, char** argv) {
  std::optional<std::string> replay_path;

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
  }

  if (!replay_path.has_value()) {
    std::cerr << "usage: brambhand_desktop --replay <replay.jsonl>\n";
    return 2;
  }

  const auto replay_report = brambhand::client::common::load_replay_jsonl(*replay_path);
  if (!replay_report.ok()) {
    std::cerr << "replay ingest failed: " << replay_report.error << "\n";
    return 1;
  }

  brambhand::client::common::SimulationFrame frame{};
  frame.run_id = replay_report.frames.empty() ? "empty_replay" : replay_report.frames.back().run_id;

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
  return 0;
}
