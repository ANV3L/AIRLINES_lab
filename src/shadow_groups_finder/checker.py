import csv
import re
from collections import defaultdict
from pathlib import Path

# ---------- пути ----------
BASE = Path(__file__).resolve().parents[2]
TEMP = BASE / "resources" / "processed" / "temp"
OUT_SHADOW = BASE / "resources" / "processed" / "shadow_groups.csv"
OUT_SPIES = Path(__file__).resolve().parent / "SPIES.md"

# ---------- конфиг ----------
MIN_SHARED_FLIGHTS = 2
EMPTY_VALUES = {"", "NOT PRESENTED", "N/A", "NONE", "-", "NULL"}
DELIMS = ["|", ";", ",", "\t"]

# ---------- нормализация ----------
_APOS_RE = re.compile(r"['\u2018\u2019\u0060\u00B4]")


def normalize(v: str) -> str:
    return re.sub(r"\s+", " ", (v or "").strip().upper())


def norm_name(s: str) -> str:
    s = normalize(s)
    s = _APOS_RE.sub("", s)
    s = s.replace(".", "")
    s = s.replace("TCH", "CH").replace("SHCH", "SCH").replace("KH", "H").replace("PH", "F").replace("TH", "T")
    s = s.replace("TZ", "C").replace("TS", "C").replace("TC", "C")
    s = s.replace("X", "KS")
    s = s.replace("Y", "I").replace("J", "I")
    s = s.replace("II", "I").replace("EE", "I")
    s = re.sub(r"E(R?)$", r"\1", s)
    return s


def clean(v: str) -> str:
    s = normalize(v)
    s = re.sub(r"\s*N/?A\s*$", "", s)
    return s.strip() if s not in EMPTY_VALUES else ""


def normalize_flight(f: str) -> str:
    return normalize(f).replace(" ", "")


def normalize_date(d: str) -> str:
    s = (d or "").strip()
    if not s: return ""
    try:
        if "/" in s:
            parts = s.split("/")
            if len(parts) == 3:
                mm, dd, yyyy = parts
                return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"
        elif "." in s:
            parts = s.split(".")
            if len(parts) == 3:
                dd, mm, yyyy = parts
                return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"
        elif "-" in s:
            parts = s.split("-")
            if len(parts) == 3:
                yyyy, mm, dd = parts
                return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"
    except Exception:
        pass
    return s


def sniff_delimiter(p: Path) -> str:
    with p.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        first = f.readline().rstrip("\n")
    return max(DELIMS, key=lambda d: first.count(d))


# ---------- Совместимость отчеств ----------
def patronymic_compatible(a: str, b: str) -> bool:
    a, b = norm_name(a), norm_name(b)
    if not a or not b: return True
    a_init, b_init = len(a) == 1, len(b) == 1
    if a_init and b_init: return a == b
    if a_init: return b.startswith(a)
    if b_init: return a.startswith(b)
    return a == b


# ---------- КАНОНИЗАЦИЯ ИМЕН ----------
def apply_canonical_names(all_records):
    name_counts = defaultdict(int)
    for r in all_records:
        name_counts[r["name"]] += 1

    groups = defaultdict(list)
    for name in name_counts:
        parts = name.split()
        if len(parts) >= 2:
            groups[(parts[0], parts[1])].append(name)

    canonical_map = {}

    for key, names in groups.items():
        by_pat = defaultdict(list)
        for n in names:
            parts = n.split()
            pat = " ".join(parts[2:]) if len(parts) > 2 else ""
            by_pat[pat].append(n)

        pat_canonicals = {}
        for pat, variants in by_pat.items():
            best = sorted(variants, key=lambda x: (-len(x), -name_counts[x], x))[0]
            pat_canonicals[pat] = best

        sorted_pats = sorted(by_pat.keys(), key=lambda p: (-len(p), p))
        pat_mapping = {}

        for i, pat in enumerate(sorted_pats):
            if pat in pat_mapping: continue
            pat_mapping[pat] = pat
            for j in range(i + 1, len(sorted_pats)):
                other_pat = sorted_pats[j]
                if other_pat in pat_mapping: continue
                if patronymic_compatible(pat, other_pat):
                    pat_mapping[other_pat] = pat

        for pat, variants in by_pat.items():
            mapped_pat = pat_mapping.get(pat, pat)
            target_name = pat_canonicals[mapped_pat]
            for v in variants:
                canonical_map[v] = target_name

    for r in all_records:
        if r["name"] in canonical_map:
            r["name"] = canonical_map[r["name"]]


# ---------- парсинг ----------
def read_boarding_data(p: Path):
    rows = []
    delim = sniff_delimiter(p)
    with p.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        for row in csv.DictReader(f, delimiter=delim):
            name = norm_name(
                f"{row.get('PassengerLastName', '')} {row.get('PassengerFirstName', '')} {row.get('PassengerSecondName', '')}")
            if not name: continue
            rows.append({
                "name": name,
                "flight": normalize_flight(row.get("FlightNumber", "")),
                "date": normalize_date(row.get("FlightDate", "")),
                "agency": "",  # В этом файле нет агентства
                "booking": clean(row.get("BookingCode", "")),
                "docs": {clean(row.get("PassengerDocument", "")), clean(row.get("TicketNumber", ""))} - {""}
            })
    return rows


def read_sirena(p: Path):
    rows = []
    delim = sniff_delimiter(p)
    with p.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        for row in csv.DictReader(f, delimiter=delim):
            name = norm_name(row.get("PaxName", ""))
            if not name: continue
            rows.append({
                "name": name,
                "flight": normalize_flight(row.get("FlightCode", "")),
                "date": normalize_date(row.get("DepartDate", "")),
                "agency": clean(row.get("AgentInfo", "")),  # Берем именно агентство
                "booking": clean(row.get("Code", "")),
                "docs": {clean(row.get("TravelDoc", "")), clean(row.get("e-Ticket", ""))} - {""}
            })
    return rows


def read_cleaned_pass(p: Path):
    rows = []
    delim = sniff_delimiter(p)
    with p.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        for row in csv.DictReader(f, delimiter=delim):
            name = norm_name(f"{row.get('Фамилия', '')} {row.get('Имя', '')} {row.get('Отчество', '')}")
            if not name: continue
            rows.append({
                "name": name,
                "flight": normalize_flight(row.get("Номер_рейса", "")),
                "date": normalize_date(row.get("Дата_вылета", "")),
                "agency": "",  # В этом файле нет агентства
                "booking": clean(row.get("PNR_бронь", "")),
                "docs": {clean(row.get("Номер_эл_билета", "")), clean(row.get("Бонусная_карта", ""))} - {""}
            })
    return rows


# ---------- основной анализ ----------
def main():
    files = {
        "BoardingData": TEMP / "BoardingData_parsed.csv",
        "sirena": TEMP / "sirena_parsed.csv",
        "cleaned_boarding_pass": TEMP / "cleaned_boarding_pass.csv",
    }

    all_records = []
    if files["BoardingData"].exists(): all_records.extend(read_boarding_data(files["BoardingData"]))
    if files["sirena"].exists(): all_records.extend(read_sirena(files["sirena"]))
    if files["cleaned_boarding_pass"].exists(): all_records.extend(read_cleaned_pass(files["cleaned_boarding_pass"]))

    print(f"[i] Всего записей о перелетах до очистки: {len(all_records)}")

    apply_canonical_names(all_records)

    pax_flights = defaultdict(set)
    for r in all_records:
        if r["flight"] and r["date"]:
            pax_flights[r["name"]].add((r["flight"], r["date"]))

    active_pax = {name for name, flights in pax_flights.items() if len(flights) >= MIN_SHARED_FLIGHTS}
    print(f"[i] Уникальных пассажиров с >= {MIN_SHARED_FLIGHTS} рейсами: {len(active_pax)}")

    by_flight = defaultdict(list)
    for r in all_records:
        if r["flight"] and r["date"] and r["name"] in active_pax:
            by_flight[(r["flight"], r["date"])].append(r)

    pax_info = defaultdict(lambda: {"agencies": set(), "bookings": set(), "docs": set(), "raw_name": ""})
    for r in all_records:
        if r["agency"]: pax_info[r["name"]]["agencies"].add(r["agency"])
        if r["booking"]: pax_info[r["name"]]["bookings"].add(r["booking"])
        pax_info[r["name"]]["docs"] |= r["docs"]
        if not pax_info[r["name"]]["raw_name"]:
            pax_info[r["name"]]["raw_name"] = r["name"]

    pair_counts = defaultdict(int)
    pair_flights = defaultdict(set)

    flight_count = 0
    print("[i] Анализ совместных перелетов...")
    for (flight, date), records in by_flight.items():
        flight_count += 1
        if flight_count % 5000 == 0:
            print(f"    ... обработано {flight_count} рейсов")

        pax_on_flight = {}
        for r in records:
            name = r["name"]
            if name not in pax_on_flight:
                pax_on_flight[name] = {"docs": set(), "bookings": set()}
            pax_on_flight[name]["docs"] |= r["docs"]
            if r["booking"]:
                pax_on_flight[name]["bookings"].add(r["booking"])

        names = list(pax_on_flight.keys())
        for i in range(len(names)):
            n1 = names[i]
            p1 = pax_on_flight[n1]
            for j in range(i + 1, len(names)):
                n2 = names[j]
                p2 = pax_on_flight[n2]

                # Нет общих документов
                if p1["docs"] & p2["docs"]:
                    continue
                # Нет общих броней (PNR)
                if p1["bookings"] & p2["bookings"]:
                    continue

                pair_key = (n1, n2) if n1 < n2 else (n2, n1)
                pair_counts[pair_key] += 1
                if len(pair_flights[pair_key]) < 10:
                    pair_flights[pair_key].add((flight, date))

    print(f"[i] Уникальных пар, летавших вместе: {len(pair_counts)}")

    shadow_pairs = {pair: pair_flights[pair] for pair, count in pair_counts.items() if count >= MIN_SHARED_FLIGHTS}
    print(f"[i] Найдено теневых пар (>= {MIN_SHARED_FLIGHTS} совместных рейсов): {len(shadow_pairs)}")

    adj = defaultdict(set)
    for (n1, n2) in shadow_pairs:
        adj[n1].add(n2)
        adj[n2].add(n1)

    visited = set()
    groups = []

    for node in adj:
        if node in visited: continue
        component = []
        queue = [node]
        visited.add(node)
        while queue:
            curr = queue.pop(0)
            component.append(curr)
            for neighbor in adj[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        groups.append(component)

    group_data = []
    for grp in groups:
        grp_flights = set()
        for j in range(len(grp)):
            for k in range(j + 1, len(grp)):
                p1, p2 = grp[j], grp[k]
                pk = (p1, p2) if p1 < p2 else (p2, p1)
                if pk in shadow_pairs:
                    grp_flights |= shadow_pairs[pk]

        group_data.append({
            "members": grp,
            "flights": grp_flights
        })

    # Сортировка: сначала по количеству совместных рейсов, затем по размеру группы
    group_data.sort(key=lambda x: (len(x["flights"]), len(x["members"])), reverse=True)

    # Запись в CSV
    OUT_SHADOW.parent.mkdir(parents=True, exist_ok=True)
    with OUT_SHADOW.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(
            ["Group_ID", "Size", "Shared_Flights_Count", "Passengers", "Agencies", "Bookings", "Flights", "Docs"])

        for i, gd in enumerate(group_data, 1):
            grp = gd["members"]
            grp_flights = gd["flights"]

            grp_agencies = set()
            grp_bookings = set()
            grp_docs = set()
            pax_names = []
            for p in grp:
                grp_agencies |= pax_info[p]["agencies"]
                grp_bookings |= pax_info[p]["bookings"]
                grp_docs |= pax_info[p]["docs"]
                pax_names.append(pax_info[p]["raw_name"])

            w.writerow([
                f"SG_{i}",
                len(grp),
                len(grp_flights),
                " | ".join(pax_names),
                " | ".join(sorted(grp_agencies)),
                " | ".join(sorted(grp_bookings)),
                " | ".join(f"{fl[0]}({fl[1]})" for fl in sorted(grp_flights)),
                " | ".join(sorted(grp_docs))
            ])

    print(f"[shadow_groups.csv] записей: {len(group_data)} -> {OUT_SHADOW}")
    update_spies_md(group_data, pax_info, len(all_records))


def update_spies_md(group_data, pax_info, total_records):
    header = "## Теневые группы пассажиров (checker.py)"
    lines = [header + "\n\n"]

    lines.append("Пассажиры, которые не пересекаются по документам и броням, ")
    lines.append("но регулярно летают одними и теми же рейсами.\n\n")

    lines.append(f"- Всего перелетов проанализировано: **{total_records}**\n")
    lines.append(f"- Найдено теневых групп: **{len(group_data)}**\n")
    lines.append(f"- Мин. совместных рейсов для группы: **{MIN_SHARED_FLIGHTS}**\n\n")

    if not group_data:
        lines.append("_Теневых групп не найдено._\n\n")
    else:
        lines.append("### Список групп (отсортировано по кол-ву совместных рейсов)\n\n")
        lines.append("| ID | Размер | Совместных рейсов | Пассажиры | Сайты (Агентства) |\n")
        lines.append("|---|---|---|---|---|\n")
        for i, gd in enumerate(group_data, 1):
            grp = gd["members"]
            grp_flights = gd["flights"]

            agencies = set()
            names = []
            for p in grp:
                agencies |= pax_info[p]["agencies"]
                names.append(pax_info[p]["raw_name"])

            agencies_str = "<br>".join(agencies) if agencies else "N/A (билеты без агентств)"
            lines.append(f"| SG_{i} | {len(grp)} | **{len(grp_flights)}** | {'<br>'.join(names)} | {agencies_str} |\n")
        lines.append("\n")

    new_section = "".join(lines)
    text = OUT_SPIES.read_text(encoding="utf-8") if OUT_SPIES.exists() else "# SPIES — подозрительные пассажиры\n\n"

    pattern = re.compile(re.escape(header) + r".*?(?=\n## |\Z)", re.DOTALL)
    text = pattern.sub("", text).rstrip() + "\n\n" + new_section
    OUT_SPIES.write_text(text, encoding="utf-8")
    print(f"[SPIES.md] обновлён: {OUT_SPIES}")


if __name__ == "__main__":
    main()