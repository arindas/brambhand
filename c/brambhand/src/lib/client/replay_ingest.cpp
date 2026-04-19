#include "brambhand/client/common/replay_ingest.hpp"

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <limits>
#include <optional>
#include <sstream>
#include <unordered_set>

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

std::optional<std::string> extract_number_token(const std::string& json, const std::string& key) {
  const auto value_pos = find_after_colon(json, key);
  if (value_pos == std::string::npos || value_pos >= json.size()) {
    return std::nullopt;
  }

  std::size_t end_pos = value_pos;
  while (end_pos < json.size()) {
    const char ch = json[end_pos];
    const bool numeric_char =
        std::isdigit(static_cast<unsigned char>(ch)) != 0 || ch == '-' || ch == '+' || ch == '.' || ch == 'e' || ch == 'E';
    if (!numeric_char) {
      break;
    }
    end_pos += 1;
  }

  if (end_pos == value_pos) {
    return std::nullopt;
  }

  return json.substr(value_pos, end_pos - value_pos);
}

std::optional<std::uint64_t> extract_u64(const std::string& json, const std::string& key) {
  const auto token = extract_number_token(json, key);
  if (!token.has_value()) {
    return std::nullopt;
  }

  try {
    return static_cast<std::uint64_t>(std::stoull(*token));
  } catch (...) {
    return std::nullopt;
  }
}

std::optional<std::uint32_t> extract_u32(const std::string& json, const std::string& key) {
  const auto token = extract_number_token(json, key);
  if (!token.has_value()) {
    return std::nullopt;
  }

  try {
    return static_cast<std::uint32_t>(std::stoul(*token));
  } catch (...) {
    return std::nullopt;
  }
}

std::optional<double> extract_double(const std::string& json, const std::string& key) {
  const auto token = extract_number_token(json, key);
  if (!token.has_value()) {
    return std::nullopt;
  }

  try {
    return std::stod(*token);
  } catch (...) {
    return std::nullopt;
  }
}

std::optional<std::string> extract_object(const std::string& json, const std::string& key) {
  const auto value_pos = find_after_colon(json, key);
  if (value_pos == std::string::npos || value_pos >= json.size() || json[value_pos] != '{') {
    return std::nullopt;
  }

  std::size_t depth = 0;
  for (std::size_t i = value_pos; i < json.size(); ++i) {
    if (json[i] == '{') {
      depth += 1;
    } else if (json[i] == '}') {
      depth -= 1;
      if (depth == 0) {
        return json.substr(value_pos, i - value_pos + 1);
      }
    }
  }

  return std::nullopt;
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

std::vector<std::string> split_json_objects_from_array(const std::string& array_json) {
  std::vector<std::string> objects;

  std::size_t depth = 0;
  std::size_t start = std::string::npos;
  for (std::size_t i = 0; i < array_json.size(); ++i) {
    const char ch = array_json[i];
    if (ch == '{') {
      if (depth == 0) {
        start = i;
      }
      depth += 1;
    } else if (ch == '}') {
      if (depth == 0) {
        continue;
      }
      depth -= 1;
      if (depth == 0 && start != std::string::npos) {
        objects.push_back(array_json.substr(start, i - start + 1));
        start = std::string::npos;
      }
    }
  }

  return objects;
}

std::vector<std::string> parse_string_array(const std::string& array_json) {
  std::vector<std::string> values;

  bool in_string = false;
  bool escaped = false;
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

    if (escaped) {
      current.push_back(ch);
      escaped = false;
      continue;
    }

    if (ch == '\\') {
      escaped = true;
      continue;
    }

    if (ch == '"') {
      values.push_back(current);
      in_string = false;
      current.clear();
      continue;
    }

    current.push_back(ch);
  }

  return values;
}

struct BodyIdCatalogFrame {
  bool present{false};
  std::vector<std::string> initial_body_ids;
  std::vector<std::string> created_body_ids;
  std::vector<std::string> destroyed_body_ids;
};

std::optional<BodyIdCatalogFrame> parse_body_id_catalog(const std::string& line) {
  BodyIdCatalogFrame catalog{};

  const auto catalog_json = extract_object(line, "body_id_catalog");
  if (!catalog_json.has_value()) {
    return catalog;
  }

  catalog.present = true;

  if (const auto schema = extract_u32(*catalog_json, "schema_version");
      schema.has_value() && *schema != 1U) {
    return std::nullopt;
  }

  if (const auto initial_ids = extract_array(*catalog_json, "initial_body_ids"); initial_ids.has_value()) {
    catalog.initial_body_ids = parse_string_array(*initial_ids);
  }
  if (const auto created_ids = extract_array(*catalog_json, "created_body_ids"); created_ids.has_value()) {
    catalog.created_body_ids = parse_string_array(*created_ids);
  }
  if (const auto destroyed_ids = extract_array(*catalog_json, "destroyed_body_ids"); destroyed_ids.has_value()) {
    catalog.destroyed_body_ids = parse_string_array(*destroyed_ids);
  }

  return catalog;
}

std::optional<BodyState> parse_body_state(const std::string& body_json) {
  const auto body_id = extract_string(body_json, "body_id");
  const auto position_json = extract_object(body_json, "position_m");
  if (!body_id.has_value() || !position_json.has_value()) {
    return std::nullopt;
  }

  const auto x = extract_double(*position_json, "x");
  const auto y = extract_double(*position_json, "y");
  const auto z = extract_double(*position_json, "z");
  if (!x.has_value() || !y.has_value() || !z.has_value()) {
    return std::nullopt;
  }

  BodyState body{};
  body.body_id = *body_id;
  body.visualization_role = extract_string(body_json, "visualization_role").value_or("");
  body.position_m = Vector3{.x = *x, .y = *y, .z = *z};
  return body;
}

std::optional<EventFrame> parse_event_frame(const std::string& event_json) {
  const auto sequence = extract_u64(event_json, "sequence");
  const auto sim_time_s = extract_double(event_json, "sim_time_s");
  const auto kind = extract_string(event_json, "kind");
  if (!sequence.has_value() || !sim_time_s.has_value() || !kind.has_value()) {
    return std::nullopt;
  }

  EventFrame event{};
  event.sequence = *sequence;
  event.sim_time_s = *sim_time_s;
  event.kind = *kind;
  event.severity = extract_string(event_json, "severity").value_or("info");
  if (const auto payload_string = extract_string(event_json, "payload_json"); payload_string.has_value()) {
    event.payload_json = *payload_string;
  } else {
    event.payload_json = extract_object(event_json, "payload_json").value_or("{}");
  }
  return event;
}

struct ParsedReplayLine {
  SimulationFrame frame;
  BodyIdCatalogFrame body_catalog;
};

std::optional<ParsedReplayLine> parse_simulation_frame_line(const std::string& line) {
  SimulationFrame frame{};

  if (const auto schema = extract_u32(line, "schema_version"); schema.has_value()) {
    frame.schema_version = *schema;
  }

  const auto run_id = extract_string(line, "run_id");
  const auto tick_id = extract_u64(line, "tick_id");
  const auto sim_time_s = extract_double(line, "sim_time_s");
  const auto sequence = extract_u64(line, "sequence");

  if (!run_id.has_value() || !tick_id.has_value() || !sim_time_s.has_value() || !sequence.has_value()) {
    return std::nullopt;
  }

  frame.run_id = *run_id;
  frame.tick_id = *tick_id;
  frame.sim_time_s = *sim_time_s;
  frame.sequence = *sequence;

  if (const auto bodies_json = extract_array(line, "bodies"); bodies_json.has_value()) {
    for (const auto& body_json : split_json_objects_from_array(*bodies_json)) {
      const auto body = parse_body_state(body_json);
      if (body.has_value()) {
        frame.bodies.push_back(*body);
      }
    }
  }

  if (const auto events_json = extract_array(line, "events"); events_json.has_value()) {
    for (const auto& event_json : split_json_objects_from_array(*events_json)) {
      const auto event = parse_event_frame(event_json);
      if (event.has_value()) {
        frame.events.push_back(*event);
      }
    }
  }

  const auto body_catalog = parse_body_id_catalog(line);
  if (!body_catalog.has_value()) {
    return std::nullopt;
  }

  return ParsedReplayLine{
      .frame = frame,
      .body_catalog = *body_catalog,
  };
}

}  // namespace

ReplayIngestReport load_replay_jsonl_incremental(
    const std::string& path,
    std::size_t chunk_size_frames,
    const ReplayIngestChunkCallback& on_chunk) {
  if (chunk_size_frames == 0) {
    return ReplayIngestReport{.error = "chunk_size_frames must be > 0"};
  }

  std::ifstream in(path);
  if (!in.is_open()) {
    return ReplayIngestReport{.frames = {}, .error = "failed to open replay file"};
  }

  ReplayIngestReport report{};
  std::string line;
  std::size_t line_number = 0;
  std::optional<std::uint64_t> last_sequence;
  std::optional<std::string> run_id;
  bool body_catalog_initialized = false;
  std::unordered_set<std::string> active_body_ids;
  std::unordered_set<std::string> body_ids_ever_seen;
  std::uint64_t chunk_index = 0;
  std::vector<SimulationFrame> chunk_frames;
  chunk_frames.reserve(std::min<std::size_t>(chunk_size_frames, 4096));

  auto emit_chunk = [&](bool is_final_chunk) mutable -> bool {
    if (chunk_frames.empty() && !is_final_chunk) {
      return true;
    }

    ReplayIngestChunk chunk{};
    chunk.chunk_index = ++chunk_index;
    chunk.lines_processed = static_cast<std::uint64_t>(line_number);
    chunk.is_final_chunk = is_final_chunk;
    chunk.frames = std::move(chunk_frames);
    chunk.cumulative_body_ids.assign(body_ids_ever_seen.begin(), body_ids_ever_seen.end());
    std::sort(chunk.cumulative_body_ids.begin(), chunk.cumulative_body_ids.end());

    chunk_frames.clear();
    chunk_frames.reserve(std::min<std::size_t>(chunk_size_frames, 4096));

    if (on_chunk) {
      return on_chunk(std::move(chunk));
    }
    return true;
  };

  while (std::getline(in, line)) {
    line_number += 1;
    if (line.empty()) {
      continue;
    }

    const auto parsed = parse_simulation_frame_line(line);
    if (!parsed.has_value()) {
      std::ostringstream err;
      err << "invalid replay JSONL frame at line " << line_number;
      report.error = err.str();
      report.frames.clear();
      return report;
    }

    const auto& frame = parsed->frame;

    if (run_id.has_value() && frame.run_id != *run_id) {
      std::ostringstream err;
      err << "run_id mismatch at line " << line_number;
      report.error = err.str();
      report.frames.clear();
      return report;
    }
    run_id = frame.run_id;

    if (last_sequence.has_value() && frame.sequence <= *last_sequence) {
      std::ostringstream err;
      err << "non-monotonic replay sequence at line " << line_number;
      report.error = err.str();
      report.frames.clear();
      return report;
    }
    last_sequence = frame.sequence;

    const auto& catalog = parsed->body_catalog;
    if (!catalog.present) {
      std::ostringstream err;
      err << "missing body_id_catalog at line " << line_number;
      report.error = err.str();
      report.frames.clear();
      return report;
    }

    if (!body_catalog_initialized) {
      if (catalog.initial_body_ids.empty()) {
        std::ostringstream err;
        err << "body_id_catalog.initial_body_ids must be provided on first frame at line " << line_number;
        report.error = err.str();
        report.frames.clear();
        return report;
      }
      for (const auto& id : catalog.initial_body_ids) {
        active_body_ids.insert(id);
        body_ids_ever_seen.insert(id);
      }
      body_catalog_initialized = true;
    } else if (!catalog.initial_body_ids.empty()) {
      std::ostringstream err;
      err << "body_id_catalog.initial_body_ids can only appear on first frame (line " << line_number << ")";
      report.error = err.str();
      report.frames.clear();
      return report;
    }

    for (const auto& id : catalog.created_body_ids) {
      if (active_body_ids.contains(id)) {
        std::ostringstream err;
        err << "body_id_catalog create for already-active id '" << id << "' at line " << line_number;
        report.error = err.str();
        report.frames.clear();
        return report;
      }
      active_body_ids.insert(id);
      body_ids_ever_seen.insert(id);
    }

    for (const auto& id : catalog.destroyed_body_ids) {
      if (!active_body_ids.contains(id)) {
        std::ostringstream err;
        err << "body_id_catalog destroy for unknown id '" << id << "' at line " << line_number;
        report.error = err.str();
        report.frames.clear();
        return report;
      }
      active_body_ids.erase(id);
    }

    report.frames.push_back(frame);
    chunk_frames.push_back(frame);

    if (chunk_frames.size() >= chunk_size_frames) {
      if (!emit_chunk(false)) {
        std::ostringstream err;
        err << "replay ingest aborted by chunk callback at line " << line_number;
        report.error = err.str();
        report.frames.clear();
        return report;
      }
    }
  }

  if (!emit_chunk(true)) {
    report.error = "replay ingest aborted by chunk callback at final chunk";
    report.frames.clear();
    return report;
  }

  report.body_ids.assign(body_ids_ever_seen.begin(), body_ids_ever_seen.end());
  std::sort(report.body_ids.begin(), report.body_ids.end());

  return report;
}

ReplayIngestReport load_replay_jsonl(const std::string& path) {
  return load_replay_jsonl_incremental(
      path,
      std::numeric_limits<std::size_t>::max(),
      ReplayIngestChunkCallback{});
}

}  // namespace brambhand::client::common
