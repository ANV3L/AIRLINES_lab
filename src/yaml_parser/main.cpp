#include "parser_yaml.hpp"

int main() {
    try {
        parse_yaml();
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}