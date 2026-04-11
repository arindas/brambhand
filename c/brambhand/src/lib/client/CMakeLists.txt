add_library(brambhand_client STATIC
  client_common.cpp
)

target_include_directories(brambhand_client
  PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)
