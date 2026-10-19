import pandas as pd
import json
from datetime import datetime

MIN_FLIGHTS = 3
BUSINESS_CLASSES = {'J', 'C', 'D', 'I', 'A', 'Z', 'P'}

YAML_CSV = "../../resources/processed/yaml_parsed.csv"
XML_CSV = "../../resources/processed/xml_parsed.csv"
JSON_RAW = "../../resources/raw/FrequentFlyerForum-Profiles.json"
OUT_CSV = "ghosts.csv"
OUT_MD = "SPIES.md"


def main():
    df_yaml = pd.read_csv(YAML_CSV, sep='|')
    df_yaml['PassengerID'] = df_yaml['FF_Airline'].astype(str).str.strip() + " " + df_yaml['FF_Number'].astype(str).str.strip()

    stats = df_yaml.groupby('PassengerID').agg(
        Total_Flights=('Flight', 'count'),
        Business_Flights=('Class', lambda x: (x.astype(str).str.upper().isin(BUSINESS_CLASSES)).sum()),
        Airlines=('FF_Airline', lambda x: ', '.join(sorted(set(x)))),
        Routes=('From', lambda x: ', '.join(sorted(set(x))))
    ).reset_index()

    suspects = stats[
        (stats['Total_Flights'] >= MIN_FLIGHTS) & 
        (stats['Business_Flights'] >= 1)
    ].copy()
    print(f"Found {len(suspects)} active passangers in VIP-class")

    df_xml = pd.read_csv(XML_CSV, sep='|')
    xml_known = set(df_xml['CardNumber'].astype(str).str.strip().unique())
    xml_known.update(df_xml['UserId'].astype(str).str.strip().unique())

    with open(JSON_RAW, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    json_known = set()
    for profile in json_data.get("Forum Profiles", []):
        loyalty_list = profile.get("Loyality Programm", [])
        if isinstance(loyalty_list, list):
            for loyalty in loyalty_list:
                prog = loyalty.get("programm", "")
                num = loyalty.get("Number", "")
                if prog and num:
                    passenger_id = f"{prog} {num.strip()}"
                    json_known.add(passenger_id)

    ghosts = suspects[
        ~suspects['PassengerID'].isin(xml_known) & 
        ~suspects['PassengerID'].isin(json_known)
    ].copy()

    ghosts = ghosts.sort_values(by='Total_Flights', ascending=False).reset_index(drop=True)

    ghosts.to_csv(OUT_CSV, sep='|', index=False)
    print(f"\nFound {len(ghosts)} passangers without public profile. Saved into {OUT_CSV}")

    generate_report(ghosts)


def generate_report(ghosts_df):
    print("Generate report...")
    
    top_10 = ghosts_df.head(10).to_markdown(index=False)
    
    report = f"""# Отчет о подозрительных пассажирах

**Дата формирования:** {datetime.now().strftime("%Y-%m-%d")}
**Автор:** Irina Rubleva

## Резюме
Выявлено **{len(ghosts_df)}** пассажиров с аномальной активностью (частые перелеты бизнес-классом), 
отсутствующих в открытых базах данных (бонусных программ).

## Методология
1. Анализ внутренних данных авиакомпании (SkyTeam-Exchange.yaml)
2. Подсчет рейсов и бизнес-класса по каждому PassengerID
3. Критерии отбора: >= {MIN_FLIGHTS} рейсов, хотя бы 1 бизнес-класс (J, C, D, I, A, Z, P)
4. Исключение пассажиров, найденных во внешних источниках (XML, JSON)

## Топ-10 подозрительных пассажиров

{top_10}

## Рекомендации
- Проверить выявленные номера через внутренние службы безопасности
- Выявить корпоративных клиентов с режимом конфиденциальности
- Настроить мониторинг новых рейсов для данных PassengerID
"""
    
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Repord was saved into {OUT_MD}")


if __name__ == "__main__":
    try:
        import pandas
    except ImportError:
        print("Error! Load: pip install pandas tabulate")
        exit(1)
    
    main()