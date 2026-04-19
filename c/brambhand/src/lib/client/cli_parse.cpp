#include "brambhand/client/common/cli_parse.hpp"

#include <span>
#include <string_view>
#include <unordered_map>

namespace brambhand::client::common {

bool cli_option_is_present(
    const CliParseReport& report,
    const std::string& option_name) {
  return report.flags.contains(option_name) || report.values.contains(option_name);
}

CliSchemaValidationReport validate_cli_schema(
    const CliParseReport& report,
    const CliSchemaValidationRules& rules) {
  CliSchemaValidationReport validation{};

  for (const auto& required_set : rules.required_sets) {
    for (const auto& option_name : required_set.option_names) {
      if (!cli_option_is_present(report, option_name)) {
        validation.error = "missing required argument: " + option_name;
        return validation;
      }
    }
  }

  for (const auto& group : rules.mutually_exclusive_groups) {
    std::size_t present_count = 0;
    std::string first_present;
    std::string second_present;

    for (const auto& option_name : group.option_names) {
      if (!cli_option_is_present(report, option_name)) {
        continue;
      }
      if (present_count == 0) {
        first_present = option_name;
      } else if (present_count == 1) {
        second_present = option_name;
      }
      present_count += 1;
    }

    if (present_count > 1) {
      validation.error =
          "arguments are mutually exclusive: " + first_present + " and " + second_present;
      return validation;
    }

    if (group.require_one && present_count == 0) {
      if (group.option_names.empty()) {
        validation.error = "schema error: empty mutually exclusive group";
      } else {
        validation.error = "one of these arguments is required: ";
        for (std::size_t i = 0; i < group.option_names.size(); ++i) {
          if (i > 0) {
            validation.error += ", ";
          }
          validation.error += group.option_names[i];
        }
      }
      return validation;
    }
  }

  return validation;
}

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
