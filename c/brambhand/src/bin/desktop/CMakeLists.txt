set(BRAMBHAND_SDL3_FOUND OFF)
set(BRAMBHAND_SDL3_USE_PKGCONFIG OFF)

find_package(SDL3 QUIET)
if(SDL3_FOUND)
  set(BRAMBHAND_SDL3_FOUND ON)
else()
  find_package(PkgConfig QUIET)
  if(PkgConfig_FOUND)
    pkg_check_modules(SDL3 QUIET sdl3)
    if(SDL3_FOUND)
      set(BRAMBHAND_SDL3_FOUND ON)
      set(BRAMBHAND_SDL3_USE_PKGCONFIG ON)
    endif()
  endif()
endif()

if(BRAMBHAND_SDL3_FOUND)
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

  if(BRAMBHAND_SDL3_USE_PKGCONFIG)
    target_include_directories(brambhand_desktop PRIVATE ${SDL3_INCLUDE_DIRS})
    target_link_directories(brambhand_desktop PRIVATE ${SDL3_LIBRARY_DIRS})
    target_compile_options(brambhand_desktop PRIVATE ${SDL3_CFLAGS_OTHER})
    target_link_libraries(brambhand_desktop
      PRIVATE
        brambhand_client
        ${SDL3_LIBRARIES}
    )
  else()
    target_link_libraries(brambhand_desktop
      PRIVATE
        brambhand_client
        SDL3::SDL3
    )
  endif()
else()
  message(WARNING "SDL3 not found; skipping brambhand_desktop target. Install SDL3 dev packages or configure with -DBRAMBHAND_BUILD_DESKTOP_CLIENT=OFF.")
endif()

add_executable(brambhand_replay_ingest_benchmark
  replay_ingest_benchmark.cpp
  replay_ingest_benchmark_options.cpp
  replay_ingest_pipeline.cpp
)

target_link_libraries(brambhand_replay_ingest_benchmark
  PRIVATE
    brambhand_client
)
