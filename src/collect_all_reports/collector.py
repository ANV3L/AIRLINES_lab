import csv
import re
from pathlib import Path
from collections import defaultdict

# Пути
BASE = Path(__file__).resolve().parents[2]
SRC_DIR = BASE / "src"
PROCESSED_DIR = BASE / "resources" / "processed"
OUT_REPORT = BASE / "report.md"


def clean_markdown_header(text: str) -> str:
    """Понижает уровень заголовков, чтобы они не ломали структуру."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        if line.startswith('### '):
            cleaned.append('#' + line)
        elif line.startswith('#### '):
            cleaned.append('#' + line)
        else:
            cleaned.append(line)
    return '\n'.join(cleaned)


def get_files_and_modules():
    """Собирает информацию о том, какие файлы проверялись какими модулями."""
    mapping = defaultdict(set)
    modules = list(SRC_DIR.rglob("*.py"))

    for mod_path in modules:
        mod_name = mod_path.parent.name
        try:
            code = mod_path.read_text(encoding="utf-8")
            for m in re.finditer(r'PROCESSED\s*/\s*["\']([^"\']+\.csv)["\']', code):
                mapping[m.group(1)].add(mod_name)
            for m in re.finditer(r'TEMP\s*/\s*["\']([^"\']+\.csv)["\']', code):
                mapping[m.group(1)].add(mod_name)
            for m in re.finditer(r'["\']([A-Za-z_]+\.csv)["\']', code):
                fname = m.group(1)
                if "parsed" in fname or "cleaned" in fname or "Boarding" in fname or "_norm" in fname:
                    mapping[fname].add(mod_name)
        except Exception:
            pass

    return mapping


def get_grouped_suspects():
    """Читает CSV и группирует подозреваемых по категориям."""
    categories = {
        "1. 🚨 Жесткие нарушения (один паспорт на разных людей)": [],
        "2. 🎭 Подмена документов (разные паспорта у одного человека)": [],
        "3. 💳 Махинации с бонусными картами": [],
        "4. ✈️ Теневые группы (летают вместе без общих броней)": [],
        "5. 👻 Призраки (частые перелеты без публичных профилей)": [],
        "6. 📅 Странности с паспортами (выдан раньше рождения / странный год)": [],
    }

    # 1. Жесткие нарушения (bad_document.csv)
    bad_doc_path = PROCESSED_DIR / "bad_document.csv"
    if bad_doc_path.exists():
        with bad_doc_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                name = row.get("FirstVariant", "").split()[0:3]
                name = " ".join(name)
                if name:
                    categories["1. 🚨 Жесткие нарушения (один паспорт на разных людей)"].append(
                        f"**{name}** — паспорт `{row.get('PassengerDocument')}` (записей: {row.get('TotalRows')})"
                    )

    # 2. Разные документы (changed_documents.csv)
    changed_path = PROCESSED_DIR / "changed_documents.csv"
    if changed_path.exists():
        with changed_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                if row.get("Type") == "DIFFERENT_DOCS":
                    categories["2. 🎭 Подмена документов (разные паспорта у одного человека)"].append(
                        f"**{row.get('FIO')}** — ДР: {row.get('BirthDate')}. Документы: `{row.get('Document')}` и другие."
                    )

    # 3. Бонусные карты (discrepancy.csv)
    disc_path = PROCESSED_DIR / "discrepancy.csv"
    if disc_path.exists():
        with disc_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                if row.get("Type") in ("BONUS_CARD_SHARED", "BONUS_CARD_MISMATCH"):
                    categories["3. 💳 Махинации с бонусными картами"].append(
                        f"**{row.get('FIO')}** — {row.get('Detail')}"
                    )

    # 4. Теневые группы (shadow_groups.csv)
    shadow_path = PROCESSED_DIR / "shadow_groups.csv"
    if shadow_path.exists():
        with shadow_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                names = row.get("Passengers", "").split(" | ")
                names_str = ", ".join(names[:3])
                if len(names) > 3: names_str += f" и еще {len(names) - 3}"

                categories["4. ✈️ Теневые группы (летают вместе без общих броней)"].append(
                    f"**Группа:** {names_str} — {row.get('Shared_Flights_Count')} совместных рейсов."
                )

    # 5. Призраки (ghosts.csv)
    ghosts_path = BASE / "src" / "find_ghosts" / "ghosts.csv"
    if not ghosts_path.exists():
        ghosts_path = PROCESSED_DIR / "ghosts.csv"
        if not ghosts_path.exists():
            ghosts_path = BASE / "src" / "ghosts_finder" / "ghosts.csv"

    if ghosts_path.exists():
        with ghosts_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="|")
            for row in reader:
                categories["5. 👻 Призраки (частые перелеты без публичных профилей)"].append(
                    f"**ID `{row.get('PassengerID')}`** — {row.get('Total_Flights')} рейсов (из них бизнесом: {row.get('Business_Flights')})."
                )

    # 6. Артефакты / Странный год
    art_path = PROCESSED_DIR / "artefacts.csv"
    if art_path.exists():
        with art_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                categories["6. 📅 Странности с паспортами (выдан раньше рождения / странный год)"].append(
                    f"**{row.get('FIO')}** — паспорт `{row.get('Document')}` (год выдачи: {row.get('IssueYear')}, дельта: {row.get('Delta')} лет)."
                )

    return categories


def main():
    print("🔍 Сборка итогового отчета...")

    file_modules = get_files_and_modules()
    grouped_suspects = get_grouped_suspects()

    lines = []
    lines.append("# 🕵️ Итоговый отчет по анализу данных\n")
    lines.append(
        "В этом отчете собраны подозрительные личности, разделенные по типу нарушений (от самых опасных к менее критичным).\n")

    # Раздел: Какие файлы проверяли
    lines.append("### 📂 Какие файлы проверяли")
    if not file_modules:
        lines.append("_Не удалось определить список файлов._")
    else:
        for fname, mods in sorted(file_modules.items()):
            mods_str = ", ".join(f"`{m}`" for m in sorted(mods))
            lines.append(f"- **{fname}**: проверено модулями {mods_str}")
    lines.append("\n---\n")

    # Раздел: Подозреваемые по категориям
    lines.append("### 🚨 Самые явные шпионы и подозрительные личности")

    has_suspects = False
    for category, items in grouped_suspects.items():
        if items:
            has_suspects = True
            lines.append(f"\n**{category}**")
            for item in items[:5]:
                lines.append(f"- {item}")
            if len(items) > 5:
                lines.append(f"  _...и еще {len(items) - 5} случаев в этой категории._")

    if not has_suspects:
        lines.append("\nПодозрительных личностей не найдено. Все пассажиры чистые.")

    lines.append("\n---\n")

    # Раздел: Ссылки на полные отчеты
    lines.append("### 📝 Детальные отчеты")
    lines.append("Для более подробного изучения смотрите файлы `SPIES.md` и CSV-выгрузки в папках модулей:")

    unique_mods = set()
    for mods in file_modules.values():
        unique_mods.update(mods)
    for m in sorted(unique_mods):
        lines.append(f"- `src/{m}/`")

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[+] Отчет сохранен: {OUT_REPORT}")


if __name__ == "__main__":
    main()