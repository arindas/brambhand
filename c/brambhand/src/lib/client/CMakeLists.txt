add_library(brambhand_client STATIC
  cli_parse.cpp
  client_common.cpp
  desktop_cli_options.cpp
  desktop_shell.cpp
  replay_ingest.cpp
  render_config.cpp
  render_semantics.cpp
  plot_geometry.cpp
  trajectory_infographic.cpp
  replay_quicklook_workflow.cpp
)

target_include_directories(brambhand_client
  PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)
