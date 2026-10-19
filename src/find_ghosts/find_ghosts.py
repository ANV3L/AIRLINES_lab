import pandas as pd
import json
from datetime import datetime
from pathlib import Path

MIN_FLIGHTS = 3
BUSINESS_CLASSES = {'J', 'C', 'D', 'I', 'A', 'Z', 'P'}

# ---------- пути ----------
BASE = Path(__file__).resolve().parents[2]
YAML_CSV = BASE / "resources" / "processed" / "yaml_parsed_norm.csv"
XML_CSV = BASE / "resources" / "processed" / "xml_parsed_norm.csv"
JSON_RAW = BASE / "resources" / "raw" / "FrequentFlyerForum-Profiles.json"

OUT_CSV = Path(__file__).resolve().parent / "ghosts.csv"
OUT_MD = Path(__file__).resolve().parent / "SPIES.md"
OUT_REPORT = Path(__file__).resolve().parent / "report.md"


def generate_report_md(ghosts_df):
    """Генерирует краткий отчет для VIEW человеческим языком."""
    lines = []
    lines.append("### Отчет по поиску 'призраков'\n")
    lines.append(
        "Проанализировал перелеты пассажиров бизнес-классом. Искал тех, кто много летает, но при этом не засветился ни в одной публичной базе бонусных программ.\n")

    # Блок файлов
    lines.append(
        "**Данные для анализа брались из:** `yaml_parsed_norm.csv`, `xml_parsed_norm.csv`, `FrequentFlyerForum-Profiles.json`\n")
    lines.append("---\n")

    if ghosts_df.empty:
        lines.append("«Призраков» не найдено. Все активные пассажиры бизнес-класса найдены в публичных базах.")
    else:
        lines.append(
            f"Обнаружено **{len(ghosts_df)}** пассажиров с аномальной активностью (от {MIN_FLIGHTS} рейсов, есть бизнес-класс), которых нет в открытых источниках.\n")

        lines.append("#### Топ-3 самых активных «призрака»")
        top_3 = ghosts_df.head(3)

        for i, row in top_3.iterrows():
            lines.append(
                f"{i + 1}. ID `{row['PassengerID']}` — **{row['Total_Flights']}** рейсов (из них бизнесом: {row['Business_Flights']}).")
            lines.append(f"   - Авиакомпании: {row['Airlines']}")
            lines.append(f"   - Маршруты: {row['Routes'][:100]}{'...' if len(str(row['Routes'])) > 100 else ''}")

        if len(ghosts_df) > 3:
            lines.append(f"\n_...и еще {len(ghosts_df) - 3} человек. Полный список в `ghosts.csv` и `SPIES.md`._")

    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report.md] обновлён.")


def main():
    # Очищаем старые отчеты при каждом новом запуске
    if OUT_MD.exists(): OUT_MD.unlink()
    if OUT_REPORT.exists(): OUT_REPORT.unlink()

    if not YAML_CSV.exists():
        print(f"[!] Нет файла: {YAML_CSV}")
        return
    if not XML_CSV.exists():
        print(f"[!] Нет файла: {XML_CSV}")
        return
    if not JSON_RAW.exists():
        print(f"[!] Нет файла: {JSON_RAW}")
        return

    print("[1/4] Чтение YAML (перелеты)...")
    df_yaml = pd.read_csv(YAML_CSV, sep='|')
    # Собираем ID карты: авиакомпания + номер (например, "FB 1234567")
    df_yaml['PassengerID'] = df_yaml['ff_airline'].astype(str).str.strip() + " " + df_yaml['ff_number'].astype(
        str).str.strip()

    print("[2/4] Подсчет статистики...")
    stats = df_yaml.groupby('PassengerID').agg(
        Total_Flights=('flight_num', 'count'),
        Business_Flights=('booking_class', lambda x: (x.astype(str).str.upper().isin(BUSINESS_CLASSES)).sum()),
        Airlines=('ff_airline', lambda x: ', '.join(sorted(set(x)))),
        Routes=('dep_airport', lambda x: ', '.join(sorted(set(x))))
    ).reset_index()

    suspects = stats[
        (stats['Total_Flights'] >= MIN_FLIGHTS) &
        (stats['Business_Flights'] >= 1)
        ].copy()
    print(f"    -> Найдено {len(suspects)} активных пассажиров бизнес-класса.")

    print("[3/4] Поиск в публичных базах XML и JSON...")
    df_xml = pd.read_csv(XML_CSV, sep='|')
    # В XML бонусные карты разбиты на airline + number
    xml_known = set(df_xml['ff_airline'].astype(str).str.strip() + " " + df_xml['ff_number'].astype(str).str.strip())
    xml_known.update(df_xml['user_id'].astype(str).str.strip().unique())

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

    print("[4/4] Формирование списка 'призраков'...")
    ghosts = suspects[
        ~suspects['PassengerID'].isin(xml_known) &
        ~suspects['PassengerID'].isin(json_known)
        ].copy()

    ghosts = ghosts.sort_values(by='Total_Flights', ascending=False).reset_index(drop=True)

    ghosts.to_csv(OUT_CSV, sep='|', index=False)
    print(f"    -> Найдено {len(ghosts)} 'призраков'. Сохранено в {OUT_CSV.name}.")

    # Генерируем детальный отчет в SPIES.md
    print("Генерация SPIES.md...")
    top_10 = ghosts.head(10).to_markdown(index=False)

    report = f"""# Отчет о подозрительных пассажирах

**Дата формирования:** {datetime.now().strftime("%Y-%m-%d")}

## Резюме
Выявлено **{len(ghosts)}** пассажиров с аномальной активностью (частые перелеты бизнес-классом), 
отсутствующих в открытых базах данных (бонусных программ).

## Методология
1. Анализ внутренних данных авиакомпании (`yaml_parsed_norm.csv`)
2. Подсчет рейсов и бизнес-класса по каждому PassengerID
3. Критерии отбора: >= {MIN_FLIGHTS} рейсов, хотя бы 1 бизнес-класс (J, C, D, I, A, Z, P)
4. Исключение пассажиров, найденных во внешних источниках (`xml_parsed_norm.csv`, `FrequentFlyerForum-Profiles.json`)

## Топ-10 подозрительных пассажиров

{top_10}

## Рекомендации
- Проверить выявленные номера через внутренние службы безопасности
- Выявить корпоративных клиентов с режимом конфиденциальности
- Настроить мониторинг новых рейсов для данных PassengerID
"""

    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"[SPIES.md] обновлён.")

    # Генерируем короткий отчет в report.md для VIEW
    generate_report_md(ghosts)
    print("✅ ГОТОВО!")


if __name__ == "__main__":
    try:
        import pandas
    except ImportError:
        print("Error! Load: pip install pandas tabulate")
        exit(1)

    main()