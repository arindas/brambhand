#include "replay_window.hpp"

#include <SDL3/SDL.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <functional>
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

constexpr double kSecondsPerDay = 86400.0;

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

Rgba hsv_to_rgb(double h, double s, double v) {
  const double c = v * s;
  const double hh = h / 60.0;
  const double x = c * (1.0 - std::abs(std::fmod(hh, 2.0) - 1.0));

  double r = 0.0;
  double g = 0.0;
  double b = 0.0;

  if (0.0 <= hh && hh < 1.0) {
    r = c;
    g = x;
  } else if (1.0 <= hh && hh < 2.0) {
    r = x;
    g = c;
  } else if (2.0 <= hh && hh < 3.0) {
    g = c;
    b = x;
  } else if (3.0 <= hh && hh < 4.0) {
    g = x;
    b = c;
  } else if (4.0 <= hh && hh < 5.0) {
    r = x;
    b = c;
  } else {
    r = c;
    b = x;
  }

  const double m = v - c;
  return Rgba{
      .r = static_cast<std::uint8_t>(255.0 * (r + m)),
      .g = static_cast<std::uint8_t>(255.0 * (g + m)),
      .b = static_cast<std::uint8_t>(255.0 * (b + m)),
      .a = 255,
  };
}

Rgba color_for_id(const std::string& id) {
  const std::uint64_t h = std::hash<std::string>{}(id);
  const double hue = static_cast<double>(h % 360ULL);
  return hsv_to_rgb(hue, 0.55, 0.95);
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

std::vector<std::string> collect_body_ids(
    const std::vector<brambhand::client::common::SimulationFrame>& frames) {
  std::vector<std::string> ids;
  for (const auto& frame : frames) {
    for (const auto& body : frame.bodies) {
      if (std::find(ids.begin(), ids.end(), body.body_id) == ids.end()) {
        ids.push_back(body.body_id);
      }
    }
  }
  std::sort(ids.begin(), ids.end());
  return ids;
}

void include_point(PlotBounds& bounds, double x, double y, bool& initialized) {
  if (!initialized) {
    bounds.min_x = bounds.max_x = x;
    bounds.min_y = bounds.max_y = y;
    initialized = true;
    return;
  }

  bounds.min_x = std::min(bounds.min_x, x);
  bounds.max_x = std::max(bounds.max_x, x);
  bounds.min_y = std::min(bounds.min_y, y);
  bounds.max_y = std::max(bounds.max_y, y);
}

std::optional<PlotBounds> compute_bounds(
    const ReplayQuicklookWorkflowOutput& workflow,
    const std::vector<brambhand::client::common::SimulationFrame>& frames) {
  bool initialized = false;
  PlotBounds bounds{};

  for (const auto& layer : workflow.trajectory_panel.curve_layers) {
    for (const auto& point : layer.points) {
      include_point(bounds, point.x_m, point.y_m, initialized);
    }
  }

  for (const auto& frame : frames) {
    for (const auto& body : frame.bodies) {
      include_point(bounds, body.position_m.x, body.position_m.y, initialized);
    }
  }

  if (!initialized) {
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

  const double pad_x = 0.08 * (bounds.max_x - bounds.min_x);
  const double pad_y = 0.08 * (bounds.max_y - bounds.min_y);
  bounds.min_x -= pad_x;
  bounds.max_x += pad_x;
  bounds.min_y -= pad_y;
  bounds.max_y += pad_y;
  return bounds;
}

PlotBounds make_view_bounds(
    const PlotBounds& base,
    double zoom,
    double pan_x,
    double pan_y) {
  const double base_span_x = base.max_x - base.min_x;
  const double base_span_y = base.max_y - base.min_y;
  const double cx = 0.5 * (base.min_x + base.max_x) + pan_x;
  const double cy = 0.5 * (base.min_y + base.max_y) + pan_y;
  const double half_x = 0.5 * base_span_x / zoom;
  const double half_y = 0.5 * base_span_y / zoom;
  return PlotBounds{
      .min_x = cx - half_x,
      .max_x = cx + half_x,
      .min_y = cy - half_y,
      .max_y = cy + half_y,
  };
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

void draw_trace_for_body(
    SDL_Renderer* renderer,
    const std::vector<brambhand::client::common::SimulationFrame>& frames,
    std::size_t upto_index,
    const std::string& body_id,
    const PlotBounds& bounds,
    const SDL_FRect& viewport,
    const Rgba& color) {
  if (frames.empty()) {
    return;
  }

  SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, 170);
  const std::size_t end = std::min(upto_index, frames.size() - 1);

  const brambhand::client::common::BodyState* prev_body = nullptr;
  for (std::size_t i = 0; i <= end; ++i) {
    const auto* body = find_body_by_id(frames[i], body_id);
    if (body == nullptr) {
      prev_body = nullptr;
      continue;
    }

    if (prev_body != nullptr) {
      const auto a = map_point(prev_body->position_m.x, prev_body->position_m.y, bounds, viewport);
      const auto b = map_point(body->position_m.x, body->position_m.y, bounds, viewport);
      SDL_RenderLine(renderer, a.x, a.y, b.x, b.y);
    }

    prev_body = body;
  }
}

void draw_body_marker(
    SDL_Renderer* renderer,
    const brambhand::client::common::BodyState& body,
    const PlotBounds& bounds,
    const SDL_FRect& viewport,
    float half_size,
    bool draw_label) {
  const auto color = color_for_id(body.body_id);
  SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);

  const auto p = map_point(body.position_m.x, body.position_m.y, bounds, viewport);
  SDL_FRect r{
      .x = p.x - half_size,
      .y = p.y - half_size,
      .w = 2.0F * half_size,
      .h = 2.0F * half_size,
  };
  SDL_RenderFillRect(renderer, &r);

  if (draw_label) {
    SDL_RenderDebugText(renderer, p.x + 5.0F, p.y - 5.0F, body.body_id.c_str());
  }
}

void draw_sidebar(
    SDL_Renderer* renderer,
    const SDL_FRect& panel,
    const ReplayQuicklookWorkflowOutput& workflow,
    const brambhand::client::common::SimulationFrame* active_frame,
    std::size_t frame_index,
    std::size_t frame_count,
    double playback_rate,
    double zoom_level,
    const std::vector<std::string>& body_ids) {
  SDL_SetRenderDrawColor(renderer, 22, 28, 40, 255);
  SDL_RenderFillRect(renderer, &panel);
  SDL_SetRenderDrawColor(renderer, 70, 80, 96, 255);
  SDL_RenderRect(renderer, &panel);

  float x = panel.x + 10.0F;
  float y = panel.y + 10.0F;
  SDL_RenderDebugText(renderer, x, y, "Replay Quicklook");
  y += 16.0F;
  SDL_RenderDebugTextFormat(renderer, x, y, "Bodies tracked: %zu", body_ids.size());
  y += 16.0F;
  SDL_RenderDebugText(renderer, x, y, "Trajectories + traces are replay-driven");
  y += 20.0F;

  if (active_frame != nullptr) {
    const double day = active_frame->sim_time_s / kSecondsPerDay;
    SDL_RenderDebugTextFormat(renderer, x, y, "Sim day: %.1f", day);
    y += 16.0F;
  }
  SDL_RenderDebugTextFormat(renderer, x, y, "Frame: %zu / %zu", frame_index + 1, frame_count);
  y += 16.0F;
  SDL_RenderDebugTextFormat(renderer, x, y, "Playback: %.2fx  ([ and ])", playback_rate);
  y += 16.0F;
  SDL_RenderDebugTextFormat(renderer, x, y, "Zoom: %.2fx  (-/= or wheel)", zoom_level);
  y += 16.0F;
  SDL_RenderDebugText(renderer, x, y, "Pan: arrow keys");
  y += 22.0F;

  SDL_RenderDebugText(renderer, x, y, "Mission/Event timeline");
  y += 16.0F;
  SDL_RenderDebugText(renderer, x, y, "Color = severity, row = event record");
  y += 18.0F;

  const float row_h = 14.0F;
  const std::size_t show = std::min<std::size_t>(workflow.event_markers.size(), 16);
  for (std::size_t i = 0; i < show; ++i) {
    const auto& m = workflow.event_markers[i];
    const auto color = parse_hex_color(m.color_hex);
    SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);
    SDL_FRect swatch{.x = x, .y = y + 2.0F, .w = 10.0F, .h = 10.0F};
    SDL_RenderFillRect(renderer, &swatch);

    SDL_RenderDebugTextFormat(
        renderer,
        x + 14.0F,
        y,
        "t=%.1fd  %s",
        m.sim_time_s / kSecondsPerDay,
        m.kind.c_str());
    y += row_h;
  }

  y += 8.0F;
  SDL_RenderDebugText(renderer, x, y, "Body color legend");
  y += 16.0F;
  const std::size_t legend_show = std::min<std::size_t>(body_ids.size(), 10);
  for (std::size_t i = 0; i < legend_show; ++i) {
    const auto color = color_for_id(body_ids[i]);
    SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);
    SDL_FRect swatch{.x = x, .y = y + 2.0F, .w = 10.0F, .h = 10.0F};
    SDL_RenderFillRect(renderer, &swatch);
    SDL_RenderDebugText(renderer, x + 14.0F, y, body_ids[i].c_str());
    y += row_h;
  }
}

}  // namespace

bool run_replay_window(
    const ReplayQuicklookWorkflowOutput& workflow,
    const std::vector<brambhand::client::common::SimulationFrame>& frames) {
  if (!SDL_Init(SDL_INIT_VIDEO)) {
    return false;
  }

  const SDL_WindowFlags flags = SDL_WINDOW_RESIZABLE | SDL_WINDOW_MAXIMIZED;
  SDL_Window* window = SDL_CreateWindow("brambhand replay quicklook", 1280, 720, flags);
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

  const auto bounds_opt = compute_bounds(workflow, frames);
  if (!bounds_opt.has_value()) {
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return false;
  }
  const PlotBounds base_bounds = *bounds_opt;
  const std::vector<std::string> body_ids = collect_body_ids(frames);

  std::size_t frame_index = 0;
  std::uint64_t last_advance_ticks = SDL_GetTicks();
  double playback_rate = 1.0;
  double zoom_level = 1.0;
  double pan_x = 0.0;
  double pan_y = 0.0;

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
      if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_LEFTBRACKET) {
        playback_rate = std::max(0.25, playback_rate * 0.5);
      }
      if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_RIGHTBRACKET) {
        playback_rate = std::min(16.0, playback_rate * 2.0);
      }
      if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_EQUALS) {
        zoom_level = std::min(64.0, zoom_level * 1.2);
      }
      if (event.type == SDL_EVENT_KEY_DOWN && event.key.key == SDLK_MINUS) {
        zoom_level = std::max(0.2, zoom_level / 1.2);
      }
      if (event.type == SDL_EVENT_MOUSE_WHEEL) {
        if (event.wheel.y > 0.0F) {
          zoom_level = std::min(64.0, zoom_level * 1.1);
        } else if (event.wheel.y < 0.0F) {
          zoom_level = std::max(0.2, zoom_level / 1.1);
        }
      }
    }

    const double span_x = (base_bounds.max_x - base_bounds.min_x) / zoom_level;
    const double span_y = (base_bounds.max_y - base_bounds.min_y) / zoom_level;

    const bool left = SDL_GetKeyboardState(nullptr)[SDL_SCANCODE_LEFT];
    const bool right = SDL_GetKeyboardState(nullptr)[SDL_SCANCODE_RIGHT];
    const bool up = SDL_GetKeyboardState(nullptr)[SDL_SCANCODE_UP];
    const bool down = SDL_GetKeyboardState(nullptr)[SDL_SCANCODE_DOWN];
    const double pan_step_x = 0.04 * span_x;
    const double pan_step_y = 0.04 * span_y;
    if (left) {
      pan_x -= pan_step_x;
    }
    if (right) {
      pan_x += pan_step_x;
    }
    if (up) {
      pan_y += pan_step_y;
    }
    if (down) {
      pan_y -= pan_step_y;
    }

    const std::uint64_t now_ticks = SDL_GetTicks();
    const std::uint64_t frame_period_ms = static_cast<std::uint64_t>(std::max(1.0, 33.0 / playback_rate));
    if (!frames.empty() && now_ticks - last_advance_ticks >= frame_period_ms) {
      frame_index = (frame_index + 1) % frames.size();
      last_advance_ticks = now_ticks;
    }

    int width = 0;
    int height = 0;
    SDL_GetWindowSize(window, &width, &height);

    SDL_SetRenderDrawColor(renderer, 12, 14, 20, 255);
    SDL_RenderClear(renderer);

    const float sidebar_w = 360.0F;
    const SDL_FRect viewport{
        .x = 20.0F,
        .y = 20.0F,
        .w = std::max(200.0F, static_cast<float>(width) - sidebar_w - 40.0F),
        .h = static_cast<float>(height) - 40.0F,
    };
    const SDL_FRect sidebar{
        .x = viewport.x + viewport.w + 10.0F,
        .y = 20.0F,
        .w = sidebar_w - 30.0F,
        .h = static_cast<float>(height) - 40.0F,
    };

    SDL_SetRenderDrawColor(renderer, 60, 66, 80, 255);
    SDL_RenderRect(renderer, &viewport);

    const PlotBounds view_bounds = make_view_bounds(base_bounds, zoom_level, pan_x, pan_y);

    for (const auto& layer : workflow.trajectory_panel.curve_layers) {
      draw_curve_layer(renderer, layer, view_bounds, viewport);
    }

    const brambhand::client::common::SimulationFrame* active_frame = nullptr;
    if (!frames.empty()) {
      for (const auto& id : body_ids) {
        draw_trace_for_body(
            renderer,
            frames,
            frame_index,
            id,
            view_bounds,
            viewport,
            color_for_id(id));
      }

      active_frame = &frames[frame_index];
      for (const auto& body : active_frame->bodies) {
        draw_body_marker(renderer, body, view_bounds, viewport, 3.0F, true);
      }
    }

    draw_sidebar(
        renderer,
        sidebar,
        workflow,
        active_frame,
        frame_index,
        frames.empty() ? 0 : frames.size(),
        playback_rate,
        zoom_level,
        body_ids);

    SDL_RenderPresent(renderer);
    SDL_Delay(16);
  }

  SDL_DestroyRenderer(renderer);
  SDL_DestroyWindow(window);
  SDL_Quit();
  return true;
}

}  // namespace brambhand::client::desktop
