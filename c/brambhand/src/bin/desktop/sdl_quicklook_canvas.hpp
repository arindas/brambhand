#pragma once

#include <SDL3/SDL.h>

#include "quicklook_canvas.hpp"

namespace brambhand::client::desktop {

class SDLQuicklookCanvas final : public QuicklookCanvas {
 public:
  explicit SDLQuicklookCanvas(SDL_Renderer* renderer);

  void set_draw_color(const CanvasColor& color) override;
  void draw_line(float x0, float y0, float x1, float y1) override;
  void draw_rect(const CanvasRect& rect) override;
  void fill_rect(const CanvasRect& rect) override;
  void draw_point(float x, float y) override;
  void draw_text(float x, float y, const std::string& text) override;
  void set_clip_rect(const std::optional<CanvasRect>& rect) override;

 private:
  SDL_Renderer* renderer_;
};

}  // namespace brambhand::client::desktop
