#include <iostream>

#include "brambhand/client/common/runtime_frame.hpp"

int main() {
  brambhand::client::common::SimulationFrame frame{};
  frame.run_id = "bootstrap";
  std::cout << "brambhand_desktop bootstrap, run_id=" << frame.run_id << "\n";
  std::cout << "TODO: initialize SDL3/GLFW + Vulkan + Dear ImGui shell\n";
  return 0;
}
