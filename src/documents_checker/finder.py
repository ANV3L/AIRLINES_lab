"""
Проверка документов пассажиров и поиск шпионов.

Проверка A: один человек (ФИО + ДР) — разные документы.
Проверка B: год выдачи паспорта != birth + 14 / + 20 / + 45
             (с учётом неоднозначности 1900+YY / 2000+YY).
Проверка D: паспорт выдан раньше года рождения (артефакт).

Результаты:
  resources/processed/changed_documents.csv
  resources/processed/artefacts.csv
  src/documents_checker/SPIES.md
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

# ---------- пути ----------

BASE = Path(__file__).resolve().parents[2]
TEMP = BASE / "resources" / "processed" / "temp"

OUT_DIFF     = BASE / "resources" / "processed" / "changed_documents.csv"
OUT_ARTEFACT = BASE / "resources" / "processed" / "artefacts.csv"
OUT_SPIES    = Path(__file__).resolve().parent / "SPIES.md"

# ---------- КОНФИГ ----------
#
# fio        — колонки для склейки ФИО (в порядке Ф, И, О)
# birth      — колонка с датой рождения
# birth_fmt  — "MDY" / "DMY" / "YMD"
# passport   — колонка с идентифицирующим документом
# doc_kind   — "passport" (можно проверять серию) или "other"
# delim      — разделитель; None → определится автоматически
#
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

PASSPORT_RE = re.compile(r"^(\d{2})(\d{2})\s?(\d{6})$")
EMPTY_VALUES = {"", "NOT PRESENTED", "N/A", "NONE", "-"}
DELIMS = ["|", ";", ",", "\t"]

# ---------- утилиты ----------

def normalize(v: str) -> str:
    return re.sub(r"\s+", " ", (v or "").strip().upper())


def doc_normalize(v: str) -> str:
    """Убирает хвост 'N/A' и лишние пробелы."""
    s = normalize(v)
    s = re.sub(r"\s*N/?A\s*$", "", s)
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
    """Возвращает (region, yy) или None, если строка не похожа на паспорт РФ."""
    m = PASSPORT_RE.match(doc)
    if not m:
        return None
    region = int(m.group(1))
    yy = int(m.group(2))
    if region < 1 or region > 99:
        return None
    return region, yy


def candidates_issue_years(doc):
    """Возвращает список возможных годов выдачи: [1900+YY, 2000+YY]."""
    parts = _parse_passport_parts(doc)
    if parts is None:
        return []
    _, yy = parts
    return [1900 + yy, 2000 + yy]


def _delta_ok(issue_year, birth_y):
    return (issue_year - birth_y) in VALID_ISSUE_OFFSETS


def determine_issue_year(doc, birth_y):
    """
    Определяет год выдачи паспорта с учётом неоднозначности 1900/2000.

    Возвращает dict:
      {
        "chosen": int | None,          # выбранный год (если однозначно)
        "candidates": [int, int],      # оба кандидата
        "ambiguous": bool,             # True, если оба кандидата дают допустимую дельту
        "suspicious": bool,            # True, если ни один кандидат не даёт допустимой дельты
        "deltas": {int: int, int: int} # год -> дельта с birth_y
      }
    """
    cands = candidates_issue_years(doc)
    if not cands or birth_y is None:
        return {
            "chosen": None,
            "candidates": cands,
            "ambiguous": False,
            "suspicious": False,
            "deltas": {},
        }

    deltas = {y: y - birth_y for y in cands}
    ok = [y for y in cands if _delta_ok(y, birth_y)]

    if len(ok) == 1:
        return {
            "chosen": ok[0],
            "candidates": cands,
            "ambiguous": False,
            "suspicious": False,
            "deltas": deltas,
        }
    if len(ok) == 2:
        return {
            "chosen": None,
            "candidates": cands,
            "ambiguous": True,
            "suspicious": False,
            "deltas": deltas,
        }
    # ни один не подходит
    return {
        "chosen": None,
        "candidates": cands,
        "ambiguous": False,
        "suspicious": True,
        "deltas": deltas,
    }


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


# ---------- проверка A: разные документы ----------

def check_different_docs(all_rows):
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


# ---------- проверка B: нетипичный год выдачи ----------

def check_suspicious_issue(all_rows):
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
            # оба кандидата дают допустимую дельту — неоднозначность
            detail = "; ".join(
                f"{y} (Δ={info['deltas'][y]})" for y in info["candidates"]
            )
            records.append({
                "Type": "AMBIGUOUS_ISSUE",
                "Source": r["source"],
                "FIO": r["fio"],
                "BirthDate": r["birth"],
                "Document": r["doc"],
                "DocKind": r["doc_kind"],
                "IssueYear": "|".join(str(y) for y in info["candidates"]),
                "BirthYear": by,
                "Detail": f"ambiguous candidates: {detail}",
            })
        elif info["suspicious"]:
            expected = sorted(by + off for off in VALID_ISSUE_OFFSETS)
            detail = "; ".join(
                f"{y} (Δ={info['deltas'][y]})" for y in info["candidates"]
            )
            records.append({
                "Type": "SUSPICIOUS_ISSUE",
                "Source": r["source"],
                "FIO": r["fio"],
                "BirthDate": r["birth"],
                "Document": r["doc"],
                "DocKind": r["doc_kind"],
                "IssueYear": "|".join(str(y) for y in info["candidates"]),
                "BirthYear": by,
                "Detail": f"expected {expected}; candidates: {detail}",
            })
        # если chosen не None — всё в порядке, пропускаем
    return records


# ---------- проверка D: паспорт выдан раньше рождения ----------

def check_passport_before_birth(all_rows):
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

        # если есть выбранный год — проверяем только его
        if info["chosen"] is not None:
            if info["chosen"] < by:
                records.append({
                    "FIO": r["fio"],
                    "BirthDate": r["birth"],
                    "BirthYear": by,
                    "Document": r["doc"],
                    "IssueYear": info["chosen"],
                    "Delta": info["chosen"] - by,
                    "Source": r["source"],
                })
        else:
            # неоднозначность или подозрительность: проверяем всех кандидатов
            for y in info["candidates"]:
                if y < by:
                    records.append({
                        "FIO": r["fio"],
                        "BirthDate": r["birth"],
                        "BirthYear": by,
                        "Document": r["doc"],
                        "IssueYear": y,
                        "Delta": y - by,
                        "Source": r["source"],
                    })
    records.sort(key=lambda x: x["Delta"])
    return records


# ---------- запись файлов ----------

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


def write_artefacts(records):
    OUT_ARTEFACT.parent.mkdir(parents=True, exist_ok=True)
    with OUT_ARTEFACT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([
            "FIO", "BirthDate", "BirthYear",
            "Document", "IssueYear", "Delta", "Source",
        ])
        for r in records:
            w.writerow([
                r["FIO"], r["BirthDate"], r["BirthYear"],
                r["Document"], r["IssueYear"], r["Delta"], r["Source"],
            ])
    print(f"[artefacts.csv] записей: {len(records)} -> {OUT_ARTEFACT}")


def update_spies_md(records, files_stats, artefacts):
    header = "## Документы со странностями"
    diff_r = [r for r in records if r["Type"] == "DIFFERENT_DOCS"]
    ambiguous_r = [r for r in records if r["Type"] == "AMBIGUOUS_ISSUE"]
    issue_r = [r for r in records if r["Type"] == "SUSPICIOUS_ISSUE"]

    lines = [header + "\n\n"]

    # сводка по файлам
    lines.append("### Сводка по файлам\n\n")
    lines.append("| Файл | Строк прочитано |\n|---|---|\n")
    for name, n in files_stats:
        lines.append(f"| {name} | {n} |\n")
    lines.append(f"\nВсего подозрительных записей: **{len(records)}**\n\n")

    # секция 1
    lines.append("### 1. Один человек — разные документы\n\n")
    lines.append(f"Найдено: **{len(diff_r)}**\n\n")
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

    # секция 2 — неоднозначные годы
    lines.append("### 2. Неоднозначный год выдачи паспорта (1900/2000)\n\n")
    lines.append("Правило: серия `XXYY` может соответствовать как `1900+YY`, так и `2000+YY`. ")
    lines.append("Если оба варианта дают допустимую дельту с годом рождения — запись попадает сюда.\n\n")
    lines.append(f"Найдено: **{len(ambiguous_r)}**\n\n")
    if ambiguous_r:
        lines.append("| Источник | ФИО | ДР | Паспорт | Кандидаты | Δ |\n")
        lines.append("|---|---|---|---|---|---|\n")
        for r in ambiguous_r[:20]:
            lines.append(
                f"| {r['Source']} | {r['FIO']} | {r['BirthDate']} "
                f"| {r['Document']} | {r['IssueYear']} | {r['Detail']} |\n"
            )
        if len(ambiguous_r) > 20:
            lines.append(f"\n_…и ещё {len(ambiguous_r) - 20} — см. changed_documents.csv._\n")
        lines.append("\n")

    # секция 3 — нетипичные годы
    lines.append("### 3. Нетипичный год выдачи паспорта\n\n")
    lines.append("Правило: год выдачи ∈ {birth + 14, birth + 20, birth + 45} ")
    lines.append("(с учётом обоих кандидатов 1900/2000).\n\n")
    lines.append(f"Найдено: **{len(issue_r)}**\n\n")
    if issue_r:
        lines.append("| Источник | ФИО | ДР | Паспорт | Кандидаты | Детали |\n")
        lines.append("|---|---|---|---|---|---|\n")
        for r in issue_r[:20]:
            lines.append(
                f"| {r['Source']} | {r['FIO']} | {r['BirthDate']} "
                f"| {r['Document']} | {r['IssueYear']} | {r['Detail']} |\n"
            )
        if len(issue_r) > 20:
            lines.append(f"\n_…и ещё {len(issue_r) - 20} — см. changed_documents.csv._\n")
        lines.append("\n")

    # секция 4 — артефакты
    lines.append("### 4. Паспорт выдан раньше рождения\n\n")
    lines.append("Физически невозможно — вероятный артефакт или подделка.\n\n")
    lines.append(f"Найдено: **{len(artefacts)}**\n\n")
    if artefacts:
        lines.append("| Источник | ФИО | ДР | Паспорт | Год выдачи | Δ (лет) |\n")
        lines.append("|---|---|---|---|---|---|\n")
        for a in artefacts[:20]:
            lines.append(
                f"| {a['Source']} | {a['FIO']} | {a['BirthDate']} "
                f"| {a['Document']} | {a['IssueYear']} | {a['Delta']} |\n"
            )
        if len(artefacts) > 20:
            lines.append(f"\n_…и ещё {len(artefacts) - 20} — см. artefacts.csv._\n")
        lines.append("\n")
    else:
        lines.append("_Артефактов не найдено._\n")

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

    # A + B -> changed_documents.csv
    records = []
    records.extend(check_different_docs(all_rows))
    records.extend(check_suspicious_issue(all_rows))
    write_diff(records)

    # D -> artefacts.csv
    artefacts = check_passport_before_birth(all_rows)
    write_artefacts(artefacts)

    # отчёт
    update_spies_md(records, files_stats, artefacts)


if __name__ == "__main__":
    main()