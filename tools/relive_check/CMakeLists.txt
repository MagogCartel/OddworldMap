# A shim project around alive_reversing's relive_api directory alone: that
# directory is self-contained (the editor consumes it the same way), while the
# decomp's own root CMakeLists demands SDL2 the api never links.
cmake_minimum_required(VERSION 3.15)
project(relive_check CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(ALIVE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../../alive_reversing" CACHE PATH
    "alive_reversing checkout (sibling of this repo by default)")

add_compile_definitions(ELPP_NO_DEFAULT_LOG_FILE)
add_subdirectory("${ALIVE_DIR}/Source/Tools/relive_api" relive_api)

add_executable(relive_check relive_check.cpp)
target_link_libraries(relive_check relive_api)
