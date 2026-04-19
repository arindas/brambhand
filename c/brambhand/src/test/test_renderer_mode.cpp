#include <gtest/gtest.h>

#include "../bin/desktop/renderer_mode.hpp"

TEST(RendererMode, ParseAndResolveQuicklook) {
  const auto parsed = brambhand::client::desktop::parse_renderer_mode("quicklook_2d");
  ASSERT_TRUE(parsed.has_value());
  EXPECT_EQ(*parsed, brambhand::client::desktop::DesktopRendererMode::Quicklook2D);

  const auto resolved = brambhand::client::desktop::resolve_renderer_mode(*parsed, false);
  EXPECT_TRUE(resolved.ok());
  EXPECT_EQ(resolved.requested, brambhand::client::desktop::DesktopRendererMode::Quicklook2D);
  EXPECT_EQ(resolved.effective, brambhand::client::desktop::DesktopRendererMode::Quicklook2D);
  EXPECT_FALSE(resolved.used_fallback);
}

TEST(RendererMode, PlannedRendererRequiresFallbackOrFails) {
  const auto parsed = brambhand::client::desktop::parse_renderer_mode("vulkan_3d");
  ASSERT_TRUE(parsed.has_value());

  EXPECT_EQ(
      brambhand::client::desktop::renderer_mode_availability(*parsed),
      brambhand::client::desktop::DesktopRendererAvailability::Planned);

  const auto no_fallback = brambhand::client::desktop::resolve_renderer_mode(*parsed, false);
  EXPECT_FALSE(no_fallback.ok());

  const auto with_fallback = brambhand::client::desktop::resolve_renderer_mode(*parsed, true);
  EXPECT_TRUE(with_fallback.ok());
  EXPECT_TRUE(with_fallback.used_fallback);
  EXPECT_EQ(
      with_fallback.effective,
      brambhand::client::desktop::DesktopRendererMode::Quicklook2D);
}
