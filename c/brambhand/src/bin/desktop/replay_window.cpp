#include "replay_window.hpp"

#include <SDL3/SDL.h>

#include <algorithm>
#include <array>
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

constexpr std::array<const char*, 5> kContextPlanets = {
    "mercury",
    "venus",
    "earth",
    "mars",
    "jupiter",
};

constexpr double kPi = 3.14159265358979323846;

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

Rgba color_for_body_id(const std::string& body_id) {
  if (body_id == "sun") {
    return parse_hex_color("#FFD54F");
  }
  if (body_id == "mercury") {
    return parse_hex_color("#B0BEC5");
  }
  if (body_id == "venus") {
    return parse_hex_color("#FFCC80");
  }
  if (body_id == "earth") {
    return parse_hex_color("#64B5F6");
  }
  if (body_id == "mars") {
    return parse_hex_color("#FF8A65");
  }
  if (body_id == "jupiter") {
    return parse_hex_color("#D7CCC8");
  }
  if (body_id == "planned_vehicle") {
    return parse_hex_color("#9AA4B2");
  }
  if (body_id == "current_vehicle") {
    return parse_hex_color("#FFFFFF");
  }
  return parse_hex_color("#90A4AE");
}

const brambhand::client::common::BodyState* find_body_by_id(
    const brambhand::client::common::SimulationFrame& frame,
    const std::string& body_id) {
  for (const auto& body : frame.bodies) {
    if (body.body_id == body_id) {
      return &body;
    }
  }
  return nullptr;
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

  return bounds;
}

void include_point(PlotBounds& bounds, double x, double y) {
  bounds.min_x = std::min(bounds.min_x, x);
  bounds.max_x = std::max(bounds.max_x, x);
  bounds.min_y = std::min(bounds.min_y, y);
  bounds.max_y = std::max(bounds.max_y, y);
}

PlotBounds normalize_bounds(PlotBounds bounds) {
  if (std::abs(bounds.max_x - bounds.min_x) < 1e-9) {
    bounds.max_x += 1.0;
    bounds.min_x -= 1.0;
  }
  if (std::abs(bounds.max_y - bounds.min_y) < 1e-9) {
    bounds.max_y += 1.0;
    bounds.min_y -= 1.0;
  }

  const double pad_x = 0.08 * (bounds.max_x - bounds.min_x);
  const double pad_y = 0.08 * (bounds.max_y - bounds.min_y);
  bounds.min_x -= pad_x;
  bounds.max_x += pad_x;
  bounds.min_y -= pad_y;
  bounds.max_y += pad_y;
  return bounds;
}

std::optional<PlotBounds> compute_bounds_with_context(
    const ReplayQuicklookWorkflowOutput& workflow,
    const std::vector<brambhand::client::common::SimulationFrame>& frames) {
  std::optional<PlotBounds> bounds = compute_bounds(workflow.trajectory_panel);

  if (frames.empty()) {
    if (!bounds.has_value()) {
      return std::nullopt;
    }
    return normalize_bounds(*bounds);
  }

  const auto* sun = find_body_by_id(frames.front(), "sun");
  const double sun_x = sun == nullptr ? 0.0 : sun->position_m.x;
  const double sun_y = sun == nullptr ? 0.0 : sun->position_m.y;

  if (!bounds.has_value()) {
    bounds = PlotBounds{.min_x = sun_x, .max_x = sun_x, .min_y = sun_y, .max_y = sun_y};
  }

  for (const auto& frame : frames) {
    const auto* frame_sun = find_body_by_id(frame, "sun");
    const double cx = frame_sun == nullptr ? sun_x : frame_sun->position_m.x;
    const double cy = frame_sun == nullptr ? sun_y : frame_sun->position_m.y;

    include_point(*bounds, cx, cy);
    for (const auto& body : frame.bodies) {
      include_point(*bounds, body.position_m.x, body.position_m.y);
    }

    for (const auto* name : kContextPlanets) {
      const auto* planet = find_body_by_id(frame, name);
      if (planet == nullptr) {
        continue;
      }
      const double dx = planet->position_m.x - cx;
      const double dy = planet->position_m.y - cy;
      const double r = std::sqrt(dx * dx + dy * dy);
      include_point(*bounds, cx - r, cy - r);
      include_point(*bounds, cx + r, cy + r);
    }
  }

  return normalize_bounds(*bounds);
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

void draw_circle_world(
    SDL_Renderer* renderer,
    double cx,
    double cy,
    double r,
    const PlotBounds& bounds,
    const SDL_FRect& viewport,
    const Rgba& color) {
  SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);

  constexpr int segments = 180;
  SDL_FPoint prev = map_point(cx + r, cy, bounds, viewport);
  for (int i = 1; i <= segments; ++i) {
    const double t = (2.0 * kPi * static_cast<double>(i)) / static_cast<double>(segments);
    SDL_FPoint cur = map_point(cx + r * std::cos(t), cy + r * std::sin(t), bounds, viewport);
    SDL_RenderLine(renderer, prev.x, prev.y, cur.x, cur.y);
    prev = cur;
  }
}

void draw_body_marker(
    SDL_Renderer* renderer,
    const std::string& body_id,
    double x,
    double y,
    const PlotBounds& bounds,
    const SDL_FRect& viewport,
    float half_size) {
  const auto color = color_for_body_id(body_id);
  SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);

  const auto p = map_point(x, y, bounds, viewport);
  SDL_FRect r{
      .x = p.x - half_size,
      .y = p.y - half_size,
      .w = 2.0F * half_size,
      .h = 2.0F * half_size,
  };
  SDL_RenderFillRect(renderer, &r);
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

void draw_solar_context(
    SDL_Renderer* renderer,
    const brambhand::client::common::SimulationFrame& frame,
    const PlotBounds& bounds,
    const SDL_FRect& viewport) {
  const auto* sun = find_body_by_id(frame, "sun");
  const double cx = sun == nullptr ? 0.0 : sun->position_m.x;
  const double cy = sun == nullptr ? 0.0 : sun->position_m.y;

  draw_body_marker(renderer, "sun", cx, cy, bounds, viewport, 5.0F);

  for (const auto* name : kContextPlanets) {
    const auto* planet = find_body_by_id(frame, name);
    if (planet == nullptr) {
      continue;
    }

    const double dx = planet->position_m.x - cx;
    const double dy = planet->position_m.y - cy;
    const double r = std::sqrt(dx * dx + dy * dy);

    draw_circle_world(
        renderer,
        cx,
        cy,
        r,
        bounds,
        viewport,
        parse_hex_color("#2E3B4E"));
    draw_body_marker(
        renderer,
        planet->body_id,
        planet->position_m.x,
        planet->position_m.y,
        bounds,
        viewport,
        3.0F);
  }

  if (const auto* current = find_body_by_id(frame, "current_vehicle"); current != nullptr) {
    draw_body_marker(
        renderer,
        current->body_id,
        current->position_m.x,
        current->position_m.y,
        bounds,
        viewport,
        4.0F);
  }
  if (const auto* planned = find_body_by_id(frame, "planned_vehicle"); planned != nullptr) {
    draw_body_marker(
        renderer,
        planned->body_id,
        planned->position_m.x,
        planned->position_m.y,
        bounds,
        viewport,
        3.0F);
  }
}

}  // namespace

bool run_replay_window(
    const ReplayQuicklookWorkflowOutput& workflow,
    const std::vector<brambhand::client::common::SimulationFrame>& frames) {
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

  const auto bounds_opt = compute_bounds_with_context(workflow, frames);
  if (!bounds_opt.has_value()) {
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return false;
  }
  const PlotBounds bounds = *bounds_opt;

  std::size_t frame_index = 0;
  std::uint64_t last_advance_ticks = SDL_GetTicks();

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

    const std::uint64_t now_ticks = SDL_GetTicks();
    if (!frames.empty() && now_ticks - last_advance_ticks >= 33) {
      frame_index = (frame_index + 1) % frames.size();
      last_advance_ticks = now_ticks;
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

    for (const auto& layer : workflow.trajectory_panel.curve_layers) {
      draw_curve_layer(renderer, layer, bounds, viewport);
    }

    if (!frames.empty()) {
      draw_solar_context(renderer, frames[frame_index], bounds, viewport);
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
