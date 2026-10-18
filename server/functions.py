from pathlib import Path
import pandas as pd

REPORT_PATH = Path("report.md")
TARGET_DIR = Path("../resources/processed/temp")

FILES_TO_PROCESS = [
    # "BoardingData.csv",
    "Skyteam_Timetable.csv",
    "cleaned_boarding_pass.csv",
    "json_parsed.csv",
    "sirena_parsed.csv",
    "xml_parsed.csv",
    "yaml_parsed.csv"
]

def count_rows_in_files() -> str:
    try:
        results = []
        total_rows = 0

        for filename in FILES_TO_PROCESS:
            file_path = TARGET_DIR / filename
            if file_path.exists():
                df = pd.read_csv(file_path, sep='|', low_memory=False)
                row_count = len(df)
                total_rows += row_count
                results.append((filename, row_count))
            else:
                results.append((filename, "Файл не найден"))

        md_content = "# Отчет по количеству строк в файлах\n\n"
        md_content += "| Имя файла | Количество строк |\n"
        md_content += "| :--- | ---: |\n"
        
        for filename, count in results:
            count_str = f"{count:,}" if isinstance(count, int) else count
            md_content += f"| `{filename}` | {count_str} |\n"
            
        md_content += f"\n**Итого общее количество строк:** `{total_rows:,}`\n"

        REPORT_PATH.write_text(md_content, encoding="utf-8")
        return "0"
    except Exception as e:
        print(f"Ошибка при обработке файлов: {e}")
        return "1"
    