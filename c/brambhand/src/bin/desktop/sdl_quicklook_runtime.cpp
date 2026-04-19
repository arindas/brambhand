#include "quicklook_runtime.hpp"

#include <SDL3/SDL.h>

#include "sdl_quicklook_canvas.hpp"

namespace brambhand::client::desktop {
namespace {

class SDLQuicklookRuntime final : public QuicklookRuntime {
 public:
  [[nodiscard]] bool initialize(const char* title, int width, int height) override {
    if (!SDL_Init(SDL_INIT_VIDEO)) {
      return false;
    }

    const SDL_WindowFlags flags = SDL_WINDOW_RESIZABLE | SDL_WINDOW_MAXIMIZED;
    window_ = SDL_CreateWindow(title, width, height, flags);
    if (window_ == nullptr) {
      SDL_Quit();
      return false;
    }

    renderer_ = SDL_CreateRenderer(window_, nullptr);
    if (renderer_ == nullptr) {
      SDL_DestroyWindow(window_);
      window_ = nullptr;
      SDL_Quit();
      return false;
    }

    canvas_ = std::make_unique<SDLQuicklookCanvas>(renderer_);
    return true;
  }

  void shutdown() override {
    canvas_.reset();
    if (renderer_ != nullptr) {
      SDL_DestroyRenderer(renderer_);
      renderer_ = nullptr;
    }
    if (window_ != nullptr) {
      SDL_DestroyWindow(window_);
      window_ = nullptr;
    }
    SDL_Quit();
  }

  [[nodiscard]] QuicklookInputSnapshot poll_input() override {
    QuicklookInputSnapshot input{};

    SDL_Event event;
    while (SDL_PollEvent(&event)) {
      if (event.type == SDL_EVENT_QUIT) {
        input.quit_requested = true;
      }
      if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_ESCAPE) {
        input.quit_requested = true;
      }
      if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_LEFTBRACKET) {
        input.decrease_playback = true;
      }
      if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_RIGHTBRACKET) {
        input.increase_playback = true;
      }
      if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_EQUALS) {
        input.zoom_in = true;
      }
      if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_MINUS) {
        input.zoom_out = true;
      }
      if (event.type == SDL_EVENT_MOUSE_WHEEL) {
        if (event.wheel.y > 0.0F) {
          input.zoom_in = true;
        } else if (event.wheel.y < 0.0F) {
          input.zoom_out = true;
        }
      }
    }

    const bool left = SDL_GetKeyboardState(nullptr)[SDL_SCANCODE_LEFT];
    const bool right = SDL_GetKeyboardState(nullptr)[SDL_SCANCODE_RIGHT];
    const bool up = SDL_GetKeyboardState(nullptr)[SDL_SCANCODE_UP];
    const bool down = SDL_GetKeyboardState(nullptr)[SDL_SCANCODE_DOWN];
    input.pan_left = left;
    input.pan_right = right;
    input.pan_up = up;
    input.pan_down = down;

    return input;
  }

  [[nodiscard]] std::uint64_t ticks_ms() const override {
    return SDL_GetTicks();
  }

  [[nodiscard]] std::pair<int, int> window_size() const override {
    int width = 0;
    int height = 0;
    if (window_ != nullptr) {
      SDL_GetWindowSize(window_, &width, &height);
    }
    return {width, height};
  }

  [[nodiscard]] QuicklookCanvas& canvas() override {
    return *canvas_;
  }

  void present() override {
    SDL_RenderPresent(renderer_);
  }

  void delay_ms(std::uint32_t ms) override {
    SDL_Delay(ms);
  }

 private:
  SDL_Window* window_{nullptr};
  SDL_Renderer* renderer_{nullptr};
  std::unique_ptr<SDLQuicklookCanvas> canvas_;
};

}  // namespace

std::unique_ptr<QuicklookRuntime> create_sdl_quicklook_runtime() {
  return std::make_unique<SDLQuicklookRuntime>();
}

}  // namespace brambhand::client::desktop
