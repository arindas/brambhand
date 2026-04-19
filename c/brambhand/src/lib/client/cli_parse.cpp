#include "brambhand/client/common/cli_parse.hpp"

#include <span>
#include <string_view>
#include <unordered_map>

namespace brambhand::client::common {

CliParseReport parse_cli_tokens(
    int argc,
    char** argv,
    const std::vector<CliOptionSpec>& specs) {
  CliParseReport report{};

  std::unordered_map<std::string, CliOptionKind> spec_by_name;
  spec_by_name.reserve(specs.size());
  for (const auto& spec : specs) {
    spec_by_name.insert_or_assign(spec.name, spec.kind);
  }

  if (argc <= 1) {
    return report;
  }

  const std::span<char*> args(argv + 1, static_cast<std::size_t>(argc - 1));
  for (std::size_t i = 0; i < args.size(); ++i) {
    const std::string_view token = args[i];
    if (token.rfind("--", 0) != 0) {
      report.positionals.emplace_back(token);
      continue;
    }

    const auto it = spec_by_name.find(std::string(token));
    if (it == spec_by_name.end()) {
      report.error = "unsupported argument: " + std::string(token);
      return report;
    }

    if (it->second == CliOptionKind::Flag) {
      report.flags.insert(std::string(token));
      continue;
    }

    if (i + 1 >= args.size()) {
      report.error = "missing value for argument: " + std::string(token);
      return report;
    }

    i += 1;
    report.values.insert_or_assign(std::string(token), std::string(args[i]));
  }

  return report;
}

}  // namespace brambhand::client::common
