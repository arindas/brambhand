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
