#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <unordered_map>
#include <set>
#include <algorithm>
#include <filesystem>
#include <cmath>
#include <iomanip>

namespace fs = std::filesystem;

// --- Список главных подозреваемых ---
std::set<std::string> CRITICAL_SUSPECTS = {
    "GLEBOV GORDEI",
    "BUROV RAMIL",
    "GOLOVINA OLESIA",
    "MASLENNIKOV ROMAN"
};

// --- Структуры данных ---
struct Person {
    std::string fio;
    bool is_suspicious = false;
    int age_at_issue = -1;
    std::map<std::string, int> dep_airports;
    std::map<std::string, int> arr_airports;
};

struct SuspectStats {
    std::map<std::string, int> deps;
    std::map<std::string, int> arrs;
    int age_at_issue = -1;
    bool found_in_base = false;
};

// --- Утилиты ---
std::string trim(const std::string& str) {
    size_t first = str.find_first_not_of(" \t\r\n\"");
    if (std::string::npos == first) return "";
    size_t last = str.find_last_not_of(" \t\r\n\"");
    return str.substr(first, (last - first + 1));
}

std::string to_lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), ::tolower);
    return s;
}

std::string to_upper(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), ::toupper);
    return s;
}

// Объединение городов и кодов IATA
std::string normalize_airport(std::string a) {
    a = to_upper(trim(a));
    if (a == "MOSCOW" || a == "МОСКВА") return "SVO";
    if (a == "KHABAROVSK" || a == "ХАБАРОВСК") return "KHV";
    if (a == "VLADIVOSTOK" || a == "ВЛАДИВОСТОК") return "VVO";
    if (a == "SOCHI" || a == "СОЧИ") return "AER";
    if (a == "YUZHNO" || a == "ЮЖНО-САХАЛИНСК") return "UUS";
    if (a == "ST. PETERSBURG" || a == "САНКТ-ПЕТЕРБУРГ" || a == "SAINT PETERSBURG") return "LED";
    if (a == "NOVOSIBIRSK" || a == "НОВОСИБИРСК") return "OVB";
    if (a == "EKATERINBURG" || a == "ЕКАТЕРИНБУРГ") return "SVX";
    if (a == "KRASNODAR" || a == "КРАСНОДАР") return "KRR";
    if (a == "ROSTOV" || a == "РОСТОВ-НА-ДОНУ") return "ROV";
    // Если это уже код IATA (3 буквы), возвращаем как есть
    if (a.length() == 3) return a;
    return a;
}

std::string format_top_routes(const std::map<std::string, int>& routes) {
    if (routes.empty()) return "нет данных";
    std::vector<std::pair<std::string, int>> sorted(routes.begin(), routes.end());
    std::sort(sorted.begin(), sorted.end(), [](auto& a, auto& b) { return a.second > b.second; });

    std::string res;
    int limit = std::min((int)sorted.size(), 3);
    for (int i = 0; i < limit; ++i) {
        res += "`" + sorted[i].first + "` (" + std::to_string(sorted[i].second) + ")";
        if (i < limit - 1) res += ", ";
    }
    return res;
}

// --- Парсинг файла ---
void process_file(const fs::path& filepath, std::unordered_map<std::string, Person>& people, std::map<std::string, SuspectStats>& critical_stats) {
    std::ifstream file(filepath);
    if (!file.is_open()) return;

    std::string line;
    if (!std::getline(file, line)) return;

    char delim = (line.find('|') != std::string::npos) ? '|' : ';';

    std::vector<std::string> headers;
    std::stringstream ss(line);
    std::string col;
    while (std::getline(ss, col, delim)) headers.push_back(to_lower(trim(col)));

    auto get_col_idx = [&](const std::vector<std::string>& names) -> int {
        for (size_t i = 0; i < headers.size(); ++i)
            for (const auto& n : names) if (headers[i] == n) return i;
        return -1;
    };

    int idx_last = get_col_idx({"passenger_last"});
    int idx_first = get_col_idx({"passenger_first"});
    int idx_mid = get_col_idx({"passenger_middle"});
    int idx_birth = get_col_idx({"birth_date"});
    int idx_doc_series = get_col_idx({"doc_series"});
    int idx_dep = get_col_idx({"dep_airport"});
    int idx_arr = get_col_idx({"arr_airport"});
    int idx_arr_city = get_col_idx({"arr_city"});

    if (idx_last == -1 && idx_first == -1) return;

    while (std::getline(file, line)) {
        std::stringstream ss_row(line);
        std::vector<std::string> row;
        std::string val;
        while (std::getline(ss_row, val, delim)) row.push_back(val);
        if (row.size() < headers.size()) continue;

        std::string fio = "";
        if (idx_last != -1) fio += trim(row[idx_last]) + " ";
        if (idx_first != -1) fio += trim(row[idx_first]) + " ";
        if (idx_mid != -1) fio += trim(row[idx_mid]);
        fio = trim(fio);

        if (fio.empty() || fio == " ") continue;

        std::string person_key = fio;

        if (people.find(person_key) == people.end()) {
            Person p; p.fio = fio;
            people[person_key] = p;
        }
        Person& p = people[person_key];

        std::string birth = idx_birth != -1 ? trim(row[idx_birth]) : "";
        std::string series = idx_doc_series != -1 ? trim(row[idx_doc_series]) : "";

        std::string dep = idx_dep != -1 ? normalize_airport(row[idx_dep]) : "";
        std::string arr = idx_arr != -1 ? normalize_airport(row[idx_arr]) : "";
        if (arr.empty() && idx_arr_city != -1) {
            arr = normalize_airport(row[idx_arr_city]);
        }

        int best_age = -1;
        if (!birth.empty() && birth != "NULL" && series.length() == 4) {
            try {
                int birth_year = std::stoi(birth.substr(0, 4));
                int yy = std::stoi(series.substr(2, 2));
                int c1 = 1900 + yy, c2 = 2000 + yy;
                int age1 = c1 - birth_year, age2 = c2 - birth_year;

                if (age1 < 0 || age2 < 0) best_age = 0;
                else if (age1 >= 0 && age1 < 11) best_age = age1;
                else if (age2 >= 0 && age2 < 11) best_age = age2;
            } catch (...) {}
        }

        for (const auto& target : CRITICAL_SUSPECTS) {
            if (fio.find(target) != std::string::npos) {
                critical_stats[target].found_in_base = true;
                if (!dep.empty() && dep != "NULL") critical_stats[target].deps[dep]++;
                if (!arr.empty() && arr != "NULL") critical_stats[target].arrs[arr]++;

                if (best_age != -1) {
                    if (critical_stats[target].age_at_issue == -1) critical_stats[target].age_at_issue = best_age;
                    else critical_stats[target].age_at_issue = std::min(critical_stats[target].age_at_issue, best_age);
                }
            }
        }

        if (best_age != -1) {
            p.is_suspicious = true;
            if (p.age_at_issue == -1) p.age_at_issue = best_age;
            else p.age_at_issue = std::min(p.age_at_issue, best_age);
        }

        if (!dep.empty() && dep != "NULL" && dep != "N/A") p.dep_airports[dep]++;
        if (!arr.empty() && arr != "NULL" && arr != "N/A") p.arr_airports[arr]++;
    }
}

// --- Отрисовка барчарта в SVG ---
// Внимание: в этой функции margin_left отвечает за названия категорий (Y), а x_label - за подпись оси значений (X)
void draw_bar_chart(const std::string& filename, const std::string& title,
                    const std::string& x_label_value, // Подпись снизу (Кол-во)
                    const std::string& y_label_category, // Подпись слева (Категория)
                    const std::string& unit_suffix,
                    const std::vector<std::pair<std::string, int>>& data,
                    const std::string& color = "#3498db") {

    int width = 1200, margin_left = 350, margin_right = 150, margin_top = 80, margin_bottom = 120;
    int bar_height = 35, gap = 15;
    int chart_width = width - margin_left - margin_right;
    int chart_height = data.size() * (bar_height + gap);
    int height = margin_top + chart_height + margin_bottom;
    int axis_y = margin_top + chart_height - gap;

    std::ofstream svg(filename);
    svg << "<svg width='" << width << "' height='" << height << "' xmlns='http://www.w3.org/2000/svg' style='background-color: white;'>\n";

    if (data.empty()) {
        svg << "<text x='" << width/2 << "' y='" << height/2 << "' text-anchor='middle' font-size='24' font-family='Arial'>Нет данных</text>\n</svg>\n";
        return;
    }

    int max_val = 1;
    for (auto& p : data) if (p.second > max_val) max_val = p.second;

    svg << "<text x='" << width/2 << "' y='40' text-anchor='middle' font-size='24' font-weight='bold' font-family='Arial, sans-serif'>" << title << "</text>\n";

    // Оси
    svg << "<line x1='" << margin_left << "' y1='" << margin_top << "' x2='" << margin_left << "' y2='" << axis_y << "' stroke='#333' stroke-width='2'/>\n";
    svg << "<line x1='" << margin_left << "' y1='" << axis_y << "' x2='" << (width - margin_right) << "' y2='" << axis_y << "' stroke='#333' stroke-width='2'/>\n";

    // Подписи осей (X внизу, Y слева)
    svg << "<text x='" << (margin_left + chart_width/2) << "' y='" << height - 20 << "' text-anchor='middle' font-size='18' font-family='Arial, sans-serif'>" << x_label_value << "</text>\n";
    svg << "<text x='30' y='" << (margin_top + chart_height/2) << "' text-anchor='middle' font-size='18' font-family='Arial, sans-serif' transform='rotate(-90 30 " << (margin_top + chart_height/2) << ")'>" << y_label_category << "</text>\n";

    for (int i = 1; i <= 5; ++i) {
        int x = margin_left + (chart_width * i) / 5;
        int val = (max_val * i) / 5;
        svg << "<line x1='" << x << "' y1='" << margin_top << "' x2='" << x << "' y2='" << axis_y << "' stroke='#ddd' stroke-width='1' stroke-dasharray='6'/>\n";
        svg << "<text x='" << x << "' y='" << (axis_y + 30) << "' text-anchor='middle' font-size='16' fill='#666' font-family='Arial, sans-serif'>" << val << "</text>\n";
    }

    int y_offset = margin_top;
    for (size_t i = 0; i < data.size(); ++i) {
        int bar_w = std::max(3, (data[i].second * chart_width) / max_val);
        svg << "<rect x='" << margin_left << "' y='" << y_offset << "' width='" << bar_w << "' height='" << bar_height << "' fill='" << color << "'/>\n";
        svg << "<text x='" << (margin_left - 15) << "' y='" << (y_offset + 24) << "' text-anchor='end' font-size='16' font-family='Arial, sans-serif'>" << data[i].first << "</text>\n";
        svg << "<text x='" << (margin_left + bar_w + 15) << "' y='" << (y_offset + 24) << "' font-size='16' font-weight='bold' font-family='Arial, sans-serif'>" << data[i].second << " " << unit_suffix << "</text>\n";
        y_offset += bar_height + gap;
    }
    svg << "</svg>\n";
}

int main() {
    std::cout << "Loading data..." << std::endl;
    std::unordered_map<std::string, Person> people;
    std::map<std::string, SuspectStats> critical_stats;

    std::string processed_dir = "resources/processed/";
    if (!fs::exists(processed_dir)) processed_dir = "../../resources/processed/";

    for (const auto& entry : fs::directory_iterator(processed_dir)) {
        if (entry.is_regular_file()) {
            std::string filename = entry.path().filename().string();
            if (filename.find("_norm.csv") != std::string::npos) {
                std::cout << "Reading: " << filename << std::endl;
                process_file(entry.path(), people, critical_stats);
            }
        }
    }

    std::map<int, int> age_counts;
    std::map<std::string, int> dep_counts;
    std::map<std::string, int> arr_counts;
    int unique_suspicious_people = 0;

    for (const auto& [key, p] : people) {
        if (p.is_suspicious) {
            age_counts[p.age_at_issue]++;
            unique_suspicious_people++;

            for (const auto& pair : p.dep_airports) dep_counts[pair.first] += pair.second;
            for (const auto& pair : p.arr_airports) arr_counts[pair.first] += pair.second;
        }
    }

    std::cout << "Suspicious people found: " << unique_suspicious_people << std::endl;

    std::vector<std::pair<std::string, int>> age_chart;
    for (auto const& [age, count] : age_counts) {
        std::string label = (age == 0) ? "0 (раньше рождения)" : std::to_string(age) + " лет";
        age_chart.push_back({label, count});
    }

    std::vector<std::pair<std::string, int>> top_dep(dep_counts.begin(), dep_counts.end());
    std::sort(top_dep.begin(), top_dep.end(), [](auto& a, auto& b) { return a.second > b.second; });
    if (top_dep.size() > 10) top_dep.resize(10);

    std::vector<std::pair<std::string, int>> top_arr(arr_counts.begin(), arr_counts.end());
    std::sort(top_arr.begin(), top_arr.end(), [](auto& a, auto& b) { return a.second > b.second; });
    if (top_arr.size() > 10) top_arr.resize(10);

    // Передаем правильные подписи: X (значение) и Y (категория)
    draw_bar_chart("chart_age.svg", "Распределение по возрасту выдачи паспорта",
                   "Количество человек", "Возраст при получении паспорта", "чел.", age_chart, "#e67e22");

    draw_bar_chart("chart_departures.svg", "Топ-10 аэропортов вылета (подозрительные лица)",
                   "Количество вылетов", "Код аэропорта вылета (IATA)", "раз", top_dep, "#3498db");

    draw_bar_chart("chart_arrivals.svg", "Топ-10 аэропортов прилета (подозрительные лица)",
                   "Количество прилетов", "Код аэропорта прилета (IATA)", "раз", top_arr, "#2ecc71");

    // Отчет
    std::ofstream md("staticAn.md");
    md << "# Статический анализ пассажиров (Поиск шпионов)\n\n";

    md << "## 🔴 1. Главные подозреваемые (Критические находки)\n";
    md << "| Подозреваемый | Аномалия паспорта | Чаще всего вылетал из | Чаще всего прилетал в |\n";
    md << "|---|---|---|---|\n";

    for (const auto& target : CRITICAL_SUSPECTS) {
        if (critical_stats.find(target) != critical_stats.end() && critical_stats[target].found_in_base) {
            std::string passport_status = "Нет (нормальный)";
            if (critical_stats[target].age_at_issue != -1) {
                if (critical_stats[target].age_at_issue == 0) passport_status = "⚠️ **Да (раньше рождения)**";
                else passport_status = "⚠️ **Да (в " + std::to_string(critical_stats[target].age_at_issue) + " лет)**";
            }
            std::string top_dep = format_top_routes(critical_stats[target].deps);
            std::string top_arr = format_top_routes(critical_stats[target].arrs);
            md << "| **" << target << "** | " << passport_status << " | " << top_dep << " | " << top_arr << " |\n";
        } else {
            md << "| **" << target << "** | _нет данных_ | _нет данных_ | _нет данных_ |\n";
        }
    }
    md << "\n---\n\n";

    md << "## 2. Паспорта, выданные ранее 11 лет\n";
    md << "- **Уникальных людей с аномалией:** " << unique_suspicious_people << "\n\n";
    md << "### Распределение по возрасту выдачи\n";
    md << "![График возрастов](chart_age.svg)\n\n";

    md << "## 3. Общая география подозрительных лиц\n";
    md << "### Откуда они вылетали (Топ-10 аэропортов)\n";
    md << "![Вылеты](chart_departures.svg)\n\n";
    md << "### Куда они прилетали (Топ-10 аэропортов)\n";
    md << "![Прилеты](chart_arrivals.svg)\n\n";

    md.close();
    std::cout << "Done! Check staticAn.md and SVG files." << std::endl;
    return 0;
}