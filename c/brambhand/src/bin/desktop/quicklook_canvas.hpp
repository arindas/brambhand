#pragma once

#include <cstdint>
#include <optional>
#include <string>

namespace brambhand::client::desktop {

struct CanvasPoint {
  float x{};
  float y{};
};

struct CanvasRect {
  float x{};
  float y{};
  float w{};
  float h{};
};

struct CanvasColor {
  std::uint8_t r{};
  std::uint8_t g{};
  std::uint8_t b{};
  std::uint8_t a{255};
};

class QuicklookCanvas {
 public:
  virtual ~QuicklookCanvas() = default;

  virtual void set_draw_color(const CanvasColor& color) = 0;
  virtual void draw_line(float x0, float y0, float x1, float y1) = 0;
  virtual void draw_rect(const CanvasRect& rect) = 0;
  virtual void fill_rect(const CanvasRect& rect) = 0;
  virtual void draw_point(float x, float y) = 0;
  virtual void draw_text(float x, float y, const std::string& text) = 0;
  virtual void set_clip_rect(const std::optional<CanvasRect>& rect) = 0;
};

}  // namespace brambhand::client::desktop
