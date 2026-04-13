#pragma once

#include "brambhand/client/common/render_config.hpp"
#include "brambhand/client/desktop/replay_quicklook_workflow.hpp"

namespace brambhand::client::desktop {

bool run_replay_window(
    const ReplayQuicklookWorkflowOutput& workflow,
    const std::vector<brambhand::client::common::SimulationFrame>& frames,
    const brambhand::client::common::ReplayRenderConfig& render_config);

}  // namespace brambhand::client::desktop
