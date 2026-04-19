add_executable(brambhand_desktop
  main.cpp
  renderer_mode.cpp
  renderer_backend.cpp
  renderer_capability_profile.cpp
  render_config_validation.cpp
  replay_ingest_pipeline.cpp
  replay_window.cpp
  sdl_quicklook_canvas.cpp
  sdl_quicklook_runtime.cpp
  quicklook_trace_policy.cpp
  quicklook_sidebar_policy.cpp
  ui_layout.cpp
)

find_package(SDL3 QUIET)
if(SDL3_FOUND)
  target_link_libraries(brambhand_desktop
    PRIVATE
      brambhand_client
      SDL3::SDL3
  )
else()
  find_package(PkgConfig REQUIRED)
  pkg_check_modules(SDL3 REQUIRED sdl3)

  target_include_directories(brambhand_desktop PRIVATE ${SDL3_INCLUDE_DIRS})
  target_link_directories(brambhand_desktop PRIVATE ${SDL3_LIBRARY_DIRS})
  target_compile_options(brambhand_desktop PRIVATE ${SDL3_CFLAGS_OTHER})
  target_link_libraries(brambhand_desktop
    PRIVATE
      brambhand_client
      ${SDL3_LIBRARIES}
  )
endif()
