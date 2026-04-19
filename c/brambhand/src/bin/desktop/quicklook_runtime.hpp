#pragma once

#include <cstdint>
#include <memory>
#include <optional>
#include <utility>

#include "brambhand/client/common/cacheline.hpp"
#include "quicklook_canvas.hpp"

namespace brambhand::client::desktop {

struct alignas(brambhand::client::common::kCacheLineBytes) QuicklookInputSnapshot {
  bool quit_requested{false};
  bool decrease_playback{false};
  bool increase_playback{false};
  bool zoom_in{false};
  bool zoom_out{false};
  bool pan_left{false};
  bool pan_right{false};
  bool pan_up{false};
  bool pan_down{false};
};

static_assert(
    sizeof(QuicklookInputSnapshot) <= brambhand::client::common::kCacheLineBytes,
    "QuicklookInputSnapshot should stay within one cache line");

class QuicklookRuntime {
 public:
  virtual ~QuicklookRuntime() = default;

  [[nodiscard]] virtual bool initialize(const char* title, int width, int height) = 0;
  virtual void shutdown() = 0;

  [[nodiscard]] virtual QuicklookInputSnapshot poll_input() = 0;
  [[nodiscard]] virtual std::uint64_t ticks_ms() const = 0;
  [[nodiscard]] virtual std::pair<int, int> window_size() const = 0;

  [[nodiscard]] virtual QuicklookCanvas& canvas() = 0;
  virtual void present() = 0;
  virtual void delay_ms(std::uint32_t ms) = 0;
};

[[nodiscard]] std::unique_ptr<QuicklookRuntime> create_sdl_quicklook_runtime();

}  // namespace brambhand::client::desktop
