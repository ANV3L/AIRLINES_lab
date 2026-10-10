#pragma once

#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <regex>
#include <vector>

inline std::string csv_escape_yaml(const std::string& s) {
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

struct FFEntry {
    std::string airline;
    std::string number;
    std::string flight_class;
    std::string fare;
};

inline void write_yaml_csv(const std::string& input_path, std::ostream& out) {
    std::ifstream fin(input_path);
    if (!fin)
        throw std::runtime_error("cannot open input file: " + input_path);

    out << "Date|Flight|From|To|Status|FF_Airline|FF_Number|Class|Fare\n";

    std::string line;
    std::string current_date;
    std::string current_flight;
    std::string from_airport, to_airport, status;
    std::vector<FFEntry> current_ff_entries;
    
    size_t count = 0;
    size_t line_num = 0;
    
    
    std::regex date_re(R"(^'([^']+)':\s*$)");
    std::regex flight_re(R"(^\s{2}([A-Za-z0-9\-]+):\s*$)");
    std::regex ff_re(R"(\s{6}([A-Z]+)\s+(\d+):)");
    std::regex field_re(R"(^\s{4}([A-Z]+):\s*(.+)$)");
    std::regex class_re(R"(CLASS:\s*([A-Za-z0-9]+))");
    std::regex fare_re(R"(FARE:\s*([A-Za-z0-9]+))");
    
    
    auto process_flight = [&]() {
        if (current_flight.empty() || current_ff_entries.empty()) return;
        
        for (const auto& ff : current_ff_entries) {
            out << csv_escape_yaml(current_date)         << '|'
                << csv_escape_yaml(current_flight)        << '|'
                << csv_escape_yaml(from_airport)          << '|'
                << csv_escape_yaml(to_airport)            << '|'
                << csv_escape_yaml(status)                << '|'
                << csv_escape_yaml(ff.airline)            << '|'
                << csv_escape_yaml(ff.number)             << '|'
                << csv_escape_yaml(ff.flight_class)       << '|'
                << csv_escape_yaml(ff.fare)               << '\n';
            ++count;
        }
    };
    
    
    auto reset_flight_state = [&]() {
        current_flight.clear();
        from_airport.clear();
        to_airport.clear();
        status.clear();
        current_ff_entries.clear();
    };

    while (std::getline(fin, line)) {
        ++line_num;
        
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty()) continue;
        
        std::smatch match;
        
        if (std::regex_match(line, match, date_re)) {
            current_date = match[1].str();
            continue;
        }
        
        if (std::regex_match(line, match, flight_re)) {
            process_flight();      
            reset_flight_state();  
            current_flight = match[1].str();
            continue;
        }
        
        if (std::regex_search(line, match, ff_re)) {
            FFEntry entry;
            entry.airline = match[1].str();
            entry.number = match[2].str();
            
            if (std::regex_search(line, match, class_re)) {
                entry.flight_class = match[1].str();
            }
            if (std::regex_search(line, match, fare_re)) {
                entry.fare = match[1].str();
            }
            
            current_ff_entries.push_back(entry);
            continue;
        }
        
        if (std::regex_match(line, match, field_re)) {
            std::string key = match[1].str();
            std::string val = match[2].str();
            
            if (key == "FROM") from_airport = val;
            else if (key == "TO") to_airport = val;
            else if (key == "STATUS") status = val;
        }
        
        if (line_num % 500000 == 0) {
            std::cout << "\rОбработано строк: " << line_num << " | Записано FF-записей: " << count << std::flush;
        }
    }
    process_flight();
    
    std::cout << "\n[yaml] total FF rows written: " << count << "\n";
}

inline void parse_yaml() {
    const std::string input_path  = "../../resources/raw/SkyTeam-Exchange.yaml";
    const std::string output_path = "../../resources/processed/yaml_parsed.csv";

    std::ofstream fout(output_path, std::ios::binary);
    if (!fout)
        throw std::runtime_error("cannot open output file for writing: " + output_path);

    write_yaml_csv(input_path, fout);

    std::cout << "[out] wrote to " << output_path << "\n";
}