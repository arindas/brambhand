#include <iostream>

#include "brambhand/client/common/runtime_frame.hpp"
#include "brambhand/client/desktop/shell.hpp"

int main() {
  brambhand::client::common::SimulationFrame frame{};
  frame.run_id = "bootstrap";

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

  std::cout << "brambhand_desktop bootstrap, run_id=" << frame.run_id << "\n";
  std::cout << "desktop shell backend="
            << brambhand::client::desktop::backend_name(shell.telemetry().backend)
            << ", imgui_docking=" << (shell.telemetry().imgui_docking_enabled ? "on" : "off")
            << ", status=" << brambhand::client::desktop::status_name(shell.telemetry().status)
            << ", frames=" << shell.telemetry().frames_pumped << "\n";
  return 0;
}
