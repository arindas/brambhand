#include "replay_window.hpp"

#include "quicklook_frame_state.hpp"
#include "quicklook_runtime.hpp"
#include "renderer_capability_profile.hpp"
#include "ui_layout.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <functional>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "brambhand/client/common/plot_geometry.hpp"
#include "brambhand/client/common/render_semantics.hpp"

namespace brambhand::client::desktop {
namespace {

using PlotBounds = brambhand::client::common::PlotBounds;
using Rgba = CanvasColor;

constexpr double kSecondsPerDay = 86400.0;

constexpr std::array<std::uint8_t, 256> build_hex_lut() {
  std::array<std::uint8_t, 256> lut{};
  for (std::size_t i = 0; i < lut.size(); ++i) {
    lut[i] = 0;
  }
  for (std::uint8_t d = 0; d < 10; ++d) {
    lut[static_cast<std::size_t>('0' + d)] = d;
  }
  for (std::uint8_t d = 0; d < 6; ++d) {
    lut[static_cast<std::size_t>('a' + d)] = static_cast<std::uint8_t>(10 + d);
    lut[static_cast<std::size_t>('A' + d)] = static_cast<std::uint8_t>(10 + d);
  }
  return lut;
}

constexpr auto kHexLut = build_hex_lut();

Rgba parse_hex_color(const std::string& hex) {
  if (hex.size() != 7 || hex[0] != '#') {
    return Rgba{.r = 255, .g = 255, .b = 255, .a = 255};
  }

  const auto parse_pair = [&](std::size_t idx) {
    const auto hi = kHexLut[static_cast<unsigned char>(hex[idx])];
    const auto lo = kHexLut[static_cast<unsigned char>(hex[idx + 1])];
    return static_cast<std::uint8_t>((hi << 4) | lo);
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

  const int sector = static_cast<int>(std::floor(hh)) % 6;
  switch (sector < 0 ? sector + 6 : sector) {
    case 0:
      r = c;
      g = x;
      break;
    case 1:
      r = x;
      g = c;
      break;
    case 2:
      g = c;
      b = x;
      break;
    case 3:
      g = x;
      b = c;
      break;
    case 4:
      r = x;
      b = c;
      break;
    default:
      r = c;
      b = x;
      break;
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

std::optional<PlotBounds> compute_bounds(
    const ReplayQuicklookWorkflowOutput& workflow,
    const std::vector<brambhand::client::common::SimulationFrame>& frames) {
  bool initialized = false;
  PlotBounds bounds{};

  for (const auto& layer : workflow.trajectory_panel.curve_layers) {
    for (const auto& point : layer.points) {
      brambhand::client::common::include_plot_point(bounds, point.x_m, point.y_m, initialized);
    }
  }

  for (const auto& frame : frames) {
    for (const auto& body : frame.bodies) {
      brambhand::client::common::include_plot_point(bounds, body.position_m.x, body.position_m.y, initialized);
    }
  }

  return brambhand::client::common::finalize_plot_bounds(bounds, initialized);
}

CanvasPoint map_point(
    double x,
    double y,
    const PlotBounds& bounds,
    const CanvasRect& viewport) {
  const auto mapped = brambhand::client::common::map_plot_point(
      x,
      y,
      bounds,
      brambhand::client::common::ViewRect{
          .x = viewport.x,
          .y = viewport.y,
          .w = viewport.w,
          .h = viewport.h,
      });
  return CanvasPoint{.x = mapped.x, .y = mapped.y};
}

void draw_curve_layer(
    QuicklookCanvas& canvas,
    const TrajectoryCurveLayer& layer,
    const PlotBounds& bounds,
    const CanvasRect& viewport) {
  const auto color = parse_hex_color(layer.color_hex);
  canvas.set_draw_color(color);

  for (std::size_t i = 1; i < layer.points.size(); ++i) {
    const auto a = map_point(layer.points[i - 1].x_m, layer.points[i - 1].y_m, bounds, viewport);
    const auto b = map_point(layer.points[i].x_m, layer.points[i].y_m, bounds, viewport);
    canvas.draw_line(a.x, a.y, b.x, b.y);
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
    QuicklookCanvas& canvas,
    const std::vector<brambhand::client::common::SimulationFrame>& frames,
    std::size_t upto_index,
    const std::string& body_id,
    const PlotBounds& bounds,
    const CanvasRect& viewport,
    const Rgba& color,
    std::uint8_t alpha,
    const QuicklookTracePolicy& trace_policy) {
  if (frames.empty()) {
    return;
  }

  canvas.set_draw_color(CanvasColor{.r = color.r, .g = color.g, .b = color.b, .a = alpha});
  const std::size_t end = std::min(upto_index, frames.size() - 1);

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

      const bool draw_segment =
          trace_policy.should_draw_segment(distance_m, prev_step_distance_m);

      if (draw_segment) {
        const auto a = map_point(prev_body->position_m.x, prev_body->position_m.y, bounds, viewport);
        const auto b = map_point(body->position_m.x, body->position_m.y, bounds, viewport);
        canvas.draw_line(a.x, a.y, b.x, b.y);
      }

      prev_step_distance_m = distance_m;
    }

    prev_body = body;
  }
}

void draw_circle_outline(QuicklookCanvas& canvas, float cx, float cy, float radius, int segments) {
  constexpr double kTau = 6.283185307179586;
  for (int i = 0; i < segments; ++i) {
    const float a0 = static_cast<float>((kTau * static_cast<double>(i)) / static_cast<double>(segments));
    const float a1 = static_cast<float>((kTau * static_cast<double>(i + 1)) / static_cast<double>(segments));
    canvas.draw_line(
        cx + (radius * std::cos(a0)),
        cy + (radius * std::sin(a0)),
        cx + (radius * std::cos(a1)),
        cy + (radius * std::sin(a1)));
  }
}

void draw_body_marker(
    QuicklookCanvas& canvas,
    const brambhand::client::common::BodyState& body,
    const PlotBounds& bounds,
    const CanvasRect& viewport,
    float half_size,
    bool draw_label,
    brambhand::client::common::BodyRenderRole marker_kind) {
  const auto color = color_for_id(body.body_id);
  canvas.set_draw_color(color);

  const auto p = map_point(body.position_m.x, body.position_m.y, bounds, viewport);

  if (marker_kind == brambhand::client::common::BodyRenderRole::Sun) {
    draw_circle_outline(canvas, p.x, p.y, half_size + 2.0F, 14);
    canvas.draw_line(p.x - (half_size + 4.0F), p.y, p.x + (half_size + 4.0F), p.y);
    canvas.draw_line(p.x, p.y - (half_size + 4.0F), p.x, p.y + (half_size + 4.0F));
  } else if (marker_kind == brambhand::client::common::BodyRenderRole::Planet) {
    draw_circle_outline(canvas, p.x, p.y, half_size + 1.5F, 12);
    canvas.draw_point(p.x, p.y);
  } else if (marker_kind == brambhand::client::common::BodyRenderRole::Probe) {
    canvas.draw_line(p.x, p.y - (half_size + 2.0F), p.x - (half_size + 2.0F), p.y + (half_size + 2.0F));
    canvas.draw_line(
        p.x - (half_size + 2.0F),
        p.y + (half_size + 2.0F),
        p.x + (half_size + 2.0F),
        p.y + (half_size + 2.0F));
    canvas.draw_line(p.x + (half_size + 2.0F), p.y + (half_size + 2.0F), p.x, p.y - (half_size + 2.0F));
  } else {
    CanvasRect r{
        .x = p.x - half_size,
        .y = p.y - half_size,
        .w = 2.0F * half_size,
        .h = 2.0F * half_size,
    };
    canvas.fill_rect(r);
  }

  if (draw_label) {
    canvas.draw_text(p.x + 5.0F, p.y - 5.0F, body.body_id);
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
    QuicklookCanvas& canvas,
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
  canvas.draw_text(x, y, clipped);
  y += line_h;
  return true;
}

void draw_sidebar(
    QuicklookCanvas& canvas,
    const CanvasRect& panel,
    const ReplayQuicklookWorkflowOutput& workflow,
    const brambhand::client::common::SimulationFrame* active_frame,
    std::size_t frame_index,
    std::size_t frame_count,
    double playback_rate,
    double zoom_level,
    const std::vector<std::string>& body_ids,
    const QuicklookSidebarPolicy& sidebar_policy) {
  canvas.set_draw_color(CanvasColor{.r = 20, .g = 24, .b = 34, .a = 255});
  canvas.fill_rect(panel);
  canvas.set_draw_color(CanvasColor{.r = 78, .g = 90, .b = 110, .a = 255});
  canvas.draw_rect(panel);

  canvas.set_clip_rect(CanvasRect{
      .x = panel.x + 1.0F,
      .y = panel.y + 1.0F,
      .w = std::max(1.0F, panel.w - 2.0F),
      .h = std::max(1.0F, panel.h - 2.0F),
  });

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

  auto set_primary = [&]() { canvas.set_draw_color(CanvasColor{.r = 228, .g = 236, .b = 250, .a = 255}); };
  auto set_secondary = [&]() { canvas.set_draw_color(CanvasColor{.r = 150, .g = 164, .b = 186, .a = 255}); };
  auto set_muted = [&]() { canvas.set_draw_color(CanvasColor{.r = 124, .g = 136, .b = 156, .a = 255}); };

  auto draw_primary = [&](const std::string& line) {
    set_primary();
    return draw_sidebar_line(canvas, x, y, y_limit, kLineH, max_chars, line);
  };
  auto draw_secondary = [&](const std::string& line) {
    set_secondary();
    return draw_sidebar_line(canvas, x, y, y_limit, kLineH, max_chars, line);
  };
  auto draw_divider = [&]() {
    if (y + 8.0F > y_limit) {
      return false;
    }
    canvas.set_draw_color(CanvasColor{.r = 62, .g = 72, .b = 90, .a = 255});
    canvas.draw_line(x, y + 3.0F, right, y + 3.0F);
    y += 8.0F;
    return true;
  };

  if (!draw_primary(sidebar_policy.title())) {
    canvas.set_clip_rect(std::nullopt);
    return;
  }

  {
    char buf[128];
    std::snprintf(buf, sizeof(buf), "Bodies tracked: %zu", body_ids.size());
    if (!draw_secondary(buf)) {
      canvas.set_clip_rect(std::nullopt);
      return;
    }
  }

  if (!draw_secondary("Replay window telemetry")) {
    canvas.set_clip_rect(std::nullopt);
    return;
  }

  if (!draw_divider()) {
    canvas.set_clip_rect(std::nullopt);
    return;
  }

  if (!draw_primary(sidebar_policy.simulation_section_title())) {
    canvas.set_clip_rect(std::nullopt);
    return;
  }

  if (active_frame != nullptr) {
    char buf[128];
    std::snprintf(buf, sizeof(buf), "Sim day: %.1f", active_frame->sim_time_s / kSecondsPerDay);
    if (!draw_secondary(buf)) {
      canvas.set_clip_rect(std::nullopt);
      return;
    }
  }

  {
    char buf[128];
    std::snprintf(buf, sizeof(buf), "Frame: %zu / %zu", frame_index + 1, frame_count);
    if (!draw_secondary(buf)) {
      canvas.set_clip_rect(std::nullopt);
      return;
    }
    std::snprintf(buf, sizeof(buf), "Playback: %.2fx  ([ / ])", playback_rate);
    if (!draw_secondary(buf)) {
      canvas.set_clip_rect(std::nullopt);
      return;
    }
    std::snprintf(buf, sizeof(buf), "Zoom: %.2fx  (-/= or wheel)", zoom_level);
    if (!draw_secondary(buf)) {
      canvas.set_clip_rect(std::nullopt);
      return;
    }
  }

  if (!draw_secondary("Pan: arrow keys")) {
    canvas.set_clip_rect(std::nullopt);
    return;
  }

  const std::size_t event_text_max = max_chars > 2 ? max_chars - 2 : max_chars;

  if (sidebar_policy.show_events_section()) {
    if (!draw_divider()) {
      canvas.set_clip_rect(std::nullopt);
      return;
    }

    if (!draw_primary(sidebar_policy.events_section_title())) {
      canvas.set_clip_rect(std::nullopt);
      return;
    }
    if (!draw_secondary("Severity color + timeline row")) {
      canvas.set_clip_rect(std::nullopt);
      return;
    }

    std::size_t event_i = 0;
    while (event_i < workflow.event_markers.size() && (y + kRowH) <= y_limit) {
      const auto& m = workflow.event_markers[event_i];
      const auto color = parse_hex_color(m.color_hex);
      canvas.set_draw_color(color);
      CanvasRect swatch{.x = x, .y = y + 2.0F, .w = 10.0F, .h = 10.0F};
      canvas.fill_rect(swatch);

      char row[256];
      std::snprintf(row, sizeof(row), "t=%.1fd  %s", m.sim_time_s / kSecondsPerDay, m.kind.c_str());
      const std::string clipped = elide_text(row, event_text_max);
      set_secondary();
      canvas.draw_text(x + 14.0F, y, clipped);
      y += kRowH;
      ++event_i;
    }

    if (event_i < workflow.event_markers.size() && (y + kLineH) <= y_limit) {
      set_muted();
      canvas.draw_text(x, y, "...");
      y += kLineH;
    }
  }

  if (sidebar_policy.show_legend_section()) {
    if (!draw_divider()) {
      canvas.set_clip_rect(std::nullopt);
      return;
    }

    if (!draw_primary(sidebar_policy.legend_section_title())) {
      canvas.set_clip_rect(std::nullopt);
      return;
    }

    for (std::size_t i = 0; i < body_ids.size() && (y + kRowH) <= y_limit; ++i) {
      const auto color = color_for_id(body_ids[i]);
      canvas.set_draw_color(color);
      CanvasRect swatch{.x = x, .y = y + 2.0F, .w = 10.0F, .h = 10.0F};
      canvas.fill_rect(swatch);
      const std::string clipped = elide_text(body_ids[i], event_text_max);
      set_secondary();
      canvas.draw_text(x + 14.0F, y, clipped);
      y += kRowH;
    }
  }

  canvas.set_clip_rect(std::nullopt);
}

}  // namespace

DesktopRendererMode Quicklook2DReplayRenderer::mode() const {
  return DesktopRendererMode::Quicklook2D;
}

bool Quicklook2DReplayRenderer::run(
    const std::shared_ptr<DesktopReplayFrameStreamState>& stream_state,
    const brambhand::client::common::ReplayRenderConfig& render_config) {
  if (stream_state == nullptr) {
    return false;
  }

  const auto runtime = create_sdl_quicklook_runtime();
  if (runtime == nullptr ||
      !runtime->initialize("brambhand replay quicklook", 1280, 720)) {
    return false;
  }

  const auto render_semantics =
      brambhand::client::common::create_replay_render_semantics(render_config);

  ReplayQuicklookWorkflowOutput workflow{};
  std::vector<brambhand::client::common::SimulationFrame> frames;
  std::vector<std::string> body_ids;
  std::vector<std::string> orbit_body_ids;
  std::optional<PlotBounds> base_bounds;
  std::size_t snapshot_version = static_cast<std::size_t>(-1);
  bool focus_initialized = false;

  QuicklookFrameState frame_state{};
  frame_state.last_advance_ticks = runtime->ticks_ms();

  const auto capability_profile =
      create_renderer_capability_profile(DesktopRendererMode::Quicklook2D);
  if (capability_profile == nullptr) {
    runtime->shutdown();
    return false;
  }

  const auto ui_layout_policy = capability_profile->create_ui_layout_policy();
  const auto trace_policy = capability_profile->create_trace_policy();
  const auto sidebar_policy = capability_profile->create_sidebar_policy();

  bool running = true;
  while (running) {
    {
      std::lock_guard<std::mutex> lock(stream_state->mutex);
      if (snapshot_version != stream_state->version) {
        workflow = stream_state->workflow;
        frames = stream_state->frames;
        body_ids = stream_state->body_ids;
        snapshot_version = stream_state->version;

        if (!frames.empty()) {
          if (frame_state.frame_index >= frames.size()) {
            frame_state.frame_index = frames.size() - 1;
          }

          base_bounds = compute_bounds(workflow, frames);
          if (base_bounds.has_value() && !focus_initialized) {
            const auto focus_point = find_focus_point(frames, render_config);
            const double base_center_x = 0.5 * (base_bounds->min_x + base_bounds->max_x);
            const double base_center_y = 0.5 * (base_bounds->min_y + base_bounds->max_y);
            frame_state.pan_x = focus_point.has_value() ? (focus_point->first - base_center_x) : 0.0;
            frame_state.pan_y = focus_point.has_value() ? (focus_point->second - base_center_y) : 0.0;
            focus_initialized = true;
          }
        }

        orbit_body_ids.clear();
        orbit_body_ids.reserve(body_ids.size());
        for (const auto& id : body_ids) {
          if (render_semantics->is_dim_trajectory_body(id)) {
            orbit_body_ids.push_back(id);
          }
        }
      }
    }

    const auto input = runtime->poll_input();
    if (input.quit_requested) {
      running = false;
    }
    if (input.decrease_playback) {
      frame_state.playback_rate = std::max(0.25, frame_state.playback_rate * 0.5);
    }
    if (input.increase_playback) {
      frame_state.playback_rate = std::min(16.0, frame_state.playback_rate * 2.0);
    }
    if (input.zoom_in) {
      frame_state.zoom_level = std::min(64.0, frame_state.zoom_level * 1.1);
    }
    if (input.zoom_out) {
      frame_state.zoom_level = std::max(0.2, frame_state.zoom_level / 1.1);
    }

    const double span_x = base_bounds.has_value()
                              ? (base_bounds->max_x - base_bounds->min_x) / frame_state.zoom_level
                              : (1.0 / frame_state.zoom_level);
    const double span_y = base_bounds.has_value()
                              ? (base_bounds->max_y - base_bounds->min_y) / frame_state.zoom_level
                              : (1.0 / frame_state.zoom_level);
    const double pan_step_x = 0.04 * span_x;
    const double pan_step_y = 0.04 * span_y;
    if (input.pan_left) {
      frame_state.pan_x -= pan_step_x;
    }
    if (input.pan_right) {
      frame_state.pan_x += pan_step_x;
    }
    if (input.pan_up) {
      frame_state.pan_y += pan_step_y;
    }
    if (input.pan_down) {
      frame_state.pan_y -= pan_step_y;
    }

    const std::uint64_t now_ticks = runtime->ticks_ms();
    const std::uint64_t frame_period_ms =
        static_cast<std::uint64_t>(std::max(1.0, 33.0 / frame_state.playback_rate));
    if (!frames.empty() && now_ticks - frame_state.last_advance_ticks >= frame_period_ms) {
      frame_state.frame_index = (frame_state.frame_index + 1) % frames.size();
      frame_state.last_advance_ticks = now_ticks;
    }

    const auto [width, height] = runtime->window_size();
    auto& canvas = runtime->canvas();

    canvas.set_draw_color(CanvasColor{.r = 12, .g = 14, .b = 20, .a = 255});
    canvas.fill_rect(CanvasRect{
        .x = 0.0F,
        .y = 0.0F,
        .w = static_cast<float>(width),
        .h = static_cast<float>(height),
    });

    const auto panels = ui_layout_policy->compute(width, height);
    const CanvasRect viewport{
        .x = panels.viewport.x,
        .y = panels.viewport.y,
        .w = panels.viewport.w,
        .h = panels.viewport.h,
    };
    const CanvasRect sidebar{
        .x = panels.sidebar.x,
        .y = panels.sidebar.y,
        .w = panels.sidebar.w,
        .h = panels.sidebar.h,
    };

    canvas.set_draw_color(CanvasColor{.r = 60, .g = 66, .b = 80, .a = 255});
    canvas.draw_rect(viewport);

    const brambhand::client::common::SimulationFrame* active_frame = nullptr;
    if (base_bounds.has_value()) {
      const PlotBounds view_bounds = brambhand::client::common::make_view_bounds(
          *base_bounds,
          frame_state.zoom_level,
          frame_state.pan_x,
          frame_state.pan_y);

      for (const auto& layer : workflow.trajectory_panel.curve_layers) {
        draw_curve_layer(canvas, layer, view_bounds, viewport);
      }

      if (!frames.empty()) {
        for (const auto& id : orbit_body_ids) {
          draw_trace_for_body(
              canvas,
              frames,
              frames.size() - 1,
              id,
              view_bounds,
              viewport,
              color_for_id(id),
              trace_policy->dim_trace_alpha(),
              *trace_policy);
        }

        for (const auto& id : body_ids) {
          draw_trace_for_body(
              canvas,
              frames,
              frame_state.frame_index,
              id,
              view_bounds,
              viewport,
              color_for_id(id),
              trace_policy->active_trace_alpha(),
              *trace_policy);
        }

        active_frame = &frames[frame_state.frame_index];
        for (const auto& body : active_frame->bodies) {
          const auto marker_kind = render_semantics->role_for(body.body_id);
          draw_body_marker(canvas, body, view_bounds, viewport, 3.0F, false, marker_kind);
        }
      }
    } else {
      canvas.set_draw_color(CanvasColor{.r = 184, .g = 198, .b = 222, .a = 255});
      canvas.draw_text(viewport.x + 18.0F, viewport.y + 18.0F, "Streaming replay ingest...");
    }

    draw_sidebar(
        canvas,
        sidebar,
        workflow,
        active_frame,
        frame_state.frame_index,
        frames.empty() ? 0 : frames.size(),
        frame_state.playback_rate,
        frame_state.zoom_level,
        body_ids,
        *sidebar_policy);

    runtime->present();
    runtime->delay_ms(16);
  }

  runtime->shutdown();
  return true;
}

}  // namespace brambhand::client::desktop
