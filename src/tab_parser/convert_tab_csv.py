import pandas as pd
import  argparse

ap = argparse.ArgumentParser()
ap.add_argument("-i", "--input", required=True)

input_file_path = ap.parse_args().input

# Позиции колонок (start, end) — взяты из формата Sirena
colspecs = [
    (0, 60),    # PaxName
    (60, 72),   # PaxBirthDate
    (72, 84),   # DepartDate
    (84, 96),   # DepartTime
    (96, 108),  # ArrivalDate
    (108, 120), # ArrivalTime
    (120, 132), # FlightCode
    (132, 138), # ShFrom
    (138, 144), # Dest
    (144, 150), # Code
    (150, 172), # e-Ticket
    (172, 184), # TravelDoc
    (184, 190), # Seat
    (190, 196), # Meal
    (196, 202), # TrvCls
    (202, 214), # Fare
    (214, 226), # Baggage
    (226, 256), # PaxAdditionalInfo
    (256, 316), # AgentInfo
]

columns = [
    "PaxName", "PaxBirthDate", "DepartDate", "DepartTime",
    "ArrivalDate", "ArrivalTime", "FlightCode", "ShFrom",
    "Dest", "Code", "e-Ticket", "TravelDoc", "Seat",
    "Meal", "TrvCls", "Fare", "Baggage",
    "PaxAdditionalInfo", "AgentInfo",
]

df = pd.read_fwf(
    input_file_path,  
    colspecs=colspecs,
    names=columns,
    encoding="utf-8",
    dtype=str,
    skiprows=1,                  # пропускаем строку заголовка
)

# Убираем пробелы по краям
df = df.apply(lambda s: s.str.strip())

print(df.head())
print(df.shape)   # должно быть (N, 19)

df.to_csv("sirena_parsed.csv", sep="|", index=False, encoding="utf-8-sig")