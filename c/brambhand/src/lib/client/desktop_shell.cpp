#include "brambhand/client/desktop/shell.hpp"

#include <utility>

namespace brambhand::client::desktop {

namespace {

bool valid_window_extent(std::uint32_t width_px, std::uint32_t height_px) {
  return width_px > 0 && height_px > 0;
}

}  // namespace

DesktopShell::DesktopShell(DesktopShellConfig config)
    : config_(std::move(config)) {
  telemetry_.backend = config_.backend;
  telemetry_.imgui_docking_enabled = config_.imgui_docking_enabled;
}

bool DesktopShell::initialize() {
  telemetry_.last_error.clear();
  if (!valid_window_extent(config_.width_px, config_.height_px)) {
    telemetry_.status = DesktopShellStatus::Failed;
    telemetry_.last_error = "window extent must be non-zero";
    return false;
  }

  telemetry_.status = DesktopShellStatus::Running;
  telemetry_.frames_pumped = 0;
  return true;
}

bool DesktopShell::pump_frame() {
  if (telemetry_.status != DesktopShellStatus::Running) {
    telemetry_.last_error = "shell is not running";
    return false;
  }

  telemetry_.frames_pumped += 1;
  return true;
}

void DesktopShell::shutdown() {
  if (telemetry_.status == DesktopShellStatus::Running) {
    telemetry_.status = DesktopShellStatus::Stopped;
  }
}

const DesktopShellConfig& DesktopShell::config() const { return config_; }

const DesktopShellTelemetry& DesktopShell::telemetry() const { return telemetry_; }

const char* backend_name(DesktopPlatformBackend backend) {
  switch (backend) {
    case DesktopPlatformBackend::SDL3:
      return "SDL3";
    case DesktopPlatformBackend::GLFW:
      return "GLFW";
  }
  return "unknown";
}

const char* status_name(DesktopShellStatus status) {
  switch (status) {
    case DesktopShellStatus::NotStarted:
      return "not_started";
    case DesktopShellStatus::Running:
      return "running";
    case DesktopShellStatus::Stopped:
      return "stopped";
    case DesktopShellStatus::Failed:
      return "failed";
  }
  return "unknown";
}

}  // namespace brambhand::client::desktop
