#include <optional>

#include <gtest/gtest.h>

#include "../bin/desktop/renderer_capability_profile.hpp"

TEST(RendererCapabilityProfile, Quicklook2DProvidesPolicyBundle) {
  const auto profile = brambhand::client::desktop::create_renderer_capability_profile(
      brambhand::client::desktop::DesktopRendererMode::Quicklook2D);
  ASSERT_NE(profile, nullptr);

  EXPECT_EQ(
      profile->renderer_mode(),
      brambhand::client::desktop::DesktopRendererMode::Quicklook2D);

  const auto layout = profile->create_ui_layout_policy();
  const auto trace = profile->create_trace_policy();
  const auto sidebar = profile->create_sidebar_policy();

  ASSERT_NE(layout, nullptr);
  ASSERT_NE(trace, nullptr);
  ASSERT_NE(sidebar, nullptr);

  const auto panels = layout->compute(1280, 720);
  EXPECT_GT(panels.viewport.w, 0.0F);
  EXPECT_GT(panels.sidebar.w, 0.0F);
  EXPECT_TRUE(sidebar->show_events_section());
  EXPECT_TRUE(trace->should_draw_segment(10.0, std::nullopt));
}

TEST(RendererCapabilityProfile, PlannedVulkanProfileIsAvailableForPolicyPlanning) {
  const auto profile = brambhand::client::desktop::create_renderer_capability_profile(
      brambhand::client::desktop::DesktopRendererMode::Vulkan3D);
  ASSERT_NE(profile, nullptr);
  EXPECT_EQ(
      profile->renderer_mode(),
      brambhand::client::desktop::DesktopRendererMode::Vulkan3D);
}
