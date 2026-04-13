#include "brambhand/client/common/render_config.hpp"

#include <cctype>
#include <cstdint>
#include <fstream>
#include <optional>
#include <sstream>

namespace brambhand::client::common {
namespace {

std::size_t find_after_colon(const std::string& json, const std::string& key) {
  const auto key_pos = json.find("\"" + key + "\"");
  if (key_pos == std::string::npos) {
    return std::string::npos;
  }

  const auto colon_pos = json.find(':', key_pos);
  if (colon_pos == std::string::npos) {
    return std::string::npos;
  }

  std::size_t value_pos = colon_pos + 1;
  while (value_pos < json.size() && std::isspace(static_cast<unsigned char>(json[value_pos])) != 0) {
    value_pos += 1;
  }
  return value_pos;
}

std::optional<std::string> extract_string(const std::string& json, const std::string& key) {
  const auto value_pos = find_after_colon(json, key);
  if (value_pos == std::string::npos || value_pos >= json.size() || json[value_pos] != '"') {
    return std::nullopt;
  }

  std::string value;
  for (std::size_t i = value_pos + 1; i < json.size(); ++i) {
    const char ch = json[i];
    if (ch == '\\') {
      if (i + 1 >= json.size()) {
        return std::nullopt;
      }
      value.push_back(json[i + 1]);
      i += 1;
      continue;
    }

    if (ch == '"') {
      return value;
    }

    value.push_back(ch);
  }

  return std::nullopt;
}

std::optional<std::uint32_t> extract_u32(const std::string& json, const std::string& key) {
  const auto value_pos = find_after_colon(json, key);
  if (value_pos == std::string::npos || value_pos >= json.size()) {
    return std::nullopt;
  }

  std::size_t end_pos = value_pos;
  while (end_pos < json.size() && std::isdigit(static_cast<unsigned char>(json[end_pos])) != 0) {
    end_pos += 1;
  }
  if (end_pos == value_pos) {
    return std::nullopt;
  }

  try {
    return static_cast<std::uint32_t>(std::stoul(json.substr(value_pos, end_pos - value_pos)));
  } catch (...) {
    return std::nullopt;
  }
}

std::optional<std::string> extract_array(const std::string& json, const std::string& key) {
  const auto value_pos = find_after_colon(json, key);
  if (value_pos == std::string::npos || value_pos >= json.size() || json[value_pos] != '[') {
    return std::nullopt;
  }

  std::size_t depth = 0;
  for (std::size_t i = value_pos; i < json.size(); ++i) {
    if (json[i] == '[') {
      depth += 1;
    } else if (json[i] == ']') {
      depth -= 1;
      if (depth == 0) {
        return json.substr(value_pos, i - value_pos + 1);
      }
    }
  }

  return std::nullopt;
}

std::vector<std::string> parse_string_array(const std::string& array_json) {
  std::vector<std::string> values;

  bool in_string = false;
  std::string current;
  for (std::size_t i = 0; i < array_json.size(); ++i) {
    const char ch = array_json[i];
    if (!in_string) {
      if (ch == '"') {
        in_string = true;
        current.clear();
      }
      continue;
    }

    if (ch == '\\') {
      if (i + 1 < array_json.size()) {
        current.push_back(array_json[i + 1]);
        i += 1;
      }
      continue;
    }

    if (ch == '"') {
      values.push_back(current);
      in_string = false;
      continue;
    }

    current.push_back(ch);
  }

  return values;
}

}  // namespace

ReplayRenderConfigReport load_replay_render_config_json(const std::string& path) {
  std::ifstream in(path);
  if (!in.is_open()) {
    return ReplayRenderConfigReport{.error = "failed to open render config file"};
  }

  std::stringstream buffer;
  buffer << in.rdbuf();
  const std::string json = buffer.str();

  ReplayRenderConfig config{};
  if (const auto schema = extract_u32(json, "schema_version"); schema.has_value()) {
    config.schema_version = *schema;
  }

  const auto dim_ids_array = extract_array(json, "dim_trajectory_body_ids");
  if (!dim_ids_array.has_value()) {
    return ReplayRenderConfigReport{.error = "render config missing dim_trajectory_body_ids array"};
  }
  config.dim_trajectory_body_ids = parse_string_array(*dim_ids_array);

  if (config.dim_trajectory_body_ids.empty()) {
    return ReplayRenderConfigReport{.error = "render config dim_trajectory_body_ids must be non-empty"};
  }

  if (const auto focus = extract_string(json, "focus_body_id"); focus.has_value() && !focus->empty()) {
    config.focus_body_id = *focus;
  }

  if (const auto sun_ids = extract_array(json, "sun_body_ids"); sun_ids.has_value()) {
    config.sun_body_ids = parse_string_array(*sun_ids);
  }
  if (const auto planet_ids = extract_array(json, "planet_body_ids"); planet_ids.has_value()) {
    config.planet_body_ids = parse_string_array(*planet_ids);
  }
  if (const auto probe_ids = extract_array(json, "probe_body_ids"); probe_ids.has_value()) {
    config.probe_body_ids = parse_string_array(*probe_ids);
  }

  return ReplayRenderConfigReport{.config = config};
}

}  // namespace brambhand::client::common
