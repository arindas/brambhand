cmake_minimum_required(VERSION 3.21)
project(brambhand_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BRAMBHAND_BUILD_DESKTOP_CLIENT "Build desktop client" ON)

add_subdirectory(src/lib/client_common)

if(BRAMBHAND_BUILD_DESKTOP_CLIENT)
  add_subdirectory(src/bin/desktop)
endif()
