#include "sdl_quicklook_canvas.hpp"

namespace brambhand::client::desktop {

SDLQuicklookCanvas::SDLQuicklookCanvas(SDL_Renderer* renderer)
    : renderer_(renderer) {}

void SDLQuicklookCanvas::set_draw_color(const CanvasColor& color) {
  SDL_SetRenderDrawColor(renderer_, color.r, color.g, color.b, color.a);
}

void SDLQuicklookCanvas::draw_line(float x0, float y0, float x1, float y1) {
  SDL_RenderLine(renderer_, x0, y0, x1, y1);
}

void SDLQuicklookCanvas::draw_rect(const CanvasRect& rect) {
  SDL_FRect r{.x = rect.x, .y = rect.y, .w = rect.w, .h = rect.h};
  SDL_RenderRect(renderer_, &r);
}

void SDLQuicklookCanvas::fill_rect(const CanvasRect& rect) {
  SDL_FRect r{.x = rect.x, .y = rect.y, .w = rect.w, .h = rect.h};
  SDL_RenderFillRect(renderer_, &r);
}

void SDLQuicklookCanvas::draw_point(float x, float y) {
  SDL_RenderPoint(renderer_, x, y);
}

void SDLQuicklookCanvas::draw_text(float x, float y, const std::string& text) {
  SDL_RenderDebugText(renderer_, x, y, text.c_str());
}

void SDLQuicklookCanvas::set_clip_rect(const std::optional<CanvasRect>& rect) {
  if (!rect.has_value()) {
    SDL_SetRenderClipRect(renderer_, nullptr);
    return;
  }
  SDL_Rect clip{
      static_cast<int>(rect->x),
      static_cast<int>(rect->y),
      static_cast<int>(rect->w),
      static_cast<int>(rect->h),
  };
  SDL_SetRenderClipRect(renderer_, &clip);
}

}  // namespace brambhand::client::desktop
