add_library(parsers INTERFACE)

target_include_directories(parsers INTERFACE
        "${CMAKE_CURRENT_SOURCE_DIR}"
        "${CMAKE_BINARY_DIR}/_deps/pugixml-src/src"
)

target_link_libraries(parsers INTERFACE nlohmann_json::nlohmann_json)