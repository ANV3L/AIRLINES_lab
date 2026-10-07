cmake_minimum_required(VERSION 3.20)
project(collect LANGUAGES CXX VERSION 1.0.0)

SET(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

add_compile_options(-Wall -Wextra -Wpedantic)

find_package(nlohmann_json 3.11 REQUIRED)
add_subdirectory(src)
add_executable(collect main.cpp)
target_link_libraries(collect PRIVATE src)


