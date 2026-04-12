#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace brambhand::client::common {

struct Vector3 {
  double x{};
  double y{};
  double z{};
};

struct Quaternion {
  double w{1.0};
  double x{};
  double y{};
  double z{};
};

struct BodyState {
  std::string body_id;
  Vector3 position_m;
  Vector3 velocity_mps;
  Quaternion attitude;
  Vector3 angular_velocity_radps;
};

struct EventFrame {
  std::uint64_t sequence{};
  double sim_time_s{};
  std::string kind;
  std::string severity;
  std::string payload_json;
};

struct SimulationFrame {
  std::uint32_t schema_version{1};
  std::string run_id;
  std::uint64_t tick_id{};
  double sim_time_s{};
  std::uint64_t sequence{};
  std::vector<BodyState> bodies;
  std::vector<EventFrame> events;
};

int brambhand_client_link_anchor();

}  // namespace brambhand::client::common
