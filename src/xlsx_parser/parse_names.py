import pandas as pd


def normalize_name(name: str) -> str:
    # Если значение пустое (NaN из Pandas) или не строка — возвращаем как есть
    if not isinstance(name, str):
        return name

    # 1. Убираем апострофы (одинарные кавычки)
    result = name.replace("'", "")

    # 2. Заменяем YA на IA (например, NATALYA -> NATALIA)
    result = result.replace("YA", "IA")

    # 3. Заменяем IY на II (например, YURIY -> YURII)
    result = result.replace("IY", "II")

    result = result.replace("EY", "EI")

    result = result.replace("YU", "IU")

    result = result.replace("AY", "AI")

    result = result.replace("TS", "TC")

    result = result.replace("X", "KS")


    return result

def parse_names(df):


    # Сеты для сбора данных (золотой стандарт)
    known_first_names = set()
    known_last_names = set()


    for name in df["Имя_пассажира"]:
        name = normalize_name(name)
        parts = name.split()

        # Ищем инициал (одиночную букву)
        init_idx = -1
        for i, p in enumerate(parts):
            if len(p) == 1 and p.isalpha():
                init_idx = i
                break

        # Если нашли инициал и в строке ровно 3 слова
        if init_idx != -1 and len(parts) == 3:
            if init_idx == 2:  # Формат: Фамилия Имя Инициал
                known_last_names.add(parts[0].upper())
                known_first_names.add(parts[1].upper())
            elif init_idx == 1:  # Формат: Имя Инициал Фамилия
                known_first_names.add(parts[0].upper())
                known_last_names.add(parts[2].upper())
            else:
                raise TypeError("Инициал на первом месте в" + name)

    parsed_last = []
    parsed_first = []
    parsed_middle = []

    count_all = 0
    conflicts = 0
    bad_format = 0
    for name in df["Имя_пассажира"]:
        name= normalize_name(name)
        parts = name.split()
        count_all += 1

        # Снова ищем инициал
        init_idx = -1
        for i, p in enumerate(parts):
            if len(p) == 1 and p.isalpha():
                init_idx = i
                break

        lname, fname, mname = None, None, None

        if init_idx != -1:
            # Если есть инициал — разбираем строго по позиции
            mname = parts[init_idx]
            if init_idx == 2:
                lname, fname = parts[0], parts[1]
            elif init_idx == 1:
                fname, lname = parts[0], parts[2]
            elif init_idx == 0:
                fname, lname = parts[1], parts[2]
        else:
            # Если инициала нет — используем наши сеты
            if len(parts) == 2:
                w1, w2 = parts[0].upper(), parts[1].upper()

                # Проверяем, какое из слов есть в базе имен
                if w1 in known_first_names and w2 not in known_first_names:
                    fname, lname = parts[0], parts[1]
                elif w2 in known_first_names and w1 not in known_first_names:
                    lname, fname = parts[0], parts[1]
                elif w1 in known_last_names and w2 not in known_last_names:
                    lname, fname = parts[0], parts[1]
                elif w2 in known_last_names and w1 not in known_last_names:
                    fname, lname = parts[0], parts[1]
                else:
                    # Если оба слова незнакомы или оба знакомы — используем порядок по умолчанию
                    # (например, Фамилия Имя, так как это стандарт для загранпаспортов)
                    lname, fname = parts[0], parts[1]
                    conflicts += 1
                    print("Неразрешенный конфликт:", name )
            elif len(parts) == 1:
                lname = parts[0]
                bad_format += 1
                err = "Совсем странное имя:"+ name
                raise TypeError(err)

        parsed_last.append(lname)
        parsed_first.append(fname)
        parsed_middle.append(mname)

    # Добавляем результаты
    df["Фамилия"] = parsed_last
    df["Имя"] = parsed_first
    df["Отчество"] = parsed_middle

    print("Stats:", count_all, conflicts, bad_format,"Conflicts percent:", conflicts/count_all * 100, "%")
    return df