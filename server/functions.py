from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
REPORT_PATH = BASE_DIR / "report.md"

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

def overtake(fin: Path, report_path: Path):
    report_path.write_text(fin.read_text(encoding="utf-8"), encoding="utf-8")

from functools import wraps
from pathlib import Path

def call_overtake_after(fin: Path, report_path: Path):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                overtake(fin, report_path)
                return "0"
            except Exception as e:
                return "1"
        return wrapper
    return decorator

import sys
current_dir = Path(__file__).resolve().parent
target_dir = (current_dir / '../src').resolve()
root_dir = current_dir.parent

if str(target_dir) not in sys.path:
    sys.path.append(str(target_dir))

from documents_checker import finder as documents_checker__
from find_discrepancy_in_verification_data import scanner as find_discrepancy_in_verification_data__
from find_ghosts import find_ghosts as find_ghosts__
from shadow_groups_finder import checker as checker_shadow_groups__
from spies_finder_in_BoardingData_csv import finder as spies_finder_in_boarding_data_csv__
from collect_all_reports import collector as collect_all_reports__

documents_checker = call_overtake_after(target_dir / 'documents_checker/report.md', REPORT_PATH)(documents_checker__.main)
find_discrepancy_in_verification_data = call_overtake_after(target_dir / 'find_discrepancy_in_verification_data/report.md', REPORT_PATH)(find_discrepancy_in_verification_data__.main)
find_ghosts = call_overtake_after(target_dir / 'find_ghosts/report.md', REPORT_PATH)(find_ghosts__.main)
shadow_groups_finder = call_overtake_after(target_dir / 'shadow_groups_finder/report.md', REPORT_PATH)(checker_shadow_groups__.main)
spies_finder_in_boarding_data_csv = call_overtake_after(target_dir / 'spies_finder_in_BoardingData_csv/report.md', REPORT_PATH)(spies_finder_in_boarding_data_csv__.main)
collect_all_reports = call_overtake_after(root_dir / 'report.md', REPORT_PATH)(collect_all_reports__.main)
