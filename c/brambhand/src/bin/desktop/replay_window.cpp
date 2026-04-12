#include "replay_window.hpp"

#include <SDL3/SDL.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace brambhand::client::desktop {
namespace {

struct PlotBounds {
  double min_x{};
  double max_x{};
  double min_y{};
  double max_y{};
};

struct Rgba {
  std::uint8_t r{};
  std::uint8_t g{};
  std::uint8_t b{};
  std::uint8_t a{255};
};

int hex_digit(char ch) {
  if (ch >= '0' && ch <= '9') {
    return ch - '0';
  }
  if (ch >= 'a' && ch <= 'f') {
    return 10 + (ch - 'a');
  }
  if (ch >= 'A' && ch <= 'F') {
    return 10 + (ch - 'A');
  }
  return 0;
}

Rgba parse_hex_color(const std::string& hex) {
  if (hex.size() != 7 || hex[0] != '#') {
    return Rgba{.r = 255, .g = 255, .b = 255, .a = 255};
  }

  const auto parse_pair = [&](std::size_t idx) {
    return static_cast<std::uint8_t>((hex_digit(hex[idx]) << 4) | hex_digit(hex[idx + 1]));
  };

  return Rgba{
      .r = parse_pair(1),
      .g = parse_pair(3),
      .b = parse_pair(5),
      .a = 255,
  };
}

std::optional<PlotBounds> compute_bounds(const TrajectoryInfographicPanel& panel) {
  bool has_point = false;
  PlotBounds bounds{};

  for (const auto& layer : panel.curve_layers) {
    for (const auto& point : layer.points) {
      if (!has_point) {
        bounds.min_x = bounds.max_x = point.x_m;
        bounds.min_y = bounds.max_y = point.y_m;
        has_point = true;
        continue;
      }

      bounds.min_x = std::min(bounds.min_x, point.x_m);
      bounds.max_x = std::max(bounds.max_x, point.x_m);
      bounds.min_y = std::min(bounds.min_y, point.y_m);
      bounds.max_y = std::max(bounds.max_y, point.y_m);
    }
  }

  if (!has_point) {
    return std::nullopt;
  }

  if (std::abs(bounds.max_x - bounds.min_x) < 1e-9) {
    bounds.max_x += 1.0;
    bounds.min_x -= 1.0;
  }
  if (std::abs(bounds.max_y - bounds.min_y) < 1e-9) {
    bounds.max_y += 1.0;
    bounds.min_y -= 1.0;
  }

  return bounds;
}

SDL_FPoint map_point(
    double x,
    double y,
    const PlotBounds& bounds,
    const SDL_FRect& viewport) {
  const double tx = (x - bounds.min_x) / (bounds.max_x - bounds.min_x);
  const double ty = (y - bounds.min_y) / (bounds.max_y - bounds.min_y);

  return SDL_FPoint{
      .x = static_cast<float>(viewport.x + tx * viewport.w),
      .y = static_cast<float>(viewport.y + (1.0 - ty) * viewport.h),
  };
}

void draw_curve_layer(
    SDL_Renderer* renderer,
    const TrajectoryCurveLayer& layer,
    const PlotBounds& bounds,
    const SDL_FRect& viewport) {
  const auto color = parse_hex_color(layer.color_hex);
  SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);

  for (std::size_t i = 1; i < layer.points.size(); ++i) {
    const auto a = map_point(layer.points[i - 1].x_m, layer.points[i - 1].y_m, bounds, viewport);
    const auto b = map_point(layer.points[i].x_m, layer.points[i].y_m, bounds, viewport);
    SDL_RenderLine(renderer, a.x, a.y, b.x, b.y);
  }
}

void draw_icon(
    SDL_Renderer* renderer,
    const TrajectoryObjectIcon& icon,
    const PlotBounds& bounds,
    const SDL_FRect& viewport) {
  const auto color = parse_hex_color(icon.color_hex);
  SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);

  const auto p = map_point(icon.x_m, icon.y_m, bounds, viewport);
  constexpr float kHalf = 3.0F;
  SDL_FRect r{
      .x = p.x - kHalf,
      .y = p.y - kHalf,
      .w = 2.0F * kHalf,
      .h = 2.0F * kHalf,
  };
  SDL_RenderFillRect(renderer, &r);
}

void draw_event_bar(
    SDL_Renderer* renderer,
    const ReplayQuicklookWorkflowOutput& workflow,
    float x,
    float y,
    float width,
    float height) {
  if (workflow.event_markers.empty()) {
    return;
  }

  const std::size_t count = workflow.event_markers.size();
  const float bar_width = width / static_cast<float>(count);

  for (std::size_t i = 0; i < count; ++i) {
    const auto color = parse_hex_color(workflow.event_markers[i].color_hex);
    SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);
    SDL_FRect rect{
        .x = x + static_cast<float>(i) * bar_width,
        .y = y,
        .w = std::max(1.0F, bar_width - 1.0F),
        .h = height,
    };
    SDL_RenderFillRect(renderer, &rect);
  }
}

}  // namespace

bool run_replay_window(const ReplayQuicklookWorkflowOutput& workflow) {
  if (!SDL_Init(SDL_INIT_VIDEO)) {
    return false;
  }

  SDL_Window* window = SDL_CreateWindow("brambhand replay quicklook", 1280, 720, 0);
  if (window == nullptr) {
    SDL_Quit();
    return false;
  }

  SDL_Renderer* renderer = SDL_CreateRenderer(window, nullptr);
  if (renderer == nullptr) {
    SDL_DestroyWindow(window);
    SDL_Quit();
    return false;
  }

  bool running = true;
  while (running) {
    SDL_Event event;
    while (SDL_PollEvent(&event)) {
      if (event.type == SDL_EVENT_QUIT) {
        running = false;
      }
      if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_ESCAPE) {
        running = false;
      }
    }

    int width = 0;
    int height = 0;
    SDL_GetWindowSize(window, &width, &height);

    SDL_SetRenderDrawColor(renderer, 12, 14, 20, 255);
    SDL_RenderClear(renderer);

    const SDL_FRect viewport{
        .x = 40.0F,
        .y = 40.0F,
        .w = static_cast<float>(width) - 80.0F,
        .h = static_cast<float>(height) - 120.0F,
    };

    SDL_SetRenderDrawColor(renderer, 60, 66, 80, 255);
    SDL_RenderRect(renderer, &viewport);

    if (const auto bounds = compute_bounds(workflow.trajectory_panel); bounds.has_value()) {
      for (const auto& layer : workflow.trajectory_panel.curve_layers) {
        draw_curve_layer(renderer, layer, *bounds, viewport);
      }

      for (const auto& icon : workflow.trajectory_panel.object_icons) {
        draw_icon(renderer, icon, *bounds, viewport);
      }
    }

    draw_event_bar(
        renderer,
        workflow,
        viewport.x,
        viewport.y + viewport.h + 12.0F,
        viewport.w,
        16.0F);

    SDL_RenderPresent(renderer);
    SDL_Delay(16);
  }

  SDL_DestroyRenderer(renderer);
  SDL_DestroyWindow(window);
  SDL_Quit();
  return true;
}

}  // namespace brambhand::client::desktop
