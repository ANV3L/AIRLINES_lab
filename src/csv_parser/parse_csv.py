import csv
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SRC = BASE / "resources" / "raw" / "BoardingData.csv"
DST = BASE / "resources" / "processed" / "temp" / "BoardingData_parsed.csv"



def main():
    with SRC.open(newline="", encoding="utf-8-sig") as fin:
        reader = csv.reader(fin, delimiter=";")
        rows = list(reader)

    with DST.open("w", newline="", encoding="utf-8") as fout:
        writer = csv.writer(fout, delimiter="|")
        writer.writerows(rows)

    print(f"Прочитано строк: {len(rows)}")
    print(f"Записано в: {DST}")


if __name__ == "__main__":
    main()