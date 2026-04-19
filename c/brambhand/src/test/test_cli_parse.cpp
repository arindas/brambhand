#include <iterator>

#include <gtest/gtest.h>

#include "brambhand/client/common/cli_parse.hpp"

TEST(CliParse, ParsesFlagsValuesAndPositionals) {
  const char* argv[] = {
      "tool",
      "--alpha",
      "--count",
      "42",
      "pos1",
      "--name",
      "delta",
  };

  const auto report = brambhand::client::common::parse_cli_tokens(
      static_cast<int>(std::size(argv)),
      const_cast<char**>(argv),
      std::vector<brambhand::client::common::CliOptionSpec>{
          {"--alpha", brambhand::client::common::CliOptionKind::Flag},
          {"--count", brambhand::client::common::CliOptionKind::Value},
          {"--name", brambhand::client::common::CliOptionKind::Value},
      });

  ASSERT_TRUE(report.ok()) << report.error;
  EXPECT_TRUE(report.flags.contains("--alpha"));
  ASSERT_TRUE(report.values.contains("--count"));
  ASSERT_TRUE(report.values.contains("--name"));
  EXPECT_EQ(report.values.at("--count"), "42");
  EXPECT_EQ(report.values.at("--name"), "delta");
  ASSERT_EQ(report.positionals.size(), 1u);
  EXPECT_EQ(report.positionals[0], "pos1");
}

TEST(CliParse, RejectsUnknownOption) {
  const char* argv[] = {
      "tool",
      "--unknown",
  };

  const auto report = brambhand::client::common::parse_cli_tokens(
      static_cast<int>(std::size(argv)),
      const_cast<char**>(argv),
      std::vector<brambhand::client::common::CliOptionSpec>{
          {"--alpha", brambhand::client::common::CliOptionKind::Flag},
      });

  EXPECT_FALSE(report.ok());
  EXPECT_NE(report.error.find("unsupported argument"), std::string::npos);
}

TEST(CliParse, RejectsMissingValue) {
  const char* argv[] = {
      "tool",
      "--count",
  };

  const auto report = brambhand::client::common::parse_cli_tokens(
      static_cast<int>(std::size(argv)),
      const_cast<char**>(argv),
      std::vector<brambhand::client::common::CliOptionSpec>{
          {"--count", brambhand::client::common::CliOptionKind::Value},
      });

  EXPECT_FALSE(report.ok());
  EXPECT_NE(report.error.find("missing value"), std::string::npos);
}

TEST(CliParse, ValidatesRequiredSetsAndMutualExclusion) {
  const char* argv[] = {
      "tool",
      "--a",
      "1",
      "--x",
      "--y",
  };

  const auto report = brambhand::client::common::parse_cli_tokens(
      static_cast<int>(std::size(argv)),
      const_cast<char**>(argv),
      std::vector<brambhand::client::common::CliOptionSpec>{
          {"--a", brambhand::client::common::CliOptionKind::Value},
          {"--b", brambhand::client::common::CliOptionKind::Value},
          {"--x", brambhand::client::common::CliOptionKind::Flag},
          {"--y", brambhand::client::common::CliOptionKind::Flag},
      });
  ASSERT_TRUE(report.ok()) << report.error;

  const auto missing_required = brambhand::client::common::validate_cli_schema(
      report,
      brambhand::client::common::CliSchemaValidationRules{
          .required_sets = {
              brambhand::client::common::CliRequiredOptionSet{.option_names = {"--a", "--b"}},
          },
      });
  EXPECT_FALSE(missing_required.ok());
  EXPECT_NE(missing_required.error.find("missing required argument"), std::string::npos);

  const auto mutually_exclusive = brambhand::client::common::validate_cli_schema(
      report,
      brambhand::client::common::CliSchemaValidationRules{
          .mutually_exclusive_groups = {
              brambhand::client::common::CliMutuallyExclusiveGroup{.option_names = {"--x", "--y"}},
          },
      });
  EXPECT_FALSE(mutually_exclusive.ok());
  EXPECT_NE(mutually_exclusive.error.find("mutually exclusive"), std::string::npos);
}

TEST(CliParse, AssignsTypedTransformsFromValues) {
  const char* argv[] = {
      "tool",
      "--count",
      "42",
      "--bad",
      "NaN?",
  };

  const auto report = brambhand::client::common::parse_cli_tokens(
      static_cast<int>(std::size(argv)),
      const_cast<char**>(argv),
      std::vector<brambhand::client::common::CliOptionSpec>{
          {"--count", brambhand::client::common::CliOptionKind::Value},
          {"--bad", brambhand::client::common::CliOptionKind::Value},
      });
  ASSERT_TRUE(report.ok()) << report.error;

  std::size_t count = 0;
  std::string err;
  EXPECT_TRUE(brambhand::client::common::cli_assign_transformed_value(
      report,
      "--count",
      count,
      err,
      "numeric"));
  EXPECT_EQ(count, 42u);

  std::size_t bad = 0;
  EXPECT_FALSE(brambhand::client::common::cli_assign_transformed_value(
      report,
      "--bad",
      bad,
      err,
      "numeric"));
  EXPECT_NE(err.find("invalid numeric value"), std::string::npos);
}
