# SPIES — подозрительные пассажиры

## Документы со странностями

### Сводка по файлам

| Файл | Строк прочитано ||---|---|| BoardingData | 155147 || sirena | 155757 || cleaned_boarding_pass | 615771 || xml | 436090 || yaml | 1687053 || json | 1308987 || Skyteam_Timetable | 1527641 |
Всего подозрительных записей: **150501**

### 1. Один человек — разные документы (внутри и между файлами)

Найдено записей: **0**

### 2. Нетипичный год выдачи паспорта

Правило: год выдачи ∈ {birth + 14, birth + 20, birth + 45}

Найдено записей: **150501**

| Источник | ФИО | ДР | Паспорт | Год выдачи | Ожидалось |
|---|---|---|---|---|---|
| BoardingData | RUSANOV SAVELII VIKTOROVICH | 1983-03-10 | 2879 096860 | 1979 | expected issue year in [1997, 2003, 2028] |
| BoardingData | ISAEV LEV MARKOVICH | 1975-12-13 | 1788 173211 | 1988 | expected issue year in [1989, 1995, 2020] |
| BoardingData | NIKOLSKII NIKOLAI I. | 1990-12-26 | 4396 926588 | 1996 | expected issue year in [2004, 2010, 2035] |
| BoardingData | SHILOV ANATOLII PETROVICH | 1997-05-24 | 2595 919752 | 1995 | expected issue year in [2011, 2017, 2042] |
| BoardingData | SEMENOVA MIROSLAVA VIACHESLAVOVNA | 1976-01-31 | 6775 516990 | 1975 | expected issue year in [1990, 1996, 2021] |
| BoardingData | TITOVA ZARINA E. | 2000-12-22 | 6600 251370 | 2000 | expected issue year in [2014, 2020, 2045] |
| BoardingData | ROZHKOV RAMIL E. | 1980-02-02 | 0595 142701 | 1995 | expected issue year in [1994, 2000, 2025] |
| BoardingData | KONSTANTINOVA ALBINA V. | 1997-07-04 | 0916 040520 | 2016 | expected issue year in [2011, 2017, 2042] |
| BoardingData | GRIBOVA VERA R. | 1977-10-17 | 0956 724736 | 1956 | expected issue year in [1991, 1997, 2022] |
| BoardingData | SUKHANOV DENIS GERMANOVICH | 1971-11-01 | 5057 285380 | 1957 | expected issue year in [1985, 1991, 2016] |
| BoardingData | IGNATEVA ANGELINA VLADEVNA | 1985-09-22 | 2685 903678 | 1985 | expected issue year in [1999, 2005, 2030] |
| BoardingData | GORBUNOVA KRISTINA M. | 1970-01-29 | 4552 046627 | 1952 | expected issue year in [1984, 1990, 2015] |
| BoardingData | BIRIUKOVA MADINA A. | 1993-03-03 | 9048 874077 | 1948 | expected issue year in [2007, 2013, 2038] |
| BoardingData | LAZAREV SERGEI V. | 2000-04-05 | 6948 339409 | 1948 | expected issue year in [2014, 2020, 2045] |
| BoardingData | LAPSHINA MILENA I. | 1990-03-07 | 7015 885040 | 2015 | expected issue year in [2004, 2010, 2035] |
| BoardingData | ASTAKHOVA MELANIIA S. | 1978-09-09 | 4137 469025 | 1937 | expected issue year in [1992, 1998, 2023] |
| BoardingData | NIKOLAEV IURII IAROMIROVICH | 1986-05-16 | 3521 274082 | 1921 | expected issue year in [2000, 2006, 2031] |
| BoardingData | LEBEDEVA NATALIA R. | 1995-11-03 | 0582 008845 | 1982 | expected issue year in [2009, 2015, 2040] |
| BoardingData | FOMICHEVA ALLA AMIROVNA | 1975-06-21 | 2708 394334 | 2008 | expected issue year in [1989, 1995, 2020] |
| BoardingData | OVSIANNIKOV ELISEI T. | 1980-01-29 | 6754 245225 | 1954 | expected issue year in [1994, 2000, 2025] |

_…и ещё 150481 — см. changed_documents.csv._

