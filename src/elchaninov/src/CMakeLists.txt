add_library(src INTERFACE)

target_include_directories(src INTERFACE
        "${CMAKE_CURRENT_SOURCE_DIR}"
)

target_link_libraries(src INTERFACE nlohmann_json::nlohmann_json)