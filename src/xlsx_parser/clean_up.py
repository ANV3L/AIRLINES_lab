import parse_names
import pandas as pd

def make_clean_csv(df):

    # 2. Удаляем дубликаты
    df = df.drop_duplicates()

    # 3. Парсим имена
    df = parse_names.parse_names(df)
    df = df.drop(columns=["Имя_пассажира"])

    # 4. Сохраняем очищенный файл
    df.to_csv("cleaned_boarding_pass.csv", sep="|", index=False, encoding="utf-8-sig")

    print("Готово! Очищенный файл сохранен как cleaned_boarding_pass.csv")
    return df