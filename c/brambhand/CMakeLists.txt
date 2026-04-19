cmake_minimum_required(VERSION 3.21)
project(brambhand_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BRAMBHAND_BUILD_DESKTOP_CLIENT "Build desktop client" ON)

include(CTest)

# Keep artifacts flat in the build root instead of per-subdirectory nesting.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})

foreach(CONFIG_TYPE DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
  set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_${CONFIG_TYPE} ${CMAKE_BINARY_DIR})
  set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_${CONFIG_TYPE} ${CMAKE_BINARY_DIR})
  set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_${CONFIG_TYPE} ${CMAKE_BINARY_DIR})
endforeach()

add_subdirectory(src/lib/client)

if(BRAMBHAND_BUILD_DESKTOP_CLIENT)
  add_subdirectory(src/bin/desktop)
endif()

if(BUILD_TESTING)
  include(FetchContent)
  FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
  )
  set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
  FetchContent_MakeAvailable(googletest)

  add_executable(brambhand_test_suite
    src/test/test_runtime_frame.cpp
    src/test/test_desktop_shell.cpp
    src/test/test_cli_parse.cpp
    src/test/test_replay_ingest.cpp
    src/test/test_render_config.cpp
    src/test/test_render_semantics.cpp
    src/test/test_plot_geometry.cpp
    src/test/test_trajectory_infographic.cpp
    src/test/test_replay_quicklook_workflow.cpp
    src/test/test_replay_ingest_pipeline.cpp
    src/test/test_replay_ingest_benchmark_options.cpp
    src/test/test_render_config_validation.cpp
    src/test/test_desktop_cli_options.cpp
    src/test/test_renderer_mode.cpp
    src/test/test_renderer_capability_profile.cpp
    src/bin/desktop/renderer_mode.cpp
    src/bin/desktop/render_config_validation.cpp
    src/bin/desktop/replay_ingest_pipeline.cpp
    src/bin/desktop/replay_ingest_benchmark_options.cpp
    src/bin/desktop/renderer_capability_profile.cpp
    src/bin/desktop/quicklook_trace_policy.cpp
    src/bin/desktop/quicklook_sidebar_policy.cpp
    src/bin/desktop/ui_layout.cpp
  )

  target_link_libraries(brambhand_test_suite
    PRIVATE
      brambhand_client
      GTest::gtest_main
  )

  include(GoogleTest)
  gtest_discover_tests(brambhand_test_suite)
endif()
