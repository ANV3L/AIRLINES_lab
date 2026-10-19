# SPIES — подозрительные пассажиры

## Документы со странностями

### Сводка по файлам

| Файл | Строк прочитано |
|---|---|
| BoardingData | 155147 |
| sirena | 155757 |
| cleaned_boarding_pass | 615771 |
| xml | 436090 |
| yaml | 1687053 |
| json | 1308987 |
| Skyteam_Timetable | 1527641 |

Всего подозрительных записей: **148911**

### 1. Один человек — разные документы

Найдено: **0**

### 2. Неоднозначный год выдачи паспорта (1900/2000)

Найдено: **0**

### 3. Нетипичный год выдачи паспорта

Найдено: **148911**

| Источник | ФИО | ДР | Паспорт | Кандидаты | Детали |
|---|---|---|---|---|---|
| BoardingData | RUSANOV SAVELII VIKTOROVICH | 1983-03-10 | 2879 096860 | 1979|2079 | expected [1997, 2003, 2028]; candidates: 1979 (Δ=-4); 2079 (Δ=96) |
| BoardingData | ISAEV LEV MARKOVICH | 1975-12-13 | 1788 173211 | 1988|2088 | expected [1989, 1995, 2020]; candidates: 1988 (Δ=13); 2088 (Δ=113) |
| BoardingData | NIKOLSKII NIKOLAI I. | 1990-12-26 | 4396 926588 | 1996|2096 | expected [2004, 2010, 2035]; candidates: 1996 (Δ=6); 2096 (Δ=106) |
| BoardingData | SHILOV ANATOLII PETROVICH | 1997-05-24 | 2595 919752 | 1995|2095 | expected [2011, 2017, 2042]; candidates: 1995 (Δ=-2); 2095 (Δ=98) |
| BoardingData | SEMENOVA MIROSLAVA VIACHESLAVOVNA | 1976-01-31 | 6775 516990 | 1975|2075 | expected [1990, 1996, 2021]; candidates: 1975 (Δ=-1); 2075 (Δ=99) |
| BoardingData | TITOVA ZARINA E. | 2000-12-22 | 6600 251370 | 1900|2000 | expected [2014, 2020, 2045]; candidates: 1900 (Δ=-100); 2000 (Δ=0) |
| BoardingData | ROZHKOV RAMIL E. | 1980-02-02 | 0595 142701 | 1995|2095 | expected [1994, 2000, 2025]; candidates: 1995 (Δ=15); 2095 (Δ=115) |
| BoardingData | KONSTANTINOVA ALBINA V. | 1997-07-04 | 0916 040520 | 1916|2016 | expected [2011, 2017, 2042]; candidates: 1916 (Δ=-81); 2016 (Δ=19) |
| BoardingData | GRIBOVA VERA R. | 1977-10-17 | 0956 724736 | 1956|2056 | expected [1991, 1997, 2022]; candidates: 1956 (Δ=-21); 2056 (Δ=79) |
| BoardingData | SUKHANOV DENIS GERMANOVICH | 1971-11-01 | 5057 285380 | 1957|2057 | expected [1985, 1991, 2016]; candidates: 1957 (Δ=-14); 2057 (Δ=86) |
| BoardingData | IGNATEVA ANGELINA VLADEVNA | 1985-09-22 | 2685 903678 | 1985|2085 | expected [1999, 2005, 2030]; candidates: 1985 (Δ=0); 2085 (Δ=100) |
| BoardingData | GORBUNOVA KRISTINA M. | 1970-01-29 | 4552 046627 | 1952|2052 | expected [1984, 1990, 2015]; candidates: 1952 (Δ=-18); 2052 (Δ=82) |
| BoardingData | BIRIUKOVA MADINA A. | 1993-03-03 | 9048 874077 | 1948|2048 | expected [2007, 2013, 2038]; candidates: 1948 (Δ=-45); 2048 (Δ=55) |
| BoardingData | LAZAREV SERGEI V. | 2000-04-05 | 6948 339409 | 1948|2048 | expected [2014, 2020, 2045]; candidates: 1948 (Δ=-52); 2048 (Δ=48) |
| BoardingData | LAPSHINA MILENA I. | 1990-03-07 | 7015 885040 | 1915|2015 | expected [2004, 2010, 2035]; candidates: 1915 (Δ=-75); 2015 (Δ=25) |
| BoardingData | ASTAKHOVA MELANIIA S. | 1978-09-09 | 4137 469025 | 1937|2037 | expected [1992, 1998, 2023]; candidates: 1937 (Δ=-41); 2037 (Δ=59) |
| BoardingData | NIKOLAEV IURII IAROMIROVICH | 1986-05-16 | 3521 274082 | 1921|2021 | expected [2000, 2006, 2031]; candidates: 1921 (Δ=-65); 2021 (Δ=35) |
| BoardingData | LEBEDEVA NATALIA R. | 1995-11-03 | 0582 008845 | 1982|2082 | expected [2009, 2015, 2040]; candidates: 1982 (Δ=-13); 2082 (Δ=87) |
| BoardingData | FOMICHEVA ALLA AMIROVNA | 1975-06-21 | 2708 394334 | 1908|2008 | expected [1989, 1995, 2020]; candidates: 1908 (Δ=-67); 2008 (Δ=33) |
| BoardingData | OVSIANNIKOV ELISEI T. | 1980-01-29 | 6754 245225 | 1954|2054 | expected [1994, 2000, 2025]; candidates: 1954 (Δ=-26); 2054 (Δ=74) |

_…и ещё 148891 — см. changed_documents.csv._

### 4. Паспорт выдан раньше рождения

Найдено: **127227**

| Источник | ФИО | ДР | Паспорт | Год выдачи | Δ (лет) |
|---|---|---|---|---|---|
| BoardingData | TITOVA ZARINA E. | 2000-12-22 | 6600 251370 | 1900 | -100 |
| BoardingData | LOBANOVA ALIIA MARSELEVNA | 2000-09-30 | 8600 758850 | 1900 | -100 |
| BoardingData | DAVYDOV ARTEMII AIDAROVICH | 2000-04-02 | 0900 135827 | 1900 | -100 |
| BoardingData | OLEINIKOVA IULIANA A. | 2000-02-09 | 6100 360298 | 1900 | -100 |
| BoardingData | AFANASEV ZAKHAR EVGENEVICH | 2000-08-21 | 6500 832266 | 1900 | -100 |
| BoardingData | ARKHIPOV VLAD DENISOVICH | 2000-02-26 | 9400 476443 | 1900 | -100 |
| BoardingData | MARKIN GERMAN ARTUROVICH | 2000-11-18 | 7900 855900 | 1900 | -100 |
| BoardingData | DAVYDOVA KSENIIA R. | 2000-11-11 | 4600 957203 | 1900 | -100 |
| BoardingData | DIAKOVA VALENTINA VIACHESLAVOVNA | 2000-05-07 | 2100 279718 | 1900 | -100 |
| BoardingData | BALASHOVA ANZHELIKA G. | 2000-11-15 | 8600 620955 | 1900 | -100 |
| BoardingData | NIKONOV AMIR M. | 2000-01-09 | 8800 941716 | 1900 | -100 |
| BoardingData | EMELIANOVA NELLI STEPANOVNA | 2000-03-11 | 1200 738022 | 1900 | -100 |
| BoardingData | ARKHIPOV VLAD D. | 2000-02-26 | 9400 476443 | 1900 | -100 |
| BoardingData | MARKIN GERMAN A. | 2000-11-18 | 7900 855900 | 1900 | -100 |
| BoardingData | NIKIFOROVA SOFIA V. | 2000-07-22 | 9400 730731 | 1900 | -100 |
| BoardingData | MERKULOV TIMUR P. | 2000-02-10 | 5700 829260 | 1900 | -100 |
| BoardingData | MERKULOV TIMUR PLATONOVICH | 2000-02-10 | 5700 829260 | 1900 | -100 |
| BoardingData | BALASHOVA ANZHELIKA G. | 2000-11-15 | 8600 620955 | 1900 | -100 |
| BoardingData | FEDOROV MAKAR A. | 2000-07-27 | 4500 927813 | 1900 | -100 |
| BoardingData | MARKIN GERMAN A. | 2000-11-18 | 7900 855900 | 1900 | -100 |

_…и ещё 127207 — см. artefacts.csv._
