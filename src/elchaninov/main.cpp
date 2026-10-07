#include "parse_json.hpp"


int main() {
    try {
        parse_json();
    } catch (const std::exception& e) {
        std::cerr << e.what() << "\n";
        return 1;
    }
    return 0;
}