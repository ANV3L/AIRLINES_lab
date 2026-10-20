# Отчет о подозрительных пассажирах

**Дата формирования:** 2026-10-20

## Резюме
Выявлено **253** пассажиров с аномальной активностью (частые перелеты бизнес-классом), 
отсутствующих в открытых базах данных (бонусных программ).

## Методология
1. Анализ внутренних данных авиакомпании (`yaml_parsed_norm.csv`)
2. Подсчет рейсов и бизнес-класса по каждому PassengerID
3. Критерии отбора: >= 3 рейсов, хотя бы 1 бизнес-класс (J, C, D, I, A, Z, P)
4. Исключение пассажиров, найденных во внешних источниках (`xml_parsed_norm.csv`, `FrequentFlyerForum-Profiles.json`)

## Топ-10 подозрительных пассажиров

| PassengerID   |   Total_Flights |   Business_Flights | Airlines   | Routes                                                                                                  |
|:--------------|----------------:|-------------------:|:-----------|:--------------------------------------------------------------------------------------------------------|
| DT 52115273   |              24 |                  3 | DT         | AMS, BOD, CDG, CPH, FCO, LIS, MPL, MRS, NCE, NTE, ORY, PRG, RNS, SVO, SVX, TLS, TOF                     |
| FB 364342762  |              24 |                  6 | FB         | AER, ATL, CHS, DUB, FCO, JFK, KZN, LAX, MAD, MSP, NJC, PHX, PRG, SHV, SVO, TRI                          |
| SU 627979589  |              24 |                  7 | SU         | AAQ, AMS, BCN, BIQ, BLQ, CDG, DUS, FCO, KZN, LYS, PRG, ROV, SGC, SLY, SVO, TLV, ZAG, ZRH                |
| DT 866508463  |              22 |                  4 | DT         | AEP, ATL, EZE, GIG, IGR, LAX, LEX, MAD, MIA, PUJ, SCW, SLA, SVO, TPA, UFA, USH                          |
| DT 358866441  |              22 |                  2 | DT         | AER, AMS, ATL, CLT, HAV, JFK, LGA, MAD, MEX, MHT, OKC, PHL, RDU, SVO, TPA, VLC, VNO, VOZ                |
| KE 554033144  |              22 |                  2 | KE         | AMS, AUH, BSL, FRU, KHV, KJA, KRS, LED, MRS, MXP, NGK, PRG, RIX, SVO, SYX, URC, WUH                     |
| SU 126942686  |              22 |                  6 | SU         | AHB, AMS, ASF, ATL, BEY, BNA, CAI, DMM, EBL, FRA, FSD, LCA, LGA, MKE, MSP, NBO, RUH, SVO                |
| KE 208679532  |              22 |                  2 | KE         | CAN, CDG, FCO, GVA, HAN, JFK, KHV, KIX, LAS, PKC, REA, SJC, SLC, SNA, SVO, UUS, VVO                     |
| FB 750503411  |              22 |                  5 | FB         | ABA, BLQ, CAN, CGD, CGO, CGQ, DLC, DNH, HGH, HTT, INC, PEK, PRG, PVG, REA, SAR, SVO, WUH, XIY, XMN, YIH |
| FB 142995172  |              21 |                  6 | FB         | ATL, DCA, DTW, JFK, LGA, MAD, MIA, MSN, MSY, NUX, PHL, RSW, SVO, TYS                                    |

## Рекомендации
- Проверить выявленные номера через внутренние службы безопасности
- Выявить корпоративных клиентов с режимом конфиденциальности
- Настроить мониторинг новых рейсов для данных PassengerID
