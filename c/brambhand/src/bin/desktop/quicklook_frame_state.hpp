#pragma once

#include <cstddef>
#include <cstdint>

#include "brambhand/client/common/cacheline.hpp"

namespace brambhand::client::desktop {

struct alignas(brambhand::client::common::kCacheLineBytes) QuicklookFrameState {
  std::size_t frame_index{0};
  std::uint64_t last_advance_ticks{0};
  double playback_rate{1.0};
  double zoom_level{1.0};
  double pan_x{0.0};
  double pan_y{0.0};
};

static_assert(
    sizeof(QuicklookFrameState) <= brambhand::client::common::kCacheLineBytes,
    "QuicklookFrameState should stay within one cache line");

}  // namespace brambhand::client::desktop
