# scripts/scan_passport_columns.py
import csv
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
TEMP = BASE / "resources" / "processed" / "temp"

# грубый признак: 4 цифры + пробел + 6 цифр, или 10 цифр подряд
PASSPORT_HINT = re.compile(r"^\d{4}\s?\d{6}$")

for path in sorted(TEMP.glob("*.csv")):
    print(f"\n=== {path.name} ===")
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="|")
        header = reader.fieldnames or []
        rows = list(reader)

    # для каждой колонки — сколько значений похоже на паспорт
    for col in header:
        hits = 0
        sample = None
        for row in rows:
            v = (row.get(col) or "").strip()
            if PASSPORT_HINT.match(v):
                hits += 1
                if sample is None:
                    sample = v
        if hits:
            print(f"  {col:<30} hits={hits:<6} example={sample!r}")
