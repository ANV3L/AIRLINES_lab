# 🕵️ Итоговый отчет по анализу данных

В этом отчете собраны подозрительные личности, разделенные по типу нарушений (от самых опасных к менее критичным).

### 📂 Какие файлы проверяли
- **BoardingData.csv**: проверено модулями `csv_parser`, `find_discrepancy_in_verification_data`
- **BoardingData_parsed.csv**: проверено модулями `csv_parser`, `documents_checker`, `normalization`, `shadow_groups_finder`
- **BoardingData_parsed_norm.csv**: проверено модулями `spies_finder_in_BoardingData_csv`
- **BoardingPass_parsed.csv**: проверено модулями `normalization`
- **Skyteam_Timetable.csv**: проверено модулями `documents_checker`
- **_norm.csv**: проверено модулями `normalization`
- **bad_document.csv**: проверено модулями `spies_finder_in_BoardingData_csv`
- **cleaned_boarding_pass.csv**: проверено модулями `documents_checker`, `find_discrepancy_in_verification_data`, `normalization`, `shadow_groups_finder`, `xlsx_parser`
- **json_parsed.csv**: проверено модулями `documents_checker`, `normalization`
- **sirena_parsed.csv**: проверено модулями `documents_checker`, `find_discrepancy_in_verification_data`, `normalization`, `shadow_groups_finder`, `tab_parser`
- **xml_parsed.csv**: проверено модулями `documents_checker`, `find_discrepancy_in_verification_data`, `normalization`
- **xml_parsed_norm.csv**: проверено модулями `find_ghosts`
- **yaml_parsed.csv**: проверено модулями `documents_checker`, `find_discrepancy_in_verification_data`, `normalization`
- **yaml_parsed_norm.csv**: проверено модулями `find_ghosts`

---

### 🚨 Самые явные шпионы и подозрительные личности

**1. 🚨 Жесткие нарушения (один паспорт на разных людей)**
- **GLEBOV GORDEI M.** — паспорт `8248 013778` (записей: 4)

**3. 💳 Махинации с бонусными картами**
- **GOLOVINA OLESIA | MASLENNIKOV ROMAN** — bonus card FB 139888197 used by 2 distinct names

**4. ✈️ Теневые группы (летают вместе без общих броней)**
- **Группа:** ROZANOVA ESENIA IGOREVNA, ROZANOVA ESENIA VIACHESLAVOVNA — 10 совместных рейсов.
- **Группа:** AVDIVA KIRA L, AVDIVA KIRA M — 8 совместных рейсов.
- **Группа:** KOSTIN SVIATOGOR MARSELEVICH, KOSTIN SVIATOGOR VITALEVICH — 8 совместных рейсов.
- **Группа:** KUKUSHKIN ILDAR ARSENEVICH, KUKUSHKIN ILDAR NAZAROVICH — 8 совместных рейсов.
- **Группа:** GORELOVA IANA NIKOLAEVNA, GORELOVA IANA KONSTANTINOVNA — 7 совместных рейсов.
  _...и еще 2275 случаев в этой категории._

**5. 👻 Призраки (частые перелеты без публичных профилей)**
- **ID `DT 52115273`** — 24 рейсов (из них бизнесом: 3).
- **ID `FB 364342762`** — 24 рейсов (из них бизнесом: 6).
- **ID `SU 627979589`** — 24 рейсов (из них бизнесом: 7).
- **ID `DT 866508463`** — 22 рейсов (из них бизнесом: 4).
- **ID `DT 358866441`** — 22 рейсов (из них бизнесом: 2).
  _...и еще 248 случаев в этой категории._

**6. 📅 Странности с паспортами (выдан раньше рождения / странный год)**
- **TITOVA ZARINA E.** — паспорт `6600 251370` (год выдачи: 1900, дельта: -100 лет).
- **LOBANOVA ALIIA MARSELEVNA** — паспорт `8600 758850` (год выдачи: 1900, дельта: -100 лет).
- **DAVYDOV ARTEMII AIDAROVICH** — паспорт `0900 135827` (год выдачи: 1900, дельта: -100 лет).
- **OLEINIKOVA IULIANA A.** — паспорт `6100 360298` (год выдачи: 1900, дельта: -100 лет).
- **AFANASEV ZAKHAR EVGENEVICH** — паспорт `6500 832266` (год выдачи: 1900, дельта: -100 лет).
  _...и еще 108389 случаев в этой категории._

---

### 📝 Детальные отчеты
Для более подробного изучения смотрите файлы `SPIES.md` и CSV-выгрузки в папках модулей:
- `src/csv_parser/`
- `src/documents_checker/`
- `src/find_discrepancy_in_verification_data/`
- `src/find_ghosts/`
- `src/normalization/`
- `src/shadow_groups_finder/`
- `src/spies_finder_in_BoardingData_csv/`
- `src/tab_parser/`
- `src/xlsx_parser/`