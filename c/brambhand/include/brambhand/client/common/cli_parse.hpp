#pragma once

#include <charconv>
#include <optional>
#include <string>
#include <string_view>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace brambhand::client::common {

enum class CliOptionKind {
  Flag,
  Value,
};

struct CliOptionSpec {
  std::string name;
  CliOptionKind kind{CliOptionKind::Flag};
};

struct CliParseReport {
  std::unordered_map<std::string, std::string> values;
  std::unordered_set<std::string> flags;
  std::vector<std::string> positionals;
  std::string error;

  [[nodiscard]] bool ok() const { return error.empty(); }
};

struct CliRequiredOptionSet {
  std::vector<std::string> option_names;
};

struct CliMutuallyExclusiveGroup {
  std::vector<std::string> option_names;
  bool require_one{false};
};

struct CliSchemaValidationRules {
  std::vector<CliRequiredOptionSet> required_sets;
  std::vector<CliMutuallyExclusiveGroup> mutually_exclusive_groups;
};

struct CliSchemaValidationReport {
  std::string error;

  [[nodiscard]] bool ok() const { return error.empty(); }
};

[[nodiscard]] CliParseReport parse_cli_tokens(
    int argc,
    char** argv,
    const std::vector<CliOptionSpec>& specs);

[[nodiscard]] bool cli_option_is_present(
    const CliParseReport& report,
    const std::string& option_name);

[[nodiscard]] CliSchemaValidationReport validate_cli_schema(
    const CliParseReport& report,
    const CliSchemaValidationRules& rules);

template <typename T>
[[nodiscard]] std::optional<T> cli_transform_from_chars(std::string_view value) {
  T parsed{};
  const auto* first = value.data();
  const auto* last = value.data() + value.size();
  const auto [ptr, ec] = std::from_chars(first, last, parsed);
  if (ec != std::errc{} || ptr != last) {
    return std::nullopt;
  }
  return parsed;
}

template <typename T>
[[nodiscard]] bool cli_assign_transformed_value(
    const CliParseReport& report,
    const std::string& option_name,
    T& destination,
    std::string& error,
    std::string_view expected_kind) {
  const auto it = report.values.find(option_name);
  if (it == report.values.end()) {
    return true;
  }

  const auto parsed = cli_transform_from_chars<T>(it->second);
  if (!parsed.has_value()) {
    error = "invalid " + std::string(expected_kind) + " value for " + option_name + ": " + it->second;
    return false;
  }

  destination = *parsed;
  return true;
}

}  // namespace brambhand::client::common
