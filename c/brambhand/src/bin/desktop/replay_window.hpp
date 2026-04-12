#pragma once

#include "brambhand/client/desktop/replay_quicklook_workflow.hpp"

namespace brambhand::client::desktop {

bool run_replay_window(
    const ReplayQuicklookWorkflowOutput& workflow,
    const std::vector<brambhand::client::common::SimulationFrame>& frames);

}  // namespace brambhand::client::desktop
