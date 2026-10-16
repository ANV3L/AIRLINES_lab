import csv
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
INPUT      = BASE / "resources" / "raw"       / "BoardingData.csv"
OUT_BAD    = BASE / "resources" / "processed" / "bad_document.csv"
OUT_SPIES  = BASE / "src"       / "spies_finder_in_BoardingData_csv" / "SPIES.md"

EMPTY_DOC_VALUES = {"", "NOT PRESENTED", "N/A", "NONE", "-"}


def normalize(v: str) -> str:
    return (v or "").strip().upper()


def strip_dots(s: str) -> str:
    return s.replace(".", "").replace(" ", "").strip()


def secondname_match(a: str, b: str) -> bool:
    """
    A. == ANATOLYEVICH ?      → True
    V. == VSEVOLODOVICH ?     → True
    A. == VSEVOLODOVICH ?     → False
    IVANOVICH == PETROVICH ?  → False

    --- случаи с пустым отчеством ---
    "" == IVANOVICH ?         → True   # пустое = «неизвестно», не считаем различием
    IVANOVICH == "" ?         → True   # (симметрично)
    "" == "" ?                → True   # у обоих нет отчества — тоже считаем совпадением
    """
    if a == b:
        return True
    a2 = strip_dots(a)
    b2 = strip_dots(b)

    # пустое = «неизвестно» — не считаем различием
    if not a2 or not b2:
        return True

    # оба инициалы — сравниваем по букве
    if len(a2) == 1 and len(b2) == 1:
        return a2 == b2

    # один — инициал, другой полный: инициал должен быть префиксом
    if len(a2) == 1:
        return b2.startswith(a2)
    if len(b2) == 1:
        return a2.startswith(b2)

    return False


def identity_match(e1: dict, e2: dict) -> bool:
    """Один и тот же человек?"""
    if e1["first"] != e2["first"]:  return False
    if e1["last"]  != e2["last"]:   return False
    if e1["sex"]   != e2["sex"]:    return False
    if e1["birth"] != e2["birth"]:  return False
    return secondname_match(e1["second"], e2["second"])


def make_identity(row: dict) -> dict:
    return {
        "first":  normalize(row.get("PassengerFirstName",  "")),
        "second": normalize(row.get("PassengerSecondName", "")),
        "last":   normalize(row.get("PassengerLastName",   "")),
        "sex":    normalize(row.get("PassengerSex",        "")),
        "birth":  normalize(row.get("PassengerBirthDate",  "")),
    }


def fio(identity: dict) -> str:
    parts = [identity["last"], identity["first"], identity["second"]]
    return " ".join(p for p in parts if p).strip()


def cluster_entries(entries):
    """
    entries: list[(identity, lineno)]
    Возвращает список кластеров: [ [entry, ...], [entry, ...], ... ]
    """
    clusters = []   # каждая — список (identity, lineno)

    for entry in entries:
        ident = entry[0]
        placed = False

        for cluster in clusters:
            rep = cluster[0][0]    # представитель кластера
            if identity_match(rep, ident):
                cluster.append(entry)
                placed = True
                break

        if not placed:
            clusters.append([entry])

    return clusters


def main():
    by_doc = defaultdict(list)

    with INPUT.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for lineno, row in enumerate(reader, start=2):
            doc = normalize(row.get("PassengerDocument", ""))
            if doc in EMPTY_DOC_VALUES:
                continue
            ident = make_identity(row)
            by_doc[doc].append((ident, lineno))

    # ---- ищем документы, у которых получилось >1 кластера ----
    spies = []   # list[(doc, clusters)]
    for doc, entries in by_doc.items():
        clusters = cluster_entries(entries)
        if len(clusters) > 1:
            spies.append((doc, clusters))

    # ---- bad_document.csv ----
    OUT_BAD.parent.mkdir(parents=True, exist_ok=True)
    with OUT_BAD.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "PassengerDocument",
            "VariantsCount",
            "TotalRows",
            "FirstVariant",
            "SecondVariant",
        ])
        for doc, clusters in spies:
            def variant_str(cluster):
                ident = cluster[0][0]
                return f"{fio(ident)} {ident['sex']} {ident['birth']}"

            first  = variant_str(clusters[0]) if len(clusters) > 0 else ""
            second = variant_str(clusters[1]) if len(clusters) > 1 else ""

            total_rows = sum(len(c) for c in clusters)

            writer.writerow([
                doc,
                len(clusters),
                total_rows,
                first,
                second,
            ])

    # ---- SPIES.md ----
    with OUT_SPIES.open("w", encoding="utf-8") as f:
        f.write("# SPIES — подозреваемые пассажиры\n\n")
        f.write("Источник: `BoardingData.csv`\n\n")
        f.write(f"Найдено документов, привязанных к разным людям: **{len(spies)}**\n\n")

        if not spies:
            f.write("Шпионов не обнаружено.\n")
        else:
            for doc, clusters in spies:
                f.write(f"## Документ `{doc}`\n\n")
                f.write("**Шпион найден в файле BoardingData**\n\n")
                f.write("| # строки | ФИО | Пол | Дата рождения |\n")
                f.write("|---|---|---|---|\n")

                # выводим строки всех кластеров, отсортированные по номеру строки
                rows = [e for cluster in clusters for e in cluster]
                rows.sort(key=lambda x: x[1])
                for ident, lineno in rows:
                    f.write(f"| {lineno} | {fio(ident)} | {ident['sex']} | {ident['birth']} |\n")
                f.write("\n")

    print(f"[bad_document.csv] записано строк: {len(spies)}")
    print(f"[SPIES.md] записан, документов: {len(spies)}")


if __name__ == "__main__":
    main()