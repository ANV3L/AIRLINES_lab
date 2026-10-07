#include "parse_json.hpp"
#include "parse_xml.hpp"


int main() {
    try {
        parse_json();
        parse_xml();
    } catch (const std::exception& e) {
        std::cerr << e.what() << "\n";
        return 1;
    }
    return 0;
}
