#pragma once

#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
#include <string>


using json = nlohmann::json;

inline std::string csv_escape_json(const std::string& s) {
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

inline void write_csv(const std::string& input_path, std::ostream& out) {
    std::ifstream fin(input_path, std::ios::binary);
    if (!fin)
        throw std::runtime_error("cannot open input file: " + input_path);

    json root;
    try {
        fin >> root;
    } catch (const std::exception& e) {
        throw std::runtime_error(std::string("JSON parse error: ") + e.what());
    }

    out << "Date|Codeshare|Flight"
           "|DepCity|DepAirport|DepCountry"
           "|ArrCity|ArrAirport|ArrCountry\n";

    size_t count = 0;
    for (const auto& profile : root.at("Forum Profiles")) {
        std::cout << "--json_parse: " << count++ << std::endl;
        auto it = profile.find("Registered Flights");
        if (it == profile.end() || !it->is_array()) continue;

        for (const auto& f : *it) {
            const auto& dep = f.at("Departure");
            const auto& arr = f.at("Arrival");

            out << csv_escape_json(f.value("Date", ""))                 << '|'
                << (f.value("Codeshare", false) ? "true" : "false")  << '|'
                << csv_escape_json(f.value("Flight", ""))               << '|'
                << csv_escape_json(dep.value("City", ""))               << '|'
                << csv_escape_json(dep.value("Airport", ""))            << '|'
                << csv_escape_json(dep.value("Country", ""))            << '|'
                << csv_escape_json(arr.value("City", ""))               << '|'
                << csv_escape_json(arr.value("Airport", ""))            << '|'
                << csv_escape_json(arr.value("Country", ""))            << '\n';
        }
    }
}


inline void parse_json() {
    const std::string input_path  = "../../resources/raw/FrequentFlyerForum-Profiles.json";
    const std::string output_path = "../../resources/processed/json_parsed.csv";

    std::ostringstream ss;
    write_csv(input_path, ss);

    std::ofstream fout(output_path, std::ios::binary);
    if (!fout)
        throw std::runtime_error("cannot open output file for writing: " + output_path);

    fout << ss.str();

    std::cerr << "[out] wrote " << ss.str().size()
              << " bytes to " << output_path << "\n";
}
