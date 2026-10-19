from functions import *

# В этом файле находится исключительно словарь с функциями
# Контракт: 
# В result.md записываете результаты работы
# Функция возвращает строку "0" при успешной отработке и "1" при ошибке

COMMANDS = {
    "Count rows in files": count_rows_in_files,
    "documents_checker": documents_checker,
    "find_discrepancy_in_verification_data": find_discrepancy_in_verification_data,
    "find_ghosts": find_ghosts,
    "shadow_groups_finder" : shadow_groups_finder,
    "spies_finder_in_BoardingData_csv": spies_finder_in_boarding_data_csv,
    "full_analysis": collect_all_reports,
}


