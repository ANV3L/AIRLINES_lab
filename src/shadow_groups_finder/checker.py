import csv
import re
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path

# ---------- пути ----------
BASE = Path(__file__).resolve().parents[2]
TEMP = BASE / "resources" / "processed"
OUT_SHADOW = BASE / "resources" / "processed" / "shadow_groups.csv"
OUT_SPIES = Path(__file__).resolve().parent / "SPIES.md"
OUT_REPORT = Path(__file__).resolve().parent / "report.md"

# ---------- конфиг ----------
MIN_SHARED_FLIGHTS = 2  # Минимум совместных рейсов (в одни и те же даты)
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
    print("[STEP 1/5] Канонизация имен (склейка инициалов и полных имен)...")
    t0 = time.time()

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

    print(
        f"    -> Уникальных имен до: {len(name_counts)}, после: {len(set(r['name'] for r in all_records))} (за {time.time() - t0:.2f} сек)")


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
                "agency": "",
                "booking": clean(row.get("BookingCode", "")),
                "docs": {clean(row.get("PassengerDocument", "")), clean(row.get("TicketNumber", ""))} - {""}
            })
    print(f"    -> {p.name}: {len(rows)} записей")
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
                "agency": clean(row.get("AgentInfo", "")),
                "booking": clean(row.get("Code", "")),
                "docs": {clean(row.get("TravelDoc", "")), clean(row.get("e-Ticket", ""))} - {""}
            })
    print(f"    -> {p.name}: {len(rows)} записей")
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
                "agency": "",
                "booking": clean(row.get("PNR_бронь", "")),
                "docs": {clean(row.get("Номер_эл_билета", "")), clean(row.get("Бонусная_карта", ""))} - {""}
            })
    print(f"    -> {p.name}: {len(rows)} записей")
    return rows


# ---------- запись отчетов ----------
def update_spies_md(groups, pax_info, total_records):
    header = "## Теневые группы пассажиров (checker.py)"
    lines = [header + "\n\n"]

    lines.append("Пассажиры, которые регулярно летают вместе на одних и тех же рейсах ")
    lines.append("в одни и те же даты, но не пересекаются по документам и броням.\n\n")

    lines.append(f"- Всего перелетов проанализировано: **{total_records}**\n")
    lines.append(f"- Найдено теневых групп: **{len(groups)}**\n")
    lines.append(f"- Мин. совместных рейсов для группы: **{MIN_SHARED_FLIGHTS}**\n\n")

    if not groups:
        lines.append("_Теневых групп не найдено._\n\n")
    else:
        lines.append("### Список групп (отсортировано по кол-ву совместных рейсов)\n\n")
        lines.append("| ID | Размер | Совместных рейсов | Пассажиры | Сайты | Пересечения (Рейс + Дата) |\n")
        lines.append("|---|---|---|---|---|---|\n")
        for i, (grp, grp_flights) in enumerate(groups, 1):
            agencies = set()
            names = []
            for p in grp:
                agencies |= pax_info[p]["agencies"]
                names.append(pax_info[p]["raw_name"])

            flights_sample = ", ".join(f"{fl.split('_')[0]} ({fl.split('_')[1]})" for fl in sorted(grp_flights)[:5])
            if len(grp_flights) > 5: flights_sample += "..."

            agencies_str = "<br>".join(agencies) if agencies else "N/A"

            lines.append(
                f"| SG_{i} | {len(grp)} | **{len(grp_flights)}** | {'<br>'.join(names)} | {agencies_str} | {flights_sample} |\n")
        lines.append("\n")

    new_section = "".join(lines)
    text = OUT_SPIES.read_text(encoding="utf-8") if OUT_SPIES.exists() else "# SPIES — подозрительные пассажиры\n\n"

    pattern = re.compile(re.escape(header) + r".*?(?=\n## |\Z)", re.DOTALL)
    text = pattern.sub("", text).rstrip() + "\n\n" + new_section
    OUT_SPIES.write_text(text, encoding="utf-8")
    print(f"    -> {OUT_SPIES.name} обновлён.")


def write_report_md(groups, pax_info, total_records, files_stats):
    """Генерирует краткий отчет (для VIEW) человеческим языком."""

    lines = []
    lines.append("### Отчет по поиску теневых групп\n")
    lines.append(
        "Проанализировал данные о перелетах. Искал пассажиров, которые регулярно летают вместе на одних и тех же рейсах в одни и те же даты, но при этом покупают билеты через разные каналы (разные PNR и без общих документов).\n")

    # --- БЛОК: ИСПОЛЬЗОВАННЫЕ ФАЙЛЫ ---
    used_files = [name for name, count in files_stats if count > 0]
    if used_files:
        files_str = ", ".join(f"`{f}`" for f in used_files)
        lines.append(f"**Данные для анализа брались из:** {files_str}\n")
    else:
        lines.append("**Данные для анализа:** файлы не найдены или пусты.\n")
    lines.append("---\n")

    lines.append(f"Всего обработано записей о перелетах: **{total_records}**.")
    lines.append(f"Найдено теневых групп (минимум {MIN_SHARED_FLIGHTS} совместных рейса): **{len(groups)}**.\n")

    if not groups:
        lines.append(
            "Подозрительных групп не обнаружено. Пассажиры, летающие вместе, обычно оформляются в одних и тех же бронях.")
    else:
        lines.append("#### Самые подозрительные группы")
        for i, (grp, grp_flights) in enumerate(groups[:3], 1):
            names = [pax_info[p]["raw_name"] for p in grp]
            names_str = ", ".join(names[:5])
            if len(names) > 5: names_str += f" и еще {len(names) - 5} чел."

            agencies = set()
            for p in grp:
                agencies |= pax_info[p]["agencies"]
            ag_str = ", ".join(agencies) if agencies else "не указаны"

            # Берем топ-3 рейса для примера
            flights_sample = ", ".join(f"{fl.split('_')[0]} ({fl.split('_')[1]})" for fl in sorted(grp_flights)[:3])

            lines.append(f"{i}. Группа из {len(grp)} человек: {names_str}.")
            lines.append(f"   - Летали вместе **{len(grp_flights)}** раз. Примеры рейсов: {flights_sample}.")
            lines.append(f"   - Оформлялись через: {ag_str}.")

        if len(groups) > 3:
            lines.append(f"\n_...и еще {len(groups) - 3} групп(ы). Полный список см. в `shadow_groups.csv`._")

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"    -> {OUT_REPORT.name} обновлён.")


# ---------- основной анализ ----------
def main():
    # Очищаем старые отчеты при каждом новом запуске
    if OUT_SPIES.exists():
        OUT_SPIES.unlink()
    if OUT_REPORT.exists():
        OUT_REPORT.unlink()

    print("=" * 60)
    print("🚀 ЗАПУСК АНАЛИЗА ТЕНЕВЫХ ГРУПП")
    print("=" * 60)

    print("[STEP 0/5] Чтение файлов...")
    files = {
        "BoardingData": TEMP / "BoardingData_parsed.csv",
        "sirena": TEMP / "sirena_parsed.csv",
        "cleaned_boarding_pass": TEMP / "cleaned_boarding_pass.csv",
    }

    all_records = []
    files_stats = []

    if files["BoardingData"].exists():
        rows = read_boarding_data(files["BoardingData"])
        all_records.extend(rows)
        files_stats.append(("BoardingData", len(rows)))
    if files["sirena"].exists():
        rows = read_sirena(files["sirena"])
        all_records.extend(rows)
        files_stats.append(("sirena", len(rows)))
    if files["cleaned_boarding_pass"].exists():
        rows = read_cleaned_pass(files["cleaned_boarding_pass"])
        all_records.extend(rows)
        files_stats.append(("cleaned_boarding_pass", len(rows)))

    print(f"    -> Всего записей о перелетах: {len(all_records)}\n")

    if not all_records:
        print("[!] Ни один файл не прочитан.")
        return

    apply_canonical_names(all_records)
    print()

    print("[STEP 2/5] Группировка пассажиров по рейсам...")
    t0 = time.time()
    pax_flights = defaultdict(set)
    flight_passengers = defaultdict(list)
    pax_info = defaultdict(lambda: {"agencies": set(), "bookings": set(), "docs": set(), "raw_name": ""})

    for r in all_records:
        if r["flight"] and r["date"]:
            fid = f"{r['flight']}_{r['date']}"
            pax_flights[r["name"]].add(fid)
            flight_passengers[fid].append(r["name"])

        if r["agency"]: pax_info[r["name"]]["agencies"].add(r["agency"])
        if r["booking"]: pax_info[r["name"]]["bookings"].add(r["booking"])
        pax_info[r["name"]]["docs"] |= r["docs"]
        if not pax_info[r["name"]]["raw_name"]:
            pax_info[r["name"]]["raw_name"] = r["name"]

    print(f"    -> Уникальных рейсов (с датами): {len(flight_passengers)}")
    print(f"    -> Завершено за {time.time() - t0:.2f} сек\n")

    print("[STEP 3/5] Поиск пар, летавших вместе (может занять время)...")
    t0 = time.time()
    pair_counts = defaultdict(int)
    flight_count = 0
    total_flights = len(flight_passengers)

    for fid, names in flight_passengers.items():
        flight_count += 1
        if flight_count % 10000 == 0:
            print(f"    ... обработано {flight_count}/{total_flights} рейсов", end="\r", flush=True)

        unique_names = list(set(names))
        if len(unique_names) < 2:
            continue

        for n1, n2 in combinations(unique_names, 2):
            pair = (n1, n2) if n1 < n2 else (n2, n1)
            pair_counts[pair] += 1

    print(f"    -> Обработано {total_flights} рейсов (за {time.time() - t0:.2f} сек)")
    print(f"    -> Найдено пар, летавших вместе хотя бы раз: {len(pair_counts)}")

    valid_pairs = {pair: count for pair, count in pair_counts.items() if count >= MIN_SHARED_FLIGHTS}
    print(f"    -> Пар, летавших вместе >= {MIN_SHARED_FLIGHTS} раз: {len(valid_pairs)}\n")

    if not valid_pairs:
        print("[!] Теневых групп не найдено. Завершаем работу.")
        update_spies_md([], pax_info, len(all_records))
        write_report_md([], pax_info, len(all_records), files_stats)
        return

    print("[STEP 4/5] Формирование теневых групп...")
    t0 = time.time()

    neighbors = defaultdict(set)
    for p1, p2 in valid_pairs:
        neighbors[p1].add(p2)
        neighbors[p2].add(p1)

    sorted_pairs = sorted(valid_pairs.items(), key=lambda x: (-x[1], x[0]))

    grouped_people = set()
    groups = []

    for idx, ((p1, p2), count) in enumerate(sorted_pairs):
        if idx % 500 == 0:
            print(f"    ... проверено пар: {idx}/{len(sorted_pairs)}, найдено групп: {len(groups)}", end="\r",
                  flush=True)

        if p1 in grouped_people or p2 in grouped_people:
            continue

        group = {p1, p2}
        shared_flights = pax_flights[p1] & pax_flights[p2]

        candidates = neighbors[p1] | neighbors[p2]

        for cand in candidates:
            if cand in grouped_people or cand in group:
                continue

            new_shared = shared_flights & pax_flights[cand]
            if len(new_shared) >= MIN_SHARED_FLIGHTS:
                group.add(cand)
                shared_flights = new_shared

        groups.append((group, shared_flights))
        grouped_people.update(group)

    print(f"    -> Сформировано групп: {len(groups)} (за {time.time() - t0:.2f} сек)\n")
    groups.sort(key=lambda x: len(x[1]), reverse=True)

    print("[STEP 5/5] Сохранение результатов...")
    OUT_SHADOW.parent.mkdir(parents=True, exist_ok=True)
    with OUT_SHADOW.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(
            ["Group_ID", "Size", "Shared_Flights_Count", "Passengers", "Agencies", "Bookings", "Exact_Shared_Flights",
             "Docs"])

        for i, (grp, grp_flights) in enumerate(groups, 1):
            grp_agencies = set()
            grp_bookings = set()
            grp_docs = set()
            pax_names = []

            for p in grp:
                grp_agencies |= pax_info[p]["agencies"]
                grp_bookings |= pax_info[p]["bookings"]
                grp_docs |= pax_info[p]["docs"]
                pax_names.append(pax_info[p]["raw_name"])

            flights_str = " | ".join(f"{fl.split('_')[0]} ({fl.split('_')[1]})" for fl in sorted(grp_flights))

            w.writerow([
                f"SG_{i}",
                len(grp),
                len(grp_flights),
                " | ".join(pax_names),
                " | ".join(sorted(grp_agencies)) or "N/A",
                " | ".join(sorted(grp_bookings)),
                flights_str,
                " | ".join(sorted(grp_docs))
            ])

    print(f"    -> {OUT_SHADOW.name} сохранен ({len(groups)} групп).")

    update_spies_md(groups, pax_info, len(all_records))
    write_report_md(groups, pax_info, len(all_records), files_stats)

    print("=" * 60)
    print("✅ ГОТОВО!")


if __name__ == "__main__":
    main()