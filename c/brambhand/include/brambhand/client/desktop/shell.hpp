#pragma once

#include <cstdint>
#include <string>

namespace brambhand::client::desktop {

enum class DesktopPlatformBackend {
  SDL3,
  GLFW,
};

enum class DesktopShellStatus {
  NotStarted,
  Running,
  Stopped,
  Failed,
};

struct DesktopShellConfig {
  DesktopPlatformBackend backend{DesktopPlatformBackend::SDL3};
  std::string app_name{"brambhand_desktop"};
  std::uint32_t width_px{1280};
  std::uint32_t height_px{720};
  bool imgui_docking_enabled{true};
};

struct DesktopShellTelemetry {
  DesktopPlatformBackend backend{DesktopPlatformBackend::SDL3};
  bool imgui_docking_enabled{true};
  std::uint64_t frames_pumped{0};
  DesktopShellStatus status{DesktopShellStatus::NotStarted};
  std::string last_error;
};

class DesktopShell {
 public:
  explicit DesktopShell(DesktopShellConfig config);

  bool initialize();
  bool pump_frame();
  void shutdown();

  [[nodiscard]] const DesktopShellConfig& config() const;
  [[nodiscard]] const DesktopShellTelemetry& telemetry() const;

 private:
  DesktopShellConfig config_;
  DesktopShellTelemetry telemetry_;
};

[[nodiscard]] const char* backend_name(DesktopPlatformBackend backend);
[[nodiscard]] const char* status_name(DesktopShellStatus status);

}  // namespace brambhand::client::desktop
