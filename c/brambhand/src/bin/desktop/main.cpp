#include <cstddef>
#include <iostream>
#include <memory>
#include <mutex>
#include <set>
#include <string>
#include <thread>
#include <vector>

#include "brambhand/client/common/render_config.hpp"
#include "brambhand/client/common/replay_ingest.hpp"
#include "brambhand/client/common/runtime_frame.hpp"
#include "brambhand/client/desktop/replay_quicklook_workflow.hpp"
#include "brambhand/client/desktop/shell.hpp"
#include "brambhand/client/desktop/trajectory_infographic.hpp"
#include "brambhand/client/common/desktop_cli_options.hpp"
#include "render_config_validation.hpp"
#include "renderer_backend.hpp"
#include "replay_ingest_pipeline.hpp"

int main(int argc, char** argv) {
  const auto cli_report = brambhand::client::common::parse_desktop_cli_options(argc, argv);
  if (!cli_report.ok()) {
    std::cerr << cli_report.error << "\n";
    std::cerr << brambhand::client::common::desktop_cli_usage() << "\n";
    return 2;
  }

  const auto& opts = cli_report.options;

  const auto renderer_mode_parsed = brambhand::client::desktop::parse_renderer_mode(opts.renderer_mode_arg);
  if (!renderer_mode_parsed.has_value()) {
    std::cerr << "unsupported --renderer value: " << opts.renderer_mode_arg
              << " (expected quicklook_2d|vulkan_3d)\n";
    return 2;
  }

  const auto renderer_resolution = brambhand::client::desktop::resolve_renderer_mode(
      *renderer_mode_parsed,
      opts.allow_renderer_fallback);
  if (!renderer_resolution.ok()) {
    std::cerr << renderer_resolution.message << "\n";
    return 2;
  }
  if (renderer_resolution.used_fallback) {
    std::cerr << "renderer fallback: "
              << brambhand::client::desktop::renderer_mode_name(renderer_resolution.requested)
              << " unavailable, using "
              << brambhand::client::desktop::renderer_mode_name(renderer_resolution.effective)
              << "\n";
  }

  const auto render_config_report =
      brambhand::client::common::load_replay_render_config_json(*opts.render_config_path);
  if (!render_config_report.ok()) {
    std::cerr << "render config ingest failed: " << render_config_report.error << "\n";
    return 1;
  }

  if (opts.concurrent_ingest && (opts.ingest_chunk_frames == 0 || opts.ingest_queue_max_chunks == 0)) {
    std::cerr << "concurrent ingest requires positive --ingest-chunk-frames and --ingest-queue-max-chunks\n";
    return 2;
  }

  auto stream_state = std::make_shared<brambhand::client::desktop::DesktopReplayFrameStreamState>();
  brambhand::client::desktop::DesktopReplayIngestOutput ingest_result{};
  std::thread ingest_thread;

  const auto ingest_options = brambhand::client::desktop::DesktopReplayIngestOptions{
      .concurrent = opts.concurrent_ingest,
      .chunk_size_frames = opts.ingest_chunk_frames,
      .queue_max_chunks = opts.ingest_queue_max_chunks,
  };

  const bool stream_into_active_renderer = opts.concurrent_ingest && !opts.no_window;
  if (stream_into_active_renderer) {
    ingest_thread = std::thread([&]() {
      ingest_result = brambhand::client::desktop::ingest_replay_for_desktop(
          *opts.replay_path,
          ingest_options,
          brambhand::client::desktop::DesktopReplayFramesUpdatedCallback{
              [stream_state](
                  const std::vector<brambhand::client::common::SimulationFrame>& frames,
                  const std::vector<std::string>& body_ids) {
                const auto workflow =
                    brambhand::client::desktop::build_replay_quicklook_workflow(frames);
                std::lock_guard<std::mutex> lock(stream_state->mutex);
                stream_state->workflow = workflow;
                stream_state->frames = frames;
                stream_state->body_ids = body_ids;
                stream_state->version += 1;
              }});

      {
        std::lock_guard<std::mutex> lock(stream_state->mutex);
        stream_state->ingest_complete = true;
        stream_state->version += 1;
      }
    });
  } else {
    ingest_result = brambhand::client::desktop::ingest_replay_for_desktop(
        *opts.replay_path,
        ingest_options,
        brambhand::client::desktop::DesktopReplayFramesUpdatedCallback{});

    if (!ingest_result.report.ok()) {
      std::cerr << "replay ingest failed: " << ingest_result.report.error << "\n";
      return 1;
    }

    const auto workflow =
        brambhand::client::desktop::build_replay_quicklook_workflow(ingest_result.report.frames);
    {
      std::lock_guard<std::mutex> lock(stream_state->mutex);
      stream_state->workflow = workflow;
      stream_state->frames = ingest_result.report.frames;
      stream_state->body_ids = ingest_result.report.body_ids;
      stream_state->ingest_complete = true;
      stream_state->version = 1;
    }
  }

  brambhand::client::desktop::DesktopShellConfig config{};
  config.backend = brambhand::client::desktop::DesktopPlatformBackend::SDL3;
  config.imgui_docking_enabled = true;

  brambhand::client::desktop::DesktopShell shell(config);
  if (!shell.initialize()) {
    if (ingest_thread.joinable()) {
      ingest_thread.join();
    }
    std::cerr << "desktop shell initialization failed: " << shell.telemetry().last_error << "\n";
    return 1;
  }
  (void)shell.pump_frame();
  shell.shutdown();

  if (!opts.no_window) {
    const auto renderer = brambhand::client::desktop::create_desktop_replay_renderer(
        renderer_resolution.effective);
    if (renderer == nullptr ||
        !renderer->run(
            stream_state,
            render_config_report.config)) {
      if (ingest_thread.joinable()) {
        ingest_thread.join();
      }
      std::cerr << "failed to open replay window for renderer="
                << brambhand::client::desktop::renderer_mode_name(renderer_resolution.effective)
                << "\n";
      return 1;
    }
  }

  if (ingest_thread.joinable()) {
    ingest_thread.join();
  }

  const auto& replay_report = ingest_result.report;
  if (!replay_report.ok()) {
    std::cerr << "replay ingest failed: " << replay_report.error << "\n";
    return 1;
  }

  const auto render_config_validation =
      brambhand::client::desktop::validate_replay_render_config_body_ids(
          render_config_report.config,
          replay_report.body_ids);

  if (render_config_validation.has_missing()) {
    std::cerr << "render config validation: replay is missing configured body ids\n";
    const auto print_missing = [&](const char* key, const std::vector<std::string>& ids) {
      if (ids.empty()) {
        return;
      }
      std::cerr << "  " << key << " missing:";
      for (const auto& id : ids) {
        std::cerr << " " << id;
      }
      std::cerr << "\n";
    };

    print_missing("dim_trajectory_body_ids", render_config_validation.missing_dim_ids);
    print_missing("sun_body_ids", render_config_validation.missing_sun_ids);
    print_missing("planet_body_ids", render_config_validation.missing_planet_ids);
    print_missing("probe_body_ids", render_config_validation.missing_probe_ids);

    if (render_config_validation.missing_focus_id) {
      std::cerr << "  focus_body_id missing: " << *render_config_report.config.focus_body_id << "\n";
    }

    if (opts.strict_render_config) {
      std::cerr << "strict render config validation enabled; aborting.\n";
      return 1;
    }
  }

  brambhand::client::common::SimulationFrame frame{};
  frame.run_id = replay_report.frames.empty() ? "empty_replay" : replay_report.frames.back().run_id;
  const auto workflow =
      brambhand::client::desktop::build_replay_quicklook_workflow(replay_report.frames);

  std::cout << "brambhand_desktop replay mode, run_id=" << frame.run_id
            << ", loaded_frames=" << replay_report.frames.size() << "\n";
  std::cout << "desktop shell backend="
            << brambhand::client::desktop::backend_name(shell.telemetry().backend)
            << ", imgui_docking=" << (shell.telemetry().imgui_docking_enabled ? "on" : "off")
            << ", status=" << brambhand::client::desktop::status_name(shell.telemetry().status)
            << ", frames=" << shell.telemetry().frames_pumped << "\n";
  std::cout << "renderer_mode="
            << brambhand::client::desktop::renderer_mode_name(renderer_resolution.requested)
            << ", effective_renderer="
            << brambhand::client::desktop::renderer_mode_name(renderer_resolution.effective)
            << "\n";
  if (opts.concurrent_ingest) {
    std::cout << "ingest_mode=concurrent"
              << ", chunk_frames=" << opts.ingest_chunk_frames
              << ", queue_max_chunks=" << opts.ingest_queue_max_chunks
              << ", chunks_processed=" << ingest_result.telemetry.chunks_processed
              << ", queue_high_watermark=" << ingest_result.telemetry.queue_high_watermark
              << "\n";
  }
  std::cout << "trajectory_panel schema=" << workflow.trajectory_panel.schema_version
            << ", curve_layers=" << workflow.trajectory_panel.curve_layers.size()
            << ", object_icons=" << workflow.trajectory_panel.object_icons.size() << "\n";
  std::cout << "event_markers=" << workflow.event_markers.size();
  if (!workflow.event_markers.empty()) {
    const auto& first = workflow.event_markers.front();
    std::cout << ", first_event={sequence:" << first.sequence << ", kind:" << first.kind
              << ", severity:" << first.severity << ", color:" << first.color_hex << "}";
  }
  std::cout << "\n";

  return 0;
}
