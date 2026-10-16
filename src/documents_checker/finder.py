"""
Проверка документов пассажиров по всем файлам с ФИО/ДР/документом.

Проверка A (кросс-файловая): один и тот же человек (ФИО + ДР)
                             встречается с разными документами.
Проверка B: год выдачи паспорта РФ != birth + 14 / + 20 / + 45.

Результат: resources/processed/changed_documents.csv
Отчёт:    src/documents_checker/SPIES.md
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

# ---------- пути ----------

BASE = Path(__file__).resolve().parents[2]
TEMP = BASE / "resources" / "processed" / "temp"

OUT_DIFF = BASE / "resources" / "processed" / "changed_documents.csv"
OUT_SPIES = Path(__file__).resolve().parent / "SPIES.md"   # рядом с finder.py


# ---------- КОНФИГ ----------
#
# fio        — колонки для склейки ФИО (в порядке Ф, И, О), либо одна строка
# birth      — колонка с ДР
# birth_fmt  — "MDY" / "DMY" / "YMD"
# passport   — колонка с идентифицирующим документом (паспорт/аналог)
# doc_kind   — "passport" (можно проверять год выдачи)
#              или "other" (только для сравнения)
# delim      — разделитель; None → определится автоматически
#
# Файлы, где нет ФИО/ДР/документа, всё равно оставляем в конфиге —
# если поля появятся в данных, они подхватятся без правки кода.

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
        "delim": ";",       # в processed/temp/ он обычно с ;
        "fio": ["PaxName"],
        "birth": "PaxBirthDate",
        "birth_fmt": "YMD",
        "passport": "TravelDoc",       # формат '890330 N/A' — не полноценный паспорт
        "doc_kind": "other",           # в проверку B не пойдёт
    },
    {
        "name": "cleaned_boarding_pass",
        "path": TEMP / "cleaned_boarding_pass.csv",
        "delim": ";",
        "fio": ["Фамилия", "Имя", "Отчество"],
        "birth": None,                 # нет ДР
        "birth_fmt": "YMD",
        "passport": "Номер_эл_билета", # это e-Ticket, не паспорт
        "doc_kind": "other",
    },
    {
        "name": "xml",
        "path": TEMP / "xml_parsed.csv",
        "delim": ";",
        "fio": ["LastName", "FirstName"],
        "birth": None,                 # нет ДР
        "birth_fmt": "YMD",
        "passport": "CardNumber",      # карта, не паспорт
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

CURRENT_YEAR = 2017
VALID_ISSUE_OFFSETS = {14, 20, 45}

PASSPORT_RE = re.compile(r"^(\d{2})(\d{2})\s?(\d{6})$")
EMPTY_VALUES = {"", "NOT PRESENTED", "N/A", "NONE", "-"}
DELIMS = ["|", ";", ",", "\t"]


# ---------- утилиты ----------

def normalize(v: str) -> str:
    return re.sub(r"\s+", " ", (v or "").strip().upper())


def doc_normalize(v: str) -> str:
    """Убираем хвосты вида 'N/A', схлопываем пробелы."""
    s = normalize(v)
    s = re.sub(r"\s*N/?A\s*$", "", s)
    return s.strip()


def sniff_delimiter(path: Path) -> str:
    with path.open(newline="", encoding="utf-8-sig") as f:
        first = f.readline().rstrip("\n")
    return max(DELIMS, key=lambda d: first.count(d))


def build_fio(row: dict, cols):
    if not cols:
        return ""
    parts = [normalize(row.get(c, "")) for c in cols]
    return " ".join(p for p in parts if p)


def parse_birth(raw: str, fmt: str):
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


def birth_year(birth: str):
    if not birth or len(birth) < 4 or not birth[:4].isdigit():
        return None
    return int(birth[:4])


def parse_passport_issue_year(doc: str):
    m = PASSPORT_RE.match(doc)
    if not m:
        return None
    region = int(m.group(1))
    yy = int(m.group(2))
    if region < 1 or region > 99:
        return None
    return 1900 + yy if yy >= CURRENT_YEAR % 100 else 2000 + yy


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
            birth = parse_birth(
                row.get(cfg["birth"], "") if cfg.get("birth") else "",
                cfg.get("birth_fmt", "YMD"),
            )
            raw_doc = row.get(cfg["passport"], "") if cfg.get("passport") else ""
            doc = doc_normalize(raw_doc)
            if doc in EMPTY_VALUES:
                doc = ""
            out.append({
                "source": cfg["name"],
                "fio": fio,
                "birth": birth,
                "doc": doc,
                "doc_kind": cfg.get("doc_kind", "other"),
            })
    return out


# ---------- проверки ----------

def check_different_docs(all_rows):
    """
    Одинаковые ФИО+ДР, разные документы — ВНУТРИ и МЕЖДУ файлами.
    """
    by_person = defaultdict(set)         # (fio, birth) -> {doc}
    row_index = {}                       # (fio, birth, doc) -> row

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
        sorted_docs = sorted(docs)
        for d in sorted_docs:
            r = row_index[(fio, birth, d)]
            others = [x for x in sorted_docs if x != d]
            records.append({
                "Type": "DIFFERENT_DOCS",
                "Source": r["source"],
                "FIO": fio,
                "BirthDate": birth,
                "Document": d,
                "DocKind": r["doc_kind"],
                "IssueYear": "",
                "BirthYear": birth[:4],
                "Detail": f"other docs: {'|'.join(others)}",
            })
    return records


def check_suspicious_issue(all_rows):
    """Год выдачи != birth + 14/20/45. Только для doc_kind='passport'."""
    records = []
    for r in all_rows:
        if r["doc_kind"] != "passport" or not r["doc"]:
            continue
        by = birth_year(r["birth"]) if r["birth"] else None
        if by is None:
            continue
        issue = parse_passport_issue_year(r["doc"])
        if issue is None:
            continue
        expected = sorted(by + off for off in VALID_ISSUE_OFFSETS)
        if issue in expected:
            continue
        records.append({
            "Type": "SUSPICIOUS_ISSUE",
            "Source": r["source"],
            "FIO": r["fio"],
            "BirthDate": r["birth"],
            "Document": r["doc"],
            "DocKind": r["doc_kind"],
            "IssueYear": issue,
            "BirthYear": by,
            "Detail": f"expected issue year in {expected}",
        })
    return records


# ---------- запись ----------

FIELDNAMES = [
    "Type", "Source", "FIO", "BirthDate",
    "Document", "DocKind", "IssueYear", "BirthYear", "Detail",
]


def write_diff(records):
    OUT_DIFF.parent.mkdir(parents=True, exist_ok=True)
    with OUT_DIFF.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, delimiter=";", fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(records)
    print(f"[changed_documents.csv] записей: {len(records)} -> {OUT_DIFF}")


def update_spies_md(records, files_stats):
    header = "## Документы со странностями"
    diff_r = [r for r in records if r["Type"] == "DIFFERENT_DOCS"]
    issue_r = [r for r in records if r["Type"] == "SUSPICIOUS_ISSUE"]

    lines = [header + "\n\n"]
    lines.append("### Сводка по файлам\n\n")
    lines.append("| Файл | Строк прочитано |")
    lines.append("|---|---|")
    for name, n in files_stats:
        lines.append(f"| {name} | {n} |")
    lines.append("")
    lines.append(f"\nВсего подозрительных записей: **{len(records)}**\n\n")

    lines.append("### 1. Один человек — разные документы (внутри и между файлами)\n\n")
    lines.append(f"Найдено записей: **{len(diff_r)}**\n\n")
    if diff_r:
        lines.append("| Источник | Тип | ФИО | ДР | Документ | Другие |\n")
        lines.append("|---|---|---|---|---|---|\n")
        for r in diff_r[:20]:
            lines.append(
                f"| {r['Source']} | {r['DocKind']} | {r['FIO']} | {r['BirthDate']} "
                f"| {r['Document']} | {r['Detail']} |\n"
            )
        if len(diff_r) > 20:
            lines.append(f"\n_…и ещё {len(diff_r) - 20} — см. changed_documents.csv._\n")
        lines.append("\n")

    lines.append("### 2. Нетипичный год выдачи паспорта\n\n")
    lines.append("Правило: год выдачи ∈ {birth + 14, birth + 20, birth + 45}\n\n")
    lines.append(f"Найдено записей: **{len(issue_r)}**\n\n")
    if issue_r:
        lines.append("| Источник | ФИО | ДР | Паспорт | Год выдачи | Ожидалось |\n")
        lines.append("|---|---|---|---|---|---|\n")
        for r in issue_r[:20]:
            lines.append(
                f"| {r['Source']} | {r['FIO']} | {r['BirthDate']} "
                f"| {r['Document']} | {r['IssueYear']} | {r['Detail']} |\n"
            )
        if len(issue_r) > 20:
            lines.append(f"\n_…и ещё {len(issue_r) - 20} — см. changed_documents.csv._\n")
        lines.append("\n")

    new_section = "".join(lines)

    text = OUT_SPIES.read_text(encoding="utf-8") if OUT_SPIES.exists() \
        else "# SPIES — подозрительные пассажиры\n\n"

    pattern = re.compile(re.escape(header) + r".*?(?=\n## |\Z)", re.DOTALL)
    text = pattern.sub("", text).rstrip() + "\n\n"
    text += new_section
    OUT_SPIES.write_text(text, encoding="utf-8")
    print(f"[SPIES.md] обновлён: {OUT_SPIES}")


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
    update_spies_md(records, files_stats)


if __name__ == "__main__":
    main()