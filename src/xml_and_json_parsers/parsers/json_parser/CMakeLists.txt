add_executable(json_parser main.cpp)

target_include_directories(json_parser PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

target_compile_options(json_parser PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(json_parser PRIVATE nlohmann_json::nlohmann_json)