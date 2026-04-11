add_executable(brambhand_desktop
  main.cpp
)

target_link_libraries(brambhand_desktop
  PRIVATE
    brambhand_client_common
)
