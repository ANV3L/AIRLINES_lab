cmake_minimum_required(VERSION 3.10)
project(yaml_parser)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(yaml-cpp REQUIRED)
add_executable(yaml_parser main.cpp)
target_link_libraries(yaml_parser PRIVATE yaml-cpp)

if(MSVC)
    target_compile_options(yaml_parser PRIVATE /W4)
else()
    target_compile_options(yaml_parser PRIVATE -Wall -Wextra)
endif()