# SPIES — подозрительные пассажиры

## Расхождения GROUP_1 и GROUP_2 (scanner.py)

### Сводка

| Файл | Строк прочитано | Группа |
|---|---|---|
| BoardingData | 0 | GROUP_1 |
| sirena | 155757 | GROUP_1 |
| cleaned_boarding_pass | 615771 | GROUP_1 |
| xml | 436090 | GROUP_2 |
| yaml | 1687053 | GROUP_2 |

- Уникальных (surname, first) в GROUP_1: **114081**
- Уникальных (surname, first) в GROUP_2: **43116**
- Всего записей в `discrepancy.csv`: **36372**

### Реальные подозрительные пассажиры

Найдено: **1**

| Тип | ФИО | ДР | Отч. G1 | Отч. G2 | Bonus G1 | Bonus G2 | Детали |
|---|---|---|---|---|---|---|---|
| BONUS_CARD_SHARED | GOLOVINA OLESIA | MASLENNIKOV ROMAN |  |  |  | FB 139888197 | FB 139888197 | bonus card FB 139888197 used by 2 distinct names |
### Однофамильцы / Тезки (POSSIBLE_HOMONYM)

Найдено: **35944** (в `discrepancy.csv` они помечены `POSSIBLE_HOMONYM_*`)
_Это люди с одинаковыми ФИО, но разными отчествами/датами рождения. Они не считаются ошибкой._

### Отсутствия

- GROUP_1 → XML: **71392**
- ⚠️ XML → GROUP_1: массовое отсутствие (427/43116) — подавлено.

