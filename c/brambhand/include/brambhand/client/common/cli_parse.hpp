#pragma once

#include <string>
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

[[nodiscard]] CliParseReport parse_cli_tokens(
    int argc,
    char** argv,
    const std::vector<CliOptionSpec>& specs);

}  // namespace brambhand::client::common
