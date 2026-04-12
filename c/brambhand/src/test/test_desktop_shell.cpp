#include <gtest/gtest.h>

#include "brambhand/client/desktop/shell.hpp"

TEST(DesktopShell, InitializesAndPumpsFrameDeterministically) {
  brambhand::client::desktop::DesktopShellConfig config{};
  config.backend = brambhand::client::desktop::DesktopPlatformBackend::GLFW;
  config.imgui_docking_enabled = true;

  brambhand::client::desktop::DesktopShell shell(config);
  ASSERT_TRUE(shell.initialize());
  EXPECT_EQ(shell.telemetry().status,
            brambhand::client::desktop::DesktopShellStatus::Running);
  EXPECT_TRUE(shell.pump_frame());
  EXPECT_EQ(shell.telemetry().frames_pumped, 1u);

  shell.shutdown();
  EXPECT_EQ(shell.telemetry().status,
            brambhand::client::desktop::DesktopShellStatus::Stopped);
}

TEST(DesktopShell, RejectsInvalidWindowExtent) {
  brambhand::client::desktop::DesktopShellConfig config{};
  config.width_px = 0;

  brambhand::client::desktop::DesktopShell shell(config);
  EXPECT_FALSE(shell.initialize());
  EXPECT_EQ(shell.telemetry().status,
            brambhand::client::desktop::DesktopShellStatus::Failed);
  EXPECT_FALSE(shell.telemetry().last_error.empty());
}
