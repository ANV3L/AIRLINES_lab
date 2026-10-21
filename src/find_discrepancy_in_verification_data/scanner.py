"""
scanner.py — поиск несоответствий между GROUP_1 и GROUP_2.
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

# ---------- пути ----------
BASE = Path(__file__).resolve().parents[2]
TEMP = BASE / "resources" / "processed"
OUT_DISCREPANCY = BASE / "resources" / "processed" / "discrepancy.csv"
OUT_SPIES = Path(__file__).resolve().parent / "SPIES.md"
OUT_REPORT = Path(__file__).resolve().parent / "report.md"

# ---------- конфиг ----------
GROUP_1 = {"BoardingData", "sirena", "cleaned_boarding_pass"}
GROUP_2 = {"xml", "yaml"}
MASS_ABSENCE_THRESHOLD = 0.5
EMPTY_VALUES = {"", "NOT PRESENTED", "N/A", "NONE", "-"}
DELIMS = ["|", ";", ",", "\t"]

FILES = [
    {
        "name": "BoardingData", "path": TEMP / "BoardingData.csv", "delim": "|",
        "name_format": "parts", "surname": "PassengerLastName", "first": "PassengerFirstName",
        "patronymic": "PassengerSecondName", "birth": "PassengerBirthDate", "birth_fmt": "MDY",
        "doc": "PassengerDocument", "bonus": None, "ticket": "TicketNumber",
    },
    {
        "name": "sirena", "path": TEMP / "sirena_parsed.csv", "delim": "|",
        "name_format": "combined", "name_col": "PaxName", "name_order": "surname_first",
        "birth": "PaxBirthDate", "birth_fmt": "YMD",
        "doc": "TravelDoc", "bonus": None, "ticket": "e-Ticket",
    },
    {
        "name": "cleaned_boarding_pass", "path": TEMP / "cleaned_boarding_pass.csv", "delim": "|",
        "name_format": "parts", "surname": "Фамилия", "first": "Имя", "patronymic": "Отчество",
        "birth": None, "birth_fmt": "YMD",
        "doc": None, "bonus": "Бонусная_карта", "ticket": "Номер_эл_билета",
    },
    {
        "name": "xml", "path": TEMP / "xml_parsed.csv", "delim": "|",
        "name_format": "parts", "surname": "LastName", "first": "FirstName", "patronymic": None,
        "birth": None, "birth_fmt": "YMD",
        "doc": None, "bonus": "CardNumber", "ticket": None,
    },
    {
        "name": "yaml", "path": TEMP / "yaml_parsed.csv", "delim": "|",
        "name_format": None, "surname": None, "first": None, "patronymic": None,
        "birth": None, "birth_fmt": "YMD", "doc": None, "bonus": None, "ticket": None,
    },
]

# ---------- нормализация ----------
_APOS_RE = re.compile(r"['\u2018\u2019\u0060\u00B4]")


def normalize(v: str) -> str:
    return re.sub(r"\s+", " ", (v or "").strip().upper())


def norm_name(s: str) -> str:
    s = normalize(s)
    s = _APOS_RE.sub("", s)
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
    return s.strip()


def patronymic_compatible(a: str, b: str) -> bool:
    a = norm_name(a) if a else ""
    b = norm_name(b) if b else ""
    if not a or not b:
        return True
    a_init = len(a) == 1
    b_init = len(b) == 1
    if a_init and b_init:
        return a == b
    if a_init:
        return b.startswith(a)
    if b_init:
        return a.startswith(b)
    return a == b


def has_patronymic_conflict(pats):
    pats = [p for p in pats if p]
    for i, a in enumerate(pats):
        for b in pats[i + 1:]:
            if not patronymic_compatible(a, b):
                return True
    return False


# ---------- парсинг ----------
def parse_combined_name(raw: str, order: str = "surname_first"):
    s = normalize(raw)
    parts = [p for p in re.split(r"[\/\s]+", s) if p]
    if not parts:
        return "", "", "", ""
    if order == "first_surname":
        first, surname = parts[0], parts[1] if len(parts) > 1 else ""
        patronymic = parts[2] if len(parts) > 2 else ""
    else:
        surname, first = parts[0], parts[1] if len(parts) > 1 else ""
        patronymic = parts[2] if len(parts) > 2 else ""
    fio = " ".join(p for p in (surname, first, patronymic) if p)
    return surname, first, patronymic, fio


def parse_name_row(row, cfg):
    fmt = cfg.get("name_format")
    if fmt == "parts":
        surname = normalize(row.get(cfg.get("surname") or "", ""))
        first = normalize(row.get(cfg.get("first") or "", ""))
        patronymic = normalize(row.get(cfg.get("patronymic") or "", ""))
        fio = " ".join(p for p in (surname, first, patronymic) if p)
    elif fmt == "combined":
        raw = row.get(cfg.get("name_col") or "", "")
        surname, first, patronymic, fio = parse_combined_name(raw, cfg.get("name_order", "surname_first"))
    else:
        surname = first = patronymic = fio = ""
    return surname, first, patronymic, fio


def parse_birth(raw, fmt):
    s = (raw or "").strip()
    if not s:
        return None
    try:
        if fmt == "MDY":
            mm, dd, yyyy = re.split(r"[/\-.]", s)
        elif fmt == "DMY":
            dd, mm, yyyy = re.split(r"[/\-.]", s)
        else:
            yyyy, mm, dd = re.split(r"[/\-.]", s)
        return f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"
    except ValueError:
        return None


def sniff_delimiter(p: Path) -> str:
    with p.open(newline="", encoding="utf-8-sig") as f:
        first = f.readline().rstrip("\n")
    return max(DELIMS, key=lambda d: first.count(d))


def read_file(cfg):
    p: Path = cfg["path"]
    if not p.exists():
        print(f"[warn] нет файла: {p}")
        return []
    delim = cfg.get("delim") or sniff_delimiter(p)
    out = []
    with p.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delim)
        for row in reader:
            surname, first, patronymic, fio = parse_name_row(row, cfg)
            birth = parse_birth(row.get(cfg["birth"], "") if cfg.get("birth") else "", cfg.get("birth_fmt", "YMD"))
            doc = clean(row.get(cfg["doc"], "")) if cfg.get("doc") else ""
            bonus = clean(row.get(cfg["bonus"], "")) if cfg.get("bonus") else ""
            ticket = clean(row.get(cfg["ticket"], "")) if cfg.get("ticket") else ""

            if doc in EMPTY_VALUES: doc = ""
            if bonus in EMPTY_VALUES: bonus = ""
            if ticket in EMPTY_VALUES: ticket = ""

            out.append({
                "source": cfg["name"], "surname_raw": surname, "first_raw": first, "patronymic_raw": patronymic,
                "surname_norm": norm_name(surname), "first_norm": norm_name(first),
                "patronymic_norm": norm_name(patronymic),
                "fio": fio, "birth": birth, "doc": doc, "bonus": bonus, "ticket": ticket,
            })
    return out


# ---------- сверка ----------
def check_discrepancies(all_rows):
    g1 = defaultdict(lambda: {
        "fio": "", "fio_set": set(), "dob_set": set(),
        "docs": set(), "bonus": set(), "tickets": set(), "sources": set(),
        "pat_ids": defaultdict(lambda: {"docs": set(), "bonus": set(), "tickets": set()})
    })
    g2 = defaultdict(lambda: {
        "fio": "", "fio_set": set(), "bonus": set(), "sources": set(),
        "pat_ids": defaultdict(lambda: {"bonus": set()})
    })

    for r in all_rows:
        if not r["surname_norm"] or not r["first_norm"]:
            continue
        key = (r["surname_norm"], r["first_norm"])
        pat = r["patronymic_norm"]

        if r["source"] in GROUP_1:
            p = g1[key]
            if r["fio"]:
                p["fio_set"].add(r["fio"])
                if len(r["fio"]) > len(p["fio"]): p["fio"] = r["fio"]
            if r["birth"]: p["dob_set"].add(r["birth"])
            if r["doc"]: p["docs"].add(r["doc"])
            if r["bonus"]: p["bonus"].add(r["bonus"])
            if r["ticket"]: p["tickets"].add(r["ticket"])
            p["sources"].add(r["source"])

            if pat:
                if r["doc"]: p["pat_ids"][pat]["docs"].add(r["doc"])
                if r["bonus"]: p["pat_ids"][pat]["bonus"].add(r["bonus"])
                if r["ticket"]: p["pat_ids"][pat]["tickets"].add(r["ticket"])

        elif r["source"] in GROUP_2:
            p = g2[key]
            if r["fio"]:
                p["fio_set"].add(r["fio"])
                if len(r["fio"]) > len(p["fio"]): p["fio"] = r["fio"]
            if r["bonus"]: p["bonus"].add(r["bonus"])
            p["sources"].add(r["source"])
            if pat and r["bonus"]: p["pat_ids"][pat]["bonus"].add(r["bonus"])

    records = []

    # 1) BONUS_CARD_SHARED
    bonus_to_names = defaultdict(set)
    for nk, p in g1.items():
        for bc in p["bonus"]: bonus_to_names[bc].add(nk)
    for nk, p in g2.items():
        for bc in p["bonus"]: bonus_to_names[bc].add(nk)

    for bc, names in bonus_to_names.items():
        if len(names) <= 1: continue
        g1_names = sorted(nk for nk in names if nk in g1)
        g2_names = sorted(nk for nk in names if nk in g2)
        fio_parts = [(g1.get(nk) or g2.get(nk))["fio"] or " ".join(nk) for nk in sorted(names)]

        records.append({
            "Type": "BONUS_CARD_SHARED", "FIO": " | ".join(fio_parts),
            "BirthDate": "|".join(sorted({d for nk in g1_names for d in g1[nk]["dob_set"]})),
            "Patronymic_G1": "|".join(sorted({x for nk in g1_names for x in g1[nk]["pat_ids"] if x})),
            "Patronymic_G2": "|".join(sorted({x for nk in g2_names for x in g2[nk]["pat_ids"] if x})),
            "Bonus_G1": bc if g1_names else "", "Bonus_G2": bc if g2_names else "",
            "Docs_G1": "|".join(sorted({d for nk in g1_names for d in g1[nk]["docs"]})), "Docs_G2": "",
            "Tickets_G1": "|".join(sorted({t for nk in g1_names for t in g1[nk]["tickets"]})), "Tickets_G2": "",
            "Sources_G1": "|".join(sorted({s for nk in g1_names for s in g1[nk]["sources"]})),
            "Sources_G2": "|".join(sorted({s for nk in g2_names for s in g2[nk]["sources"]})),
            "Detail": f"bonus card {bc} used by {len(names)} distinct names",
        })

    # 2) per-name checks
    all_names = set(g1) | set(g2)
    for nk in sorted(all_names):
        p1, p2 = g1.get(nk), g2.get(nk)
        fio_display = (p1 and p1["fio"]) or (p2 and p2["fio"]) or " ".join(nk)

        def base_record(type_name, detail):
            return {
                "Type": type_name, "FIO": fio_display,
                "BirthDate": "|".join(sorted(p1["dob_set"])) if p1 else "",
                "Patronymic_G1": "|".join(sorted(x for x in (p1["pat_ids"] if p1 else {}) if x)),
                "Patronymic_G2": "|".join(sorted(x for x in (p2["pat_ids"] if p2 else {}) if x)),
                "Bonus_G1": "|".join(sorted(p1["bonus"])) if p1 else "",
                "Bonus_G2": "|".join(sorted(p2["bonus"])) if p2 else "",
                "Docs_G1": "|".join(sorted(p1["docs"])) if p1 else "", "Docs_G2": "",
                "Tickets_G1": "|".join(sorted(p1["tickets"])) if p1 else "", "Tickets_G2": "",
                "Sources_G1": "|".join(sorted(p1["sources"])) if p1 else "",
                "Sources_G2": "|".join(sorted(p2["sources"])) if p2 else "",
                "Detail": detail,
            }

        # 2.1 Проверка конфликтов отчеств (внутри группы)
        def check_real_conflict(p, group_name):
            pats = [x for x in p["pat_ids"] if x]
            if len(pats) < 2 or not has_patronymic_conflict(pats): return

            has_shared_id = False
            for i, pat_a in enumerate(pats):
                for pat_b in pats[i + 1:]:
                    if not patronymic_compatible(pat_a, pat_b):
                        for id_type in ["docs", "bonus", "tickets"]:
                            if p["pat_ids"][pat_a][id_type] & p["pat_ids"][pat_b][id_type]:
                                has_shared_id = True
                                break

            if has_shared_id:
                records.append(base_record(
                    f"PATRONYMIC_CONFLICT_{group_name}",
                    f"same person has incompatible patronymics sharing same tickets/docs: {sorted(pats)}"
                ))
            else:
                records.append(base_record(
                    f"POSSIBLE_HOMONYM_{group_name}",
                    f"multiple people with same name, different patronymics (no shared IDs): {sorted(pats)}"
                ))

        if p1: check_real_conflict(p1, "G1")
        if p2: check_real_conflict(p2, "G2")

        # 2.2 POSSIBLE_HOMONYM_G1 (по датам рождения)
        if p1 and len(p1["dob_set"]) > 1:
            records.append(base_record("POSSIBLE_HOMONYM_G1", f"multiple DOBs: {sorted(p1['dob_set'])}"))

        if p1 and p2:
            # 2.3 PATRONYMIC_MISMATCH cross-group
            pats1 = [x for x in p1["pat_ids"] if x]
            pats2 = [x for x in p2["pat_ids"] if x]
            if pats1 and pats2 and not any(patronymic_compatible(a, b) for a in pats1 for b in pats2):
                records.append(base_record("PATRONYMIC_MISMATCH",
                                           f"patronymics incompatible: G1={sorted(pats1)}, G2={sorted(pats2)}"))

            # 2.4 XML_NAME_AMBIGUOUS
            if len(p1["dob_set"]) > 1:
                records.append(base_record("XML_NAME_AMBIGUOUS", f"xml matches {len(p1['dob_set'])} DOBs in GROUP_1"))
                continue

            # 2.5 BONUS_CARD_MISMATCH
            if p1["bonus"] and p2["bonus"] and not (p1["bonus"] & p2["bonus"]):
                if pats1 and pats2 and any(patronymic_compatible(a, b) for a in pats1 for b in pats2):
                    records.append(base_record("BONUS_CARD_MISMATCH",
                                               f"bonus differs: G1={sorted(p1['bonus'])}, G2={sorted(p2['bonus'])}"))

    # 3) missing
    g1_only = [nk for nk in g1 if nk not in g2]
    g2_only = [nk for nk in g2 if nk not in g1]
    mass_g1_only = (len(g1_only) / len(g1) > MASS_ABSENCE_THRESHOLD) if g1 else False
    mass_g2_only = (len(g2_only) / len(g2) > MASS_ABSENCE_THRESHOLD) if g2 else False

    def missing_record(type_name, p, group):
        return {
            "Type": type_name, "FIO": p["fio"] or "",
            "BirthDate": "|".join(sorted(p["dob_set"])) if "dob_set" in p else "",
            "Patronymic_G1": "|".join(sorted(x for x in p["pat_ids"] if x)) if group == "G1" else "",
            "Patronymic_G2": "|".join(sorted(x for x in p["pat_ids"] if x)) if group == "G2" else "",
            "Bonus_G1": "|".join(sorted(p["bonus"])) if group == "G1" else "",
            "Bonus_G2": "|".join(sorted(p["bonus"])) if group == "G2" else "",
            "Docs_G1": "|".join(sorted(p["docs"])) if group == "G1" else "", "Docs_G2": "",
            "Tickets_G1": "|".join(sorted(p["tickets"])) if group == "G1" else "", "Tickets_G2": "",
            "Sources_G1": "|".join(sorted(p["sources"])) if group == "G1" else "",
            "Sources_G2": "|".join(sorted(p["sources"])) if group == "G2" else "",
            "Detail": "in GROUP_1 but not in GROUP_2" if group == "G1" else "in GROUP_2 but not in GROUP_1",
        }

    if not mass_g1_only:
        for nk in g1_only: records.append(missing_record("MISSING_IN_G2", g1[nk], "G1"))
    if not mass_g2_only:
        for nk in g2_only: records.append(missing_record("MISSING_IN_G1", g2[nk], "G2"))

    order = {
        "BONUS_CARD_SHARED": 0, "PATRONYMIC_MISMATCH": 1, "PATRONYMIC_CONFLICT_G1": 2,
        "PATRONYMIC_CONFLICT_G2": 3, "BONUS_CARD_MISMATCH": 4, "XML_NAME_AMBIGUOUS": 5,
        "POSSIBLE_HOMONYM_G1": 6, "POSSIBLE_HOMONYM_G2": 7, "MISSING_IN_G1": 8, "MISSING_IN_G2": 9,
    }
    records.sort(key=lambda x: (order.get(x["Type"], 99), x["FIO"]))

    stats = {
        "g1_persons": len(g1), "g2_persons": len(g2), "g1_only": len(g1_only), "g2_only": len(g2_only),
        "mass_g1_only": mass_g1_only, "mass_g2_only": mass_g2_only, "by_type": {},
    }
    for r in records: stats["by_type"][r["Type"]] = stats["by_type"].get(r["Type"], 0) + 1
    return records, stats


# ---------- запись ----------
FIELDS = [
    "Type", "FIO", "BirthDate", "Patronymic_G1", "Patronymic_G2",
    "Bonus_G1", "Bonus_G2", "Docs_G1", "Docs_G2", "Tickets_G1", "Tickets_G2",
    "Sources_G1", "Sources_G2", "Detail",
]


def write_discrepancy(records):
    OUT_DISCREPANCY.parent.mkdir(parents=True, exist_ok=True)
    with OUT_DISCREPANCY.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, delimiter=";", fieldnames=FIELDS)
        w.writeheader()
        w.writerows(records)
    print(f"[discrepancy.csv] записей: {len(records)} -> {OUT_DISCREPANCY}")


def update_spies_md(records, stats, files_stats):
    header = "## Расхождения GROUP_1 и GROUP_2 (scanner.py)"
    lines = [header + "\n\n"]
    lines.append("### Сводка\n\n")
    lines.append("| Файл | Строк прочитано | Группа |\n|---|---|---|\n")
    for name, n in files_stats:
        grp = "GROUP_1" if name in GROUP_1 else "GROUP_2" if name in GROUP_2 else "—"
        lines.append(f"| {name} | {n} | {grp} |\n")
    lines.append("\n")
    lines.append(f"- Уникальных (surname, first) в GROUP_1: **{stats['g1_persons']}**\n")
    lines.append(f"- Уникальных (surname, first) в GROUP_2: **{stats['g2_persons']}**\n")
    lines.append(f"- Всего записей в `discrepancy.csv`: **{len(records)}**\n\n")

    suspicious_types = {
        "BONUS_CARD_SHARED", "PATRONYMIC_MISMATCH", "PATRONYMIC_CONFLICT_G1",
        "PATRONYMIC_CONFLICT_G2", "BONUS_CARD_MISMATCH", "XML_NAME_AMBIGUOUS",
    }
    suspicious = [r for r in records if r["Type"] in suspicious_types]
    homonyms = [r for r in records if r["Type"].startswith("POSSIBLE_HOMONYM")]

    lines.append("### Реальные подозрительные пассажиры\n\n")
    lines.append(f"Найдено: **{len(suspicious)}**\n\n")
    if suspicious:
        lines.append("| Тип | ФИО | ДР | Отч. G1 | Отч. G2 | Bonus G1 | Bonus G2 | Детали |\n")
        lines.append("|---|---|---|---|---|---|---|---|\n")
        for r in suspicious[:40]:
            lines.append(
                f"| {r['Type']} | {r['FIO']} | {r['BirthDate']} | {r['Patronymic_G1']} | {r['Patronymic_G2']} | {r['Bonus_G1']} | {r['Bonus_G2']} | {r['Detail']} |\n")
        if len(suspicious) > 40: lines.append(f"\n_…и ещё {len(suspicious) - 40} — см. discrepancy.csv._\n")
    else:
        lines.append("_Подозрительных пассажиров не найдено._\n\n")

    lines.append("### Однофамильцы / Тезки (POSSIBLE_HOMONYM)\n\n")
    lines.append(f"Найдено: **{len(homonyms)}** (в `discrepancy.csv` они помечены `POSSIBLE_HOMONYM_*`)\n")
    lines.append("_Это люди с одинаковыми ФИО, но разными отчествами/датами рождения. Они не считаются ошибкой._\n\n")

    lines.append("### Отсутствия\n\n")
    if stats["mass_g2_only"]:
        lines.append(
            f"- ⚠️ GROUP_1 → XML: массовое отсутствие ({stats['g1_only']}/{stats['g1_persons']}) — подавлено.\n")
    else:
        lines.append(f"- GROUP_1 → XML: **{stats['g1_only']}**\n")
    if stats["mass_g1_only"]:
        lines.append(
            f"- ⚠️ XML → GROUP_1: массовое отсутствие ({stats['g2_only']}/{stats['g2_persons']}) — подавлено.\n")
    else:
        lines.append(f"- XML → GROUP_1: **{stats['g2_only']}**\n")
    lines.append("\n")

    new_section = "".join(lines)
    text = OUT_SPIES.read_text(encoding="utf-8") if OUT_SPIES.exists() else "# SPIES — подозрительные пассажиры\n\n"
    pattern = re.compile(re.escape(header) + r".*?(?=\n## |\Z)", re.DOTALL)
    text = pattern.sub("", text).rstrip() + "\n\n"
    text += new_section
    OUT_SPIES.write_text(text, encoding="utf-8")
    print(f"[SPIES.md] обновлён: {OUT_SPIES}")


def write_report_md(records, stats, files_stats):
    """Генерирует краткий отчет (для VIEW) человеческим языком."""
    suspicious_types = {
        "BONUS_CARD_SHARED", "PATRONYMIC_MISMATCH", "PATRONYMIC_CONFLICT_G1",
        "PATRONYMIC_CONFLICT_G2", "BONUS_CARD_MISMATCH", "XML_NAME_AMBIGUOUS",
    }
    suspicious = [r for r in records if r["Type"] in suspicious_types]
    homonyms = [r for r in records if r["Type"].startswith("POSSIBLE_HOMONYM")]

    lines = []
    lines.append("### Отчет по расхождениям между GROUP_1 и GROUP_2\n")
    lines.append(
        "Проанализировал файлы билетов/броней и выгрузки лояльности. Ниже - краткая сводка по найденным нестыковкам.\n")

    # --- БЛОК: ИСПОЛЬЗОВАННЫЕ ФАЙЛЫ ---
    g1_files = [name for name, n in files_stats if n > 0 and name in GROUP_1]
    g2_files = [name for name, n in files_stats if n > 0 and name in GROUP_2]

    if g1_files or g2_files:
        lines.append(f"**Данные для анализа брались из:**")
        if g1_files:
            lines.append(f"- Группа 1 (брони/билеты): {', '.join(f'`{f}`' for f in g1_files)}")
        if g2_files:
            lines.append(f"- Группа 2 (лояльность/выгрузки): {', '.join(f'`{f}`' for f in g2_files)}")
        lines.append("")
    else:
        lines.append("**Данные для анализа:** файлы не найдены или пусты.\n")
    lines.append("---\n")

    # 1. Подозрительные пассажиры
    lines.append("#### 1. Подозрительные пассажиры")
    if suspicious:
        lines.append(
            f"Найдено **{len(suspicious)}** аномалий. Это случаи, когда у человека с одинаковым именем и отчеством в разных базах (или внутри одной) висят разные бонусные карты, либо одна карта используется разными людьми.")
        for r in suspicious[:3]:
            lines.append(f"- {r['FIO']} ({r['Type']}): {r['Detail']}.")
    else:
        lines.append("Подозрительных аномалий не найдено. Все бонусные карты и отчества бьются друг с другом.")
    lines.append("")

    # 2. Тезки / Однофамильцы
    lines.append("#### 2. Однофамильцы (тезки)")
    if homonyms:
        lines.append(
            f"Найдено **{len(homonyms)}** случаев. Это люди с одинаковыми ФИО, но разными отчествами или датами рождения. Они не считаются ошибкой, просто совпадение имен.")
        for r in homonyms[:2]:
            lines.append(f"- {r['FIO']}: {r['Detail']}.")
    else:
        lines.append("Тезок с конфликтом отчеств не обнаружено.")
    lines.append("")

    # 3. Отсутствия
    lines.append("#### 3. Отсутствие данных")
    if stats.get("mass_g2_only"):
        lines.append(
            f"- Связь **GROUP_1 -> XML** не проверялась, так как отсутствие массовое ({stats['g1_only']} из {stats['g1_persons']}). Базы не обязаны совпадать на 100%.")
    else:
        lines.append(f"- Из GROUP_1 не нашлось в XML: **{stats['g1_only']}** чел.")

    if stats.get("mass_g1_only"):
        lines.append(
            f"- Связь **XML → GROUP_1** не проверялась, так как отсутствие массовое ({stats['g2_only']} из {stats['g2_persons']}).")
    else:
        lines.append(f"- Из XML не нашлось в GROUP_1: **{stats['g2_only']}** чел.")
    lines.append("")

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report.md] обновлён: {OUT_REPORT}")


def main():
    # Очищаем старые отчеты при каждом новом запуске
    if OUT_SPIES.exists():
        OUT_SPIES.unlink()
    if OUT_REPORT.exists():
        OUT_REPORT.unlink()

    all_rows, files_stats = [], []
    for cfg in FILES:
        rows = read_file(cfg)
        print(f"[read] {cfg['name']}: {len(rows)} строк")
        files_stats.append((cfg["name"], len(rows)))
        all_rows.extend(rows)

    if not all_rows:
        print("[!] Ни один файл не прочитан.")
        return

    records, stats = check_discrepancies(all_rows)
    write_discrepancy(records)

    print(f"\n[scanner] G1={stats['g1_persons']}, G2={stats['g2_persons']}, records={len(records)}")
    for t, n in stats["by_type"].items():
        print(f"  {t}: {n}")

    update_spies_md(records, stats, files_stats)
    write_report_md(records, stats, files_stats)


if __name__ == "__main__":
    main()