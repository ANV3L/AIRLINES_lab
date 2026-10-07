#pragma once
#include <pugixml.hpp>

#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>


inline std::string csv_escape_xml(const std::string& s) {
    bool need_quotes = s.find('|') != std::string::npos ||
                       s.find('"') != std::string::npos ||
                       s.find('\n') != std::string::npos;
    if (!need_quotes) return s;

    std::string out = "\"";
    for (char c : s) {
        if (c == '"') out += "\"\"";
        else          out += c;
    }
    out += '"';
    return out;
}

inline void write_xml_csv(const std::string& input_path, std::ostream& out) {
    pugi::xml_document doc;
    pugi::xml_parse_result res = doc.load_file(input_path.c_str());

    if (!res)
        throw std::runtime_error(
            "XML parse error at offset " + std::to_string(res.offset) +
            ": " + res.description());

    pugi::xml_node root = doc.child("PointzAggregatorUsers");
    if (!root)
        throw std::runtime_error("root <PointzAggregatorUsers> not found");

    out << "UserId|FirstName|LastName|CardNumber|BonusProgram|"
           "Code|Date|Departure|Arrival|Fare\n";

    std::size_t rows = 0;
    size_t count = 0;
    for (pugi::xml_node user : root.children("user")) {
        std::cout << "--xml_parse: " << count++ << std::endl;
        const std::string uid = user.attribute("uid").as_string();

        pugi::xml_node name = user.child("name");
        const std::string first = name.attribute("first").as_string();
        const std::string last  = name.attribute("last").as_string();

        pugi::xml_node cards = user.child("cards");
        for (pugi::xml_node card : cards.children("card")) {
            const std::string card_number  = card.attribute("number").as_string();
            const std::string bonus_prog   = card.child("bonusprogramm").text().as_string();

            pugi::xml_node activities = card.child("activities");
            for (pugi::xml_node act : activities.children("activity")) {
                if (std::string(act.attribute("type").as_string()) != "Flight")
                    continue;

                const std::string code      = act.child("Code").text().as_string();
                const std::string date      = act.child("Date").text().as_string();
                const std::string departure = act.child("Departure").text().as_string();
                const std::string arrival   = act.child("Arrival").text().as_string();
                const std::string fare      = act.child("Fare").text().as_string();

                out << csv_escape_xml(uid)         << '|'
                    << csv_escape_xml(first)       << '|'
                    << csv_escape_xml(last)        << '|'
                    << csv_escape_xml(card_number) << '|'
                    << csv_escape_xml(bonus_prog)  << '|'
                    << csv_escape_xml(code)        << '|'
                    << csv_escape_xml(date)        << '|'
                    << csv_escape_xml(departure)   << '|'
                    << csv_escape_xml(arrival)     << '|'
                    << csv_escape_xml(fare)        << '\n';

                ++rows;
            }
        }
    }

    std::cout << "[xml] rows written: " << rows << "\n";
}


inline void convert_xml(const std::string& input_path, std::ostream& out) {
    write_xml_csv(input_path, out);
}

inline std::string convert_xml_to_string(const std::string& input_path) {
    std::ostringstream ss;
    write_xml_csv(input_path, ss);
    return ss.str();
}


inline void parse_xml() {
    const std::string input_path  = "../../resources/raw/PointzAggregator-AirlinesData.xml";
    const std::string output_path = "../../resources/processed/xml_parsed.csv";

    std::ostringstream ss;
    write_xml_csv(input_path, ss);

    std::ofstream fout(output_path, std::ios::binary);
    if (!fout)
        throw std::runtime_error("cannot open output file for writing: " + output_path);

    fout << ss.str();

    std::cout << "[out] wrote " << ss.str().size()
              << " bytes to " << output_path << "\n";
}
