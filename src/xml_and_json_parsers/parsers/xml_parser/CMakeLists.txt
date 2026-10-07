add_executable(xml_parser main.cpp)

target_include_directories(xml_parser PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/include"
        "${CMAKE_BINARY_DIR}/_deps/pugixml-src/src"
)

target_compile_options(xml_parser PRIVATE -Wall -Wextra -Wpedantic)
target_link_libraries(xml_parser PRIVATE pugixml::pugixml)