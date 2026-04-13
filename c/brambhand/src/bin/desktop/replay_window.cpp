#include "replay_window.hpp"

#include <SDL3/SDL.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <functional>
#include <optional>
#include <string>
#include <unordered_set>
#include <utility>
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
  const double span_x = bounds.max_x - bounds.min_x;
  const double span_y = bounds.max_y - bounds.min_y;
  const double scale = std::min(viewport.w / span_x, viewport.h / span_y);
  const double center_x = 0.5 * (bounds.min_x + bounds.max_x);
  const double center_y = 0.5 * (bounds.min_y + bounds.max_y);

  return SDL_FPoint{
      .x = static_cast<float>(viewport.x + (0.5 * viewport.w) + ((x - center_x) * scale)),
      .y = static_cast<float>(viewport.y + (0.5 * viewport.h) - ((y - center_y) * scale)),
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

std::optional<std::pair<double, double>> find_focus_point(
    const std::vector<brambhand::client::common::SimulationFrame>& frames,
    const brambhand::client::common::ReplayRenderConfig& render_config) {
  if (frames.empty() || !render_config.focus_body_id.has_value()) {
    return std::nullopt;
  }

  const auto* body = find_body_by_id(frames.front(), *render_config.focus_body_id);
  if (body == nullptr) {
    return std::nullopt;
  }

  return std::pair<double, double>{body->position_m.x, body->position_m.y};
}

void draw_trace_for_body(
    SDL_Renderer* renderer,
    const std::vector<brambhand::client::common::SimulationFrame>& frames,
    std::size_t upto_index,
    const std::string& body_id,
    const PlotBounds& bounds,
    const SDL_FRect& viewport,
    const Rgba& color,
    std::uint8_t alpha) {
  if (frames.empty()) {
    return;
  }

  SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, alpha);
  const std::size_t end = std::min(upto_index, frames.size() - 1);

  constexpr double kJumpDiscontinuityFactor = 6.0;
  constexpr double kMinReferenceDistanceM = 1.0;

  const brambhand::client::common::BodyState* prev_body = nullptr;
  std::optional<double> prev_step_distance_m;
  for (std::size_t i = 0; i <= end; ++i) {
    const auto* body = find_body_by_id(frames[i], body_id);
    if (body == nullptr) {
      prev_body = nullptr;
      prev_step_distance_m = std::nullopt;
      continue;
    }

    if (prev_body != nullptr) {
      const double dx = body->position_m.x - prev_body->position_m.x;
      const double dy = body->position_m.y - prev_body->position_m.y;
      const double distance_m = std::sqrt(dx * dx + dy * dy);

      bool draw_segment = true;
      if (prev_step_distance_m.has_value()) {
        const double reference_m = std::max(*prev_step_distance_m, kMinReferenceDistanceM);
        if (distance_m > (kJumpDiscontinuityFactor * reference_m)) {
          draw_segment = false;
        }
      }

      if (draw_segment) {
        const auto a = map_point(prev_body->position_m.x, prev_body->position_m.y, bounds, viewport);
        const auto b = map_point(body->position_m.x, body->position_m.y, bounds, viewport);
        SDL_RenderLine(renderer, a.x, a.y, b.x, b.y);
      }

      prev_step_distance_m = distance_m;
    }

    prev_body = body;
  }
}

enum class MarkerKind {
  Generic,
  Probe,
  Planet,
  Sun,
};

void draw_circle_outline(SDL_Renderer* renderer, float cx, float cy, float radius, int segments) {
  constexpr double kTau = 6.283185307179586;
  for (int i = 0; i < segments; ++i) {
    const float a0 = static_cast<float>((kTau * static_cast<double>(i)) / static_cast<double>(segments));
    const float a1 = static_cast<float>((kTau * static_cast<double>(i + 1)) / static_cast<double>(segments));
    SDL_RenderLine(
        renderer,
        cx + (radius * std::cos(a0)),
        cy + (radius * std::sin(a0)),
        cx + (radius * std::cos(a1)),
        cy + (radius * std::sin(a1)));
  }
}

void draw_body_marker(
    SDL_Renderer* renderer,
    const brambhand::client::common::BodyState& body,
    const PlotBounds& bounds,
    const SDL_FRect& viewport,
    float half_size,
    bool draw_label,
    MarkerKind marker_kind) {
  const auto color = color_for_id(body.body_id);
  SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);

  const auto p = map_point(body.position_m.x, body.position_m.y, bounds, viewport);

  if (marker_kind == MarkerKind::Sun) {
    draw_circle_outline(renderer, p.x, p.y, half_size + 2.0F, 14);
    SDL_RenderLine(renderer, p.x - (half_size + 4.0F), p.y, p.x + (half_size + 4.0F), p.y);
    SDL_RenderLine(renderer, p.x, p.y - (half_size + 4.0F), p.x, p.y + (half_size + 4.0F));
  } else if (marker_kind == MarkerKind::Planet) {
    draw_circle_outline(renderer, p.x, p.y, half_size + 1.5F, 12);
    SDL_RenderPoint(renderer, p.x, p.y);
  } else if (marker_kind == MarkerKind::Probe) {
    SDL_RenderLine(renderer, p.x, p.y - (half_size + 2.0F), p.x - (half_size + 2.0F), p.y + (half_size + 2.0F));
    SDL_RenderLine(renderer, p.x - (half_size + 2.0F), p.y + (half_size + 2.0F), p.x + (half_size + 2.0F), p.y + (half_size + 2.0F));
    SDL_RenderLine(renderer, p.x + (half_size + 2.0F), p.y + (half_size + 2.0F), p.x, p.y - (half_size + 2.0F));
  } else {
    SDL_FRect r{
        .x = p.x - half_size,
        .y = p.y - half_size,
        .w = 2.0F * half_size,
        .h = 2.0F * half_size,
    };
    SDL_RenderFillRect(renderer, &r);
  }

  if (draw_label) {
    SDL_RenderDebugText(renderer, p.x + 5.0F, p.y - 5.0F, body.body_id.c_str());
  }
}

std::string elide_text(const std::string& text, std::size_t max_chars) {
  if (max_chars == 0) {
    return {};
  }
  if (text.size() <= max_chars) {
    return text;
  }
  if (max_chars <= 3) {
    return text.substr(0, max_chars);
  }
  return text.substr(0, max_chars - 3) + "...";
}

bool draw_sidebar_line(
    SDL_Renderer* renderer,
    float x,
    float& y,
    float y_limit,
    float line_h,
    std::size_t max_chars,
    const std::string& text) {
  if (y + line_h > y_limit) {
    return false;
  }
  const std::string clipped = elide_text(text, max_chars);
  SDL_RenderDebugText(renderer, x, y, clipped.c_str());
  y += line_h;
  return true;
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
  SDL_SetRenderDrawColor(renderer, 20, 24, 34, 255);
  SDL_RenderFillRect(renderer, &panel);
  SDL_SetRenderDrawColor(renderer, 78, 90, 110, 255);
  SDL_RenderRect(renderer, &panel);

  const SDL_Rect clip_rect{
      static_cast<int>(panel.x) + 1,
      static_cast<int>(panel.y) + 1,
      std::max(1, static_cast<int>(panel.w) - 2),
      std::max(1, static_cast<int>(panel.h) - 2),
  };
  SDL_SetRenderClipRect(renderer, &clip_rect);

  constexpr float kMargin = 10.0F;
  constexpr float kLineH = 16.0F;
  constexpr float kRowH = 14.0F;
  constexpr float kCharW = 8.0F;

  const float x = panel.x + kMargin;
  float y = panel.y + kMargin;
  const float y_limit = panel.y + panel.h - kMargin;
  const float right = panel.x + panel.w - kMargin;
  const std::size_t max_chars = static_cast<std::size_t>(
      std::max(6.0F, (panel.w - (2.0F * kMargin)) / kCharW));

  auto set_primary = [&]() { SDL_SetRenderDrawColor(renderer, 228, 236, 250, 255); };
  auto set_secondary = [&]() { SDL_SetRenderDrawColor(renderer, 150, 164, 186, 255); };
  auto set_muted = [&]() { SDL_SetRenderDrawColor(renderer, 124, 136, 156, 255); };

  auto draw_primary = [&](const std::string& line) {
    set_primary();
    return draw_sidebar_line(renderer, x, y, y_limit, kLineH, max_chars, line);
  };
  auto draw_secondary = [&](const std::string& line) {
    set_secondary();
    return draw_sidebar_line(renderer, x, y, y_limit, kLineH, max_chars, line);
  };
  auto draw_divider = [&]() {
    if (y + 8.0F > y_limit) {
      return false;
    }
    SDL_SetRenderDrawColor(renderer, 62, 72, 90, 255);
    SDL_RenderLine(renderer, x, y + 3.0F, right, y + 3.0F);
    y += 8.0F;
    return true;
  };

  if (!draw_primary("Replay Quicklook")) {
    SDL_SetRenderClipRect(renderer, nullptr);
    return;
  }

  {
    char buf[128];
    std::snprintf(buf, sizeof(buf), "Bodies tracked: %zu", body_ids.size());
    if (!draw_secondary(buf)) {
      SDL_SetRenderClipRect(renderer, nullptr);
      return;
    }
  }

  if (!draw_secondary("Replay window telemetry")) {
    SDL_SetRenderClipRect(renderer, nullptr);
    return;
  }

  if (!draw_divider()) {
    SDL_SetRenderClipRect(renderer, nullptr);
    return;
  }

  if (!draw_primary("Simulation")) {
    SDL_SetRenderClipRect(renderer, nullptr);
    return;
  }

  if (active_frame != nullptr) {
    char buf[128];
    std::snprintf(buf, sizeof(buf), "Sim day: %.1f", active_frame->sim_time_s / kSecondsPerDay);
    if (!draw_secondary(buf)) {
      SDL_SetRenderClipRect(renderer, nullptr);
      return;
    }
  }

  {
    char buf[128];
    std::snprintf(buf, sizeof(buf), "Frame: %zu / %zu", frame_index + 1, frame_count);
    if (!draw_secondary(buf)) {
      SDL_SetRenderClipRect(renderer, nullptr);
      return;
    }
    std::snprintf(buf, sizeof(buf), "Playback: %.2fx  ([ / ])", playback_rate);
    if (!draw_secondary(buf)) {
      SDL_SetRenderClipRect(renderer, nullptr);
      return;
    }
    std::snprintf(buf, sizeof(buf), "Zoom: %.2fx  (-/= or wheel)", zoom_level);
    if (!draw_secondary(buf)) {
      SDL_SetRenderClipRect(renderer, nullptr);
      return;
    }
  }

  if (!draw_secondary("Pan: arrow keys")) {
    SDL_SetRenderClipRect(renderer, nullptr);
    return;
  }

  if (!draw_divider()) {
    SDL_SetRenderClipRect(renderer, nullptr);
    return;
  }

  if (!draw_primary("Mission Events")) {
    SDL_SetRenderClipRect(renderer, nullptr);
    return;
  }
  if (!draw_secondary("Severity color + timeline row")) {
    SDL_SetRenderClipRect(renderer, nullptr);
    return;
  }

  std::size_t event_i = 0;
  const std::size_t event_text_max = max_chars > 2 ? max_chars - 2 : max_chars;
  while (event_i < workflow.event_markers.size() && (y + kRowH) <= y_limit) {
    const auto& m = workflow.event_markers[event_i];
    const auto color = parse_hex_color(m.color_hex);
    SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);
    SDL_FRect swatch{.x = x, .y = y + 2.0F, .w = 10.0F, .h = 10.0F};
    SDL_RenderFillRect(renderer, &swatch);

    char row[256];
    std::snprintf(row, sizeof(row), "t=%.1fd  %s", m.sim_time_s / kSecondsPerDay, m.kind.c_str());
    const std::string clipped = elide_text(row, event_text_max);
    set_secondary();
    SDL_RenderDebugText(renderer, x + 14.0F, y, clipped.c_str());
    y += kRowH;
    ++event_i;
  }

  if (event_i < workflow.event_markers.size() && (y + kLineH) <= y_limit) {
    set_muted();
    SDL_RenderDebugText(renderer, x, y, "...");
    y += kLineH;
  }

  if (!draw_divider()) {
    SDL_SetRenderClipRect(renderer, nullptr);
    return;
  }

  if (!draw_primary("Body Legend")) {
    SDL_SetRenderClipRect(renderer, nullptr);
    return;
  }

  for (std::size_t i = 0; i < body_ids.size() && (y + kRowH) <= y_limit; ++i) {
    const auto color = color_for_id(body_ids[i]);
    SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);
    SDL_FRect swatch{.x = x, .y = y + 2.0F, .w = 10.0F, .h = 10.0F};
    SDL_RenderFillRect(renderer, &swatch);
    const std::string clipped = elide_text(body_ids[i], event_text_max);
    set_secondary();
    SDL_RenderDebugText(renderer, x + 14.0F, y, clipped.c_str());
    y += kRowH;
  }

  SDL_SetRenderClipRect(renderer, nullptr);
}

}  // namespace

bool run_replay_window(
    const ReplayQuicklookWorkflowOutput& workflow,
    const std::vector<brambhand::client::common::SimulationFrame>& frames,
    const brambhand::client::common::ReplayRenderConfig& render_config) {
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

  const std::unordered_set<std::string> orbit_body_id_set(
      render_config.dim_trajectory_body_ids.begin(),
      render_config.dim_trajectory_body_ids.end());
  const std::unordered_set<std::string> sun_body_id_set(
      render_config.sun_body_ids.begin(),
      render_config.sun_body_ids.end());
  const std::unordered_set<std::string> planet_body_id_set(
      render_config.planet_body_ids.begin(),
      render_config.planet_body_ids.end());
  const std::unordered_set<std::string> probe_body_id_set(
      render_config.probe_body_ids.begin(),
      render_config.probe_body_ids.end());
  std::vector<std::string> orbit_body_ids;
  orbit_body_ids.reserve(orbit_body_id_set.size());
  for (const auto& id : body_ids) {
    if (orbit_body_id_set.contains(id)) {
      orbit_body_ids.push_back(id);
    }
  }

  const auto focus_point = find_focus_point(frames, render_config);
  const double base_center_x = 0.5 * (base_bounds.min_x + base_bounds.max_x);
  const double base_center_y = 0.5 * (base_bounds.min_y + base_bounds.max_y);

  std::size_t frame_index = 0;
  std::uint64_t last_advance_ticks = SDL_GetTicks();
  double playback_rate = 1.0;
  double zoom_level = 1.0;
  double pan_x = focus_point.has_value() ? (focus_point->first - base_center_x) : 0.0;
  double pan_y = focus_point.has_value() ? (focus_point->second - base_center_y) : 0.0;

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

    const float outer_margin = 20.0F;
    const float panel_gap = 10.0F;
    const float min_view_w = 180.0F;
    const float preferred_sidebar_w = 330.0F;

    float sidebar_w = std::clamp(
        preferred_sidebar_w,
        180.0F,
        std::max(180.0F, static_cast<float>(width) - (2.0F * outer_margin) - panel_gap - min_view_w));
    float viewport_w = static_cast<float>(width) - (2.0F * outer_margin) - panel_gap - sidebar_w;
    if (viewport_w < min_view_w) {
      viewport_w = min_view_w;
      sidebar_w = std::max(180.0F, static_cast<float>(width) - (2.0F * outer_margin) - panel_gap - viewport_w);
    }

    const SDL_FRect viewport{
        .x = outer_margin,
        .y = outer_margin,
        .w = std::max(120.0F, viewport_w),
        .h = std::max(120.0F, static_cast<float>(height) - (2.0F * outer_margin)),
    };
    const SDL_FRect sidebar{
        .x = viewport.x + viewport.w + panel_gap,
        .y = outer_margin,
        .w = std::max(140.0F, sidebar_w),
        .h = std::max(120.0F, static_cast<float>(height) - (2.0F * outer_margin)),
    };

    SDL_SetRenderDrawColor(renderer, 60, 66, 80, 255);
    SDL_RenderRect(renderer, &viewport);

    const PlotBounds view_bounds = make_view_bounds(base_bounds, zoom_level, pan_x, pan_y);

    for (const auto& layer : workflow.trajectory_panel.curve_layers) {
      draw_curve_layer(renderer, layer, view_bounds, viewport);
    }

    const brambhand::client::common::SimulationFrame* active_frame = nullptr;
    if (!frames.empty()) {
      for (const auto& id : orbit_body_ids) {
        draw_trace_for_body(
            renderer,
            frames,
            frames.size() - 1,
            id,
            view_bounds,
            viewport,
            color_for_id(id),
            85);
      }

      for (const auto& id : body_ids) {
        draw_trace_for_body(
            renderer,
            frames,
            frame_index,
            id,
            view_bounds,
            viewport,
            color_for_id(id),
            180);
      }

      active_frame = &frames[frame_index];
      for (const auto& body : active_frame->bodies) {
        MarkerKind marker_kind = MarkerKind::Generic;
        if (sun_body_id_set.contains(body.body_id)) {
          marker_kind = MarkerKind::Sun;
        } else if (probe_body_id_set.contains(body.body_id)) {
          marker_kind = MarkerKind::Probe;
        } else if (planet_body_id_set.contains(body.body_id)) {
          marker_kind = MarkerKind::Planet;
        }

        draw_body_marker(renderer, body, view_bounds, viewport, 3.0F, false, marker_kind);
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
