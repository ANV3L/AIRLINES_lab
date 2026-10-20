"""
Проверка документов пассажиров и поиск шпионов.

Проверка A: один человек (ФИО + ДР) — разные документы.
Проверка B: год выдачи паспорта != birth + 14 / + 20 / + 45
             (с учётом неоднозначности 1900+YY / 2000+YY и допуска ±3 года).
Проверка D: паспорт выдан раньше года рождения (артефакт).

Результаты:
  resources/processed/changed_documents.csv
  resources/processed/artefacts.csv
  SPIES.md
  report.md (для вывода в VIEW)
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

# ---------- пути ----------

BASE = Path(__file__).resolve().parents[2]
TEMP = BASE / "resources" / "processed"

OUT_DIFF = BASE / "resources" / "processed" / "changed_documents.csv"
OUT_ARTEFACT = BASE / "resources" / "processed" / "artefacts.csv"
OUT_SPIES = Path(__file__).resolve().parent / "SPIES.md"
OUT_REPORT = Path(__file__).resolve().parent / "report.md"

# ---------- КОНФИГ ----------

FILES = [
    {
        "name": "BoardingData",
        "path": TEMP / "BoardingData.csv",
        "delim": None,
        "fio": ["PassengerLastName", "PassengerFirstName", "PassengerSecondName"],
        "birth": "PassengerBirthDate",
        "birth_fmt": "MDY",
        "passport": "PassengerDocument",
        "doc_kind": "passport",
    },
    {
        "name": "sirena",
        "path": TEMP / "sirena_parsed.csv",
        "delim": ";",
        "fio": ["PaxName"],
        "birth": "PaxBirthDate",
        "birth_fmt": "YMD",
        "passport": "TravelDoc",
        "doc_kind": "other",
    },
    {
        "name": "cleaned_boarding_pass",
        "path": TEMP / "cleaned_boarding_pass.csv",
        "delim": ";",
        "fio": ["Фамилия", "Имя", "Отчество"],
        "birth": None,
        "birth_fmt": "YMD",
        "passport": "Номер_эл_билета",
        "doc_kind": "other",
    },
    {
        "name": "xml",
        "path": TEMP / "xml_parsed.csv",
        "delim": ";",
        "fio": ["LastName", "FirstName"],
        "birth": None,
        "birth_fmt": "YMD",
        "passport": "CardNumber",
        "doc_kind": "other",
    },
    {
        "name": "yaml",
        "path": TEMP / "yaml_parsed.csv",
        "delim": ";",
        "fio": None,
        "birth": None,
        "birth_fmt": "YMD",
        "passport": None,
        "doc_kind": "other",
    },
    {
        "name": "json",
        "path": TEMP / "json_parsed.csv",
        "delim": ";",
        "fio": None,
        "birth": None,
        "birth_fmt": "YMD",
        "passport": None,
        "doc_kind": "other",
    },
    {
        "name": "Skyteam_Timetable",
        "path": TEMP / "Skyteam_Timetable.csv",
        "delim": ";",
        "fio": None,
        "birth": None,
        "birth_fmt": "YMD",
        "passport": None,
        "doc_kind": "other",
    },
]

# ---------- константы ----------

CURRENT_YEAR = 2017
VALID_ISSUE_OFFSETS = {14, 20, 45}
OFFSET_TOLERANCE = 3  # Допуск в годах (серия может отличаться от года выдачи на 1-3 года)

PASSPORT_RE = re.compile(r"^(\d{2})(\d{2})\s?(\d{6})$")
EMPTY_VALUES = {"", "NOT PRESENTED", "N/A", "NONE", "-"}
DELIMS = ["|", ";", ",", "\t"]


# ---------- утилиты ----------

def normalize(v: str) -> str:
    return re.sub(r"\s+", " ", (v or "").strip().upper())


def doc_normalize(v: str) -> str:
    """Очищает документ от N/A и лишних пробелов. Оставляет либо '1234 567890', либо '567890'."""
    s = normalize(v)
    s = re.sub(r"\s*N/?A\s*$", "", s)  # Убираем N/A в конце
    s = re.sub(r"^N/?A\s*", "", s)  # Убираем N/A в начале (на всякий случай)
    return s.strip()


def sniff_delimiter(path: Path) -> str:
    with path.open(newline="", encoding="utf-8-sig") as f:
        first = f.readline().rstrip("\n")
    return max(DELIMS, key=lambda d: first.count(d))


def build_fio(row, cols):
    if not cols:
        return ""
    parts = [normalize(row.get(c, "")) for c in cols]
    return " ".join(p for p in parts if p)


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


def birth_year(birth):
    if not birth or len(birth) < 4 or not birth[:4].isdigit():
        return None
    return int(birth[:4])


def _parse_passport_parts(doc):
    m = PASSPORT_RE.match(doc)
    if not m:
        return None
    region = int(m.group(1))
    yy = int(m.group(2))
    if region < 1 or region > 99:
        return None
    return region, yy


def candidates_issue_years(doc):
    parts = _parse_passport_parts(doc)
    if parts is None:
        return []
    _, yy = parts
    return [1900 + yy, 2000 + yy]


def is_valid_issue_year(issue_year, birth_y):
    """Проверяет, попадает ли год выдачи в окно с учетом допуска."""
    for offset in VALID_ISSUE_OFFSETS:
        expected = birth_y + offset
        if abs(issue_year - expected) <= OFFSET_TOLERANCE:
            return True
    return False


def determine_issue_year(doc, birth_y):
    cands = candidates_issue_years(doc)
    if not cands or birth_y is None:
        return {"chosen": None, "candidates": cands, "ambiguous": False, "suspicious": False, "deltas": {}}

    deltas = {y: y - birth_y for y in cands}
    ok = [y for y in cands if is_valid_issue_year(y, birth_y)]

    if len(ok) == 1:
        return {"chosen": ok[0], "candidates": cands, "ambiguous": False, "suspicious": False, "deltas": deltas}
    if len(ok) == 2:
        return {"chosen": None, "candidates": cands, "ambiguous": True, "suspicious": False, "deltas": deltas}
    return {"chosen": None, "candidates": cands, "ambiguous": False, "suspicious": True, "deltas": deltas}


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
            fio = build_fio(row, cfg.get("fio"))
            birth = parse_birth(row.get(cfg["birth"], "") if cfg.get("birth") else "", cfg.get("birth_fmt", "YMD"))
            raw_doc = row.get(cfg["passport"], "") if cfg.get("passport") else ""
            doc = doc_normalize(raw_doc)
            if doc in EMPTY_VALUES:
                doc = ""

            agency = ""
            for col in ("AgentInfo", "Agency", "Agent"):
                if col in row:
                    agency = normalize(row.get(col, ""))
                    break
            destination = ""
            for col in ("Destination", "Dest", "ArrCity"):
                if col in row:
                    destination = normalize(row.get(col, ""))
                    break

            out.append({
                "source": cfg["name"],
                "fio": fio,
                "birth": birth,
                "doc": doc,
                "doc_kind": cfg.get("doc_kind", "other"),
                "agency": agency,
                "destination": destination,
            })
    return out


# ---------- проверки ----------

def check_different_docs(all_rows):
    """Проверка A: один человек — разные документы."""
    by_person = defaultdict(set)
    row_index = {}
    for r in all_rows:
        if not r["fio"] or not r["birth"] or not r["doc"]:
            continue
        key = (r["fio"], r["birth"])
        by_person[key].add(r["doc"])
        row_index[(r["fio"], r["birth"], r["doc"])] = r

    records = []
    for (fio, birth), docs in by_person.items():
        if len(docs) <= 1:
            continue

        # Проверяем, не является ли один документ усеченной версией другого (только номер vs серия+номер)
        # Если да, группируем их как один документ.
        unique_docs = []
        for d in sorted(docs):
            is_dup = False
            for u in unique_docs:
                if d in u or u in d:  # если один является подстрокой другого
                    is_dup = True
                    break
            if not is_dup:
                unique_docs.append(d)

        if len(unique_docs) <= 1:
            continue

        for d in unique_docs:
            r = next(r for r in all_rows if r["fio"] == fio and r["birth"] == birth and r["doc"] == d)
            others = [x for x in unique_docs if x != d]
            records.append({
                "Type": "DIFFERENT_DOCS", "Source": r["source"], "FIO": fio, "BirthDate": birth,
                "Document": d, "DocKind": r["doc_kind"], "IssueYear": "", "BirthYear": birth[:4],
                "Detail": f"other docs: {'|'.join(others)}",
            })
    return records


def check_suspicious_issue(all_rows):
    """Проверка B: нетипичный год выдачи."""
    records = []
    for r in all_rows:
        if r["doc_kind"] != "passport" or not r["doc"]:
            continue
        by = birth_year(r["birth"]) if r["birth"] else None
        if by is None:
            continue

        info = determine_issue_year(r["doc"], by)
        if not info["candidates"]:
            continue

        if info["ambiguous"]:
            detail = "; ".join(f"{y} (Δ={info['deltas'][y]})" for y in info["candidates"])
            records.append({
                "Type": "AMBIGUOUS_ISSUE", "Source": r["source"], "FIO": r["fio"], "BirthDate": r["birth"],
                "Document": r["doc"], "DocKind": r["doc_kind"],
                "IssueYear": "|".join(str(y) for y in info["candidates"]), "BirthYear": by,
                "Detail": f"ambiguous candidates: {detail}",
            })
        elif info["suspicious"]:
            expected = sorted(by + off for off in VALID_ISSUE_OFFSETS)
            detail = "; ".join(f"{y} (Δ={info['deltas'][y]})" for y in info["candidates"])
            records.append({
                "Type": "SUSPICIOUS_ISSUE", "Source": r["source"], "FIO": r["fio"], "BirthDate": r["birth"],
                "Document": r["doc"], "DocKind": r["doc_kind"],
                "IssueYear": "|".join(str(y) for y in info["candidates"]), "BirthYear": by,
                "Detail": f"expected {expected} (±{OFFSET_TOLERANCE}); candidates: {detail}",
            })
    return records


def check_passport_before_birth(all_rows):
    """Проверка D: паспорт выдан раньше рождения."""
    records = []
    for r in all_rows:
        if r["doc_kind"] != "passport" or not r["doc"]:
            continue
        by = birth_year(r["birth"]) if r["birth"] else None
        if by is None:
            continue

        info = determine_issue_year(r["doc"], by)
        if not info["candidates"]:
            continue

        if info["chosen"] is not None:
            if info["chosen"] < by:
                records.append({
                    "FIO": r["fio"], "BirthDate": r["birth"], "BirthYear": by,
                    "Document": r["doc"], "IssueYear": info["chosen"],
                    "Delta": info["chosen"] - by, "Source": r["source"],
                })
        else:
            for y in info["candidates"]:
                if y < by:
                    records.append({
                        "FIO": r["fio"], "BirthDate": r["birth"], "BirthYear": by,
                        "Document": r["doc"], "IssueYear": y,
                        "Delta": y - by, "Source": r["source"],
                    })
    records.sort(key=lambda x: x["Delta"])
    return records


# ---------- запись файлов ----------

FIELDNAMES = ["Type", "Source", "FIO", "BirthDate", "Document", "DocKind", "IssueYear", "BirthYear", "Detail"]


def write_diff(records):
    OUT_DIFF.parent.mkdir(parents=True, exist_ok=True)
    with OUT_DIFF.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, delimiter=";", fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(records)
    print(f"[changed_documents.csv] записей: {len(records)} -> {OUT_DIFF}")


def write_artefacts(records):
    OUT_ARTEFACT.parent.mkdir(parents=True, exist_ok=True)
    with OUT_ARTEFACT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["FIO", "BirthDate", "BirthYear", "Document", "IssueYear", "Delta", "Source"])
        for r in records:
            w.writerow(
                [r["FIO"], r["BirthDate"], r["BirthYear"], r["Document"], r["IssueYear"], r["Delta"], r["Source"]])
    print(f"[artefacts.csv] записей: {len(records)} -> {OUT_ARTEFACT}")


def update_spies_md(records, files_stats, artefacts):
    header = "## Документы со странностями"
    diff_r = [r for r in records if r["Type"] == "DIFFERENT_DOCS"]
    ambiguous_r = [r for r in records if r["Type"] == "AMBIGUOUS_ISSUE"]
    issue_r = [r for r in records if r["Type"] == "SUSPICIOUS_ISSUE"]

    lines = [header + "\n\n"]
    lines.append("### Сводка по файлам\n\n")
    lines.append("| Файл | Строк прочитано |\n|---|---|\n")
    for name, n in files_stats:
        lines.append(f"| {name} | {n} |\n")
    lines.append(f"\nВсего подозрительных записей: **{len(records)}**\n\n")

    lines.append("### 1. Один человек — разные документы\n\n")
    lines.append(f"Найдено: **{len(diff_r)}**\n\n")
    if diff_r:
        lines.append("| Источник | Тип | ФИО | ДР | Документ | Другие |\n|---|---|---|---|---|---|\n")
        for r in diff_r[:20]:
            lines.append(
                f"| {r['Source']} | {r['DocKind']} | {r['FIO']} | {r['BirthDate']} | {r['Document']} | {r['Detail']} |\n")
        if len(diff_r) > 20: lines.append(f"\n_…и ещё {len(diff_r) - 20} — см. changed_documents.csv._\n")
        lines.append("\n")

    lines.append("### 2. Неоднозначный год выдачи паспорта (1900/2000)\n\n")
    lines.append(f"Найдено: **{len(ambiguous_r)}**\n\n")
    if ambiguous_r:
        lines.append("| Источник | ФИО | ДР | Паспорт | Кандидаты | Δ |\n|---|---|---|---|---|---|\n")
        for r in ambiguous_r[:20]:
            lines.append(
                f"| {r['Source']} | {r['FIO']} | {r['BirthDate']} | {r['Document']} | {r['IssueYear']} | {r['Detail']} |\n")
        if len(ambiguous_r) > 20: lines.append(f"\n_…и ещё {len(ambiguous_r) - 20} — см. changed_documents.csv._\n")
        lines.append("\n")

    lines.append("### 3. Нетипичный год выдачи паспорта\n\n")
    lines.append(f"Найдено: **{len(issue_r)}**\n\n")
    if issue_r:
        lines.append("| Источник | ФИО | ДР | Паспорт | Кандидаты | Детали |\n|---|---|---|---|---|---|\n")
        for r in issue_r[:20]:
            lines.append(
                f"| {r['Source']} | {r['FIO']} | {r['BirthDate']} | {r['Document']} | {r['IssueYear']} | {r['Detail']} |\n")
        if len(issue_r) > 20: lines.append(f"\n_…и ещё {len(issue_r) - 20} — см. changed_documents.csv._\n")
        lines.append("\n")

    lines.append("### 4. Паспорт выдан раньше рождения\n\n")
    lines.append(f"Найдено: **{len(artefacts)}**\n\n")
    if artefacts:
        lines.append("| Источник | ФИО | ДР | Паспорт | Год выдачи | Δ (лет) |\n|---|---|---|---|---|---|\n")
        for a in artefacts[:20]:
            lines.append(
                f"| {a['Source']} | {a['FIO']} | {a['BirthDate']} | {a['Document']} | {a['IssueYear']} | {a['Delta']} |\n")
        if len(artefacts) > 20: lines.append(f"\n_…и ещё {len(artefacts) - 20} — см. artefacts.csv._\n")
    else:
        lines.append("_Артефактов не найдено._\n")

    new_section = "".join(lines)
    text = OUT_SPIES.read_text(encoding="utf-8") if OUT_SPIES.exists() else "# SPIES — подозрительные пассажиры\n\n"
    pattern = re.compile(re.escape(header) + r".*?(?=\n## |\Z)", re.DOTALL)
    text = pattern.sub("", text).rstrip() + "\n\n" + new_section
    OUT_SPIES.write_text(text, encoding="utf-8")
    print(f"[SPIES.md] обновлён: {OUT_SPIES}")


def write_report_md(records, files_stats, artefacts):
    """Генерирует краткий отчет (для VIEW) человеческим языком."""
    diff_r = [r for r in records if r["Type"] == "DIFFERENT_DOCS"]
    ambiguous_r = [r for r in records if r["Type"] == "AMBIGUOUS_ISSUE"]
    issue_r = [r for r in records if r["Type"] == "SUSPICIOUS_ISSUE"]

    lines = []
    lines.append("### Отчет по проверке документов пассажиров\n")
    lines.append(
        "Проанализировал данные из билетов и посадочных талонов. Ниже — краткая сводка по найденным нестыковкам.\n")

    used_files = [name for name, count in files_stats if count > 0]
    if used_files:
        files_str = ", ".join(f"`{f}`" for f in used_files)
        lines.append(f"**Данные для анализа брались из:** {files_str}\n")
    else:
        lines.append("**Данные для анализа:** файлы не найдены или пусты.\n")
    lines.append("---\n")

    # 1. Разные документы
    lines.append("#### 1. Разные документы у одного человека")
    if diff_r:
        lines.append(
            f"Нашлось **{len(diff_r)}** случаев. У людей с одинаковыми ФИО и датой рождения в базе висят разные паспорта или билеты. Стоит проверить на предмет смены документа или ошибки ввода.")
        lines.append("Примеры:")
        for r in diff_r[:3]:
            lines.append(
                f"- {r['FIO']} (ДР: {r['BirthDate']}): документы `{r['Document']}` и `{r['Detail'].replace('other docs: ', '')}`.")
    else:
        lines.append("Таких людей нет. Люди с одинаковыми ФИО и ДР используют одни и те же документы.")
    lines.append("")

    # 3. Странный год выдачи
    lines.append("#### 2. Странный год выдачи паспорта")
    if issue_r:
        lines.append(
            f"Целых **{len(issue_r)}** записей. Год выдачи паспорта не бьется с возрастом пассажира (с учетом допуска ±{OFFSET_TOLERANCE} лет).")
        for r in issue_r[:3]:
            lines.append(f"- {r['FIO']} (ДР: {r['BirthDate']}): паспорт `{r['Document']}`. {r['Detail']}.")
    else:
        lines.append("Странных годов не обнаружено. Все паспорта выданы в логичном возрасте.")
    lines.append("")



    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report.md] обновлён: {OUT_REPORT}")


# ---------- main ----------

def main():
    all_rows = []
    files_stats = []
    for cfg in FILES:
        rows = read_file(cfg)
        print(f"[read] {cfg['name']}: {len(rows)} строк")
        files_stats.append((cfg["name"], len(rows)))
        all_rows.extend(rows)

    if not all_rows:
        print("[!] Ни один файл не прочитан.")
        return

    records = []
    records.extend(check_different_docs(all_rows))
    records.extend(check_suspicious_issue(all_rows))
    write_diff(records)

    artefacts = check_passport_before_birth(all_rows)
    write_artefacts(artefacts)

    # Отчеты
    update_spies_md(records, files_stats, artefacts)
    write_report_md(records, files_stats, artefacts)


if __name__ == "__main__":
    main()