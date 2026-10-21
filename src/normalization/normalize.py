"""
normalize_aviation.py

Нормализует 7 CSV-файлов по отдельности, без merge.
Применяет:
  - транслитерацию кириллицы по заданному правилу;
  - латинскую нормализацию имён (апострофы, YA→IA, IY→II, EY→EI,
    YU→IU, AY→AI, TS→TC, X→KS);
  - uppercasing всех текстовых полей (города, страны, регионы и т.д.);
  - разбивку склеенных ФИО по колонкам.
"""

import re
from pathlib import Path
import pandas as pd
import numpy as np
import os
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT_DIR = Path(__file__).parent.parent.parent
INPUT_DIR = ROOT_DIR / "resources" / "processed" / "temp"
OUT_DIR = ROOT_DIR / "resources" / "processed"

print(INPUT_DIR)
print(OUT_DIR)
#INPUT_DIR = Path('../../resources/processed')
#OUT_DIR = Path('../../resources/processed')
#OUT_DIR.mkdir(exist_ok=True)

SEP = '|'


# ============================================================
# 1. Транслитерация
# ============================================================
TRANSLIT_MAP = {
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E',
    'Ё': 'E', 'Ж': 'ZH', 'З': 'Z', 'И': 'I', 'Й': 'I', 'К': 'K',
    'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R',
    'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'KH', 'Ц': 'TC',
    'Ч': 'CH', 'Ш': 'SH', 'Щ': 'SHCH', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
    'Э': 'E', 'Ю': 'IU', 'Я': 'IA',
}


def transliterate(s):
    if not isinstance(s, str):
        return s
    out = []
    for ch in s:
        up = ch.upper()
        if up in TRANSLIT_MAP:
            t = TRANSLIT_MAP[up]
            out.append(t.lower() if ch.islower() else t)
        else:
            out.append(ch)
    return ''.join(out)


def has_cyr(s):
    return isinstance(s, str) and bool(re.search('[А-Яа-яЁё]', s))


# ============================================================
# 2. Латинская нормализация имён
# ============================================================
def latin_name_rules(s):
    """Применяется к уже latin/upper строке."""
    if not isinstance(s, str):
        return s
    s = s.replace("'", "")   # апострофы (мягкий знак)
    s = s.replace("YA", "IA")  # NATALYA -> NATALIA
    s = s.replace("IY", "II")  # YURIY -> YURII
    s = s.replace("EY", "EI")  # SERGEY -> SERGEI
    s = s.replace("YU", "IU")  # YULIA -> IULIA
    s = s.replace("AY", "AI")  # ...
    s = s.replace("TS", "TC")  # TSAREV -> TCAREV
    s = s.replace("X",  "KS")  # ALEXEY -> ALEKSEI
    return s


def norm_name(s):
    """Trim + upper + (транслит если надо) + latin rules."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    s = str(s).strip().upper()
    if not s:
        return None
    if has_cyr(s):
        s = transliterate(s).upper()
    return latin_name_rules(s)


def split_fio(s, translit=True):
    """'ФАМИЛИЯ ИМЯ ОТЧЕСТВО' -> (last, first, middle) с нормализацией."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None, None, None
    s = str(s).strip()
    if not s:
        return None, None, None
    parts = s.split()
    if len(parts) == 1:
        last, first, middle = parts[0], None, None
    elif len(parts) == 2:
        last, first, middle = parts[0], parts[1], None
    else:
        last, first, middle = parts[0], parts[1], ' '.join(parts[2:])

    if translit:
        last   = norm_name(last)
        first  = norm_name(first)
        middle = norm_name(middle)
    else:
        last   = last.strip().upper()   if last   else None
        first  = first.strip().upper()  if first  else None
        middle = middle.strip().upper() if middle else None
    return last, first, middle


# ============================================================
# 3. Парсеры полей
# ============================================================
def s_clean(x, upper=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    x = str(x).strip()
    if not x:
        return None
    return x.upper() if upper else x


def norm_date(x, fmt=None):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        dt = (pd.to_datetime(s, format=fmt, errors='coerce')
              if fmt else pd.to_datetime(s, errors='coerce'))
        return None if pd.isna(dt) else dt.strftime('%Y-%m-%d')
    except Exception:
        return None


def norm_time(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip()
    if not s:
        return None
    m = re.match(r'^\s*(\d{1,2}):(\d{2})', s)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else s


def split_flight(x):
    """'SU1306NO' -> ('SU','1306','NO'); 'DL3377' -> ('DL','3377',None)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None, None, None
    s = str(x).strip().upper().replace(' ', '')
    if not s:
        return None, None, None
    m = re.match(r'^([A-Z0-9]{2})(\d+)([A-Z]*)$', s)
    if m:
        return m.group(1), m.group(2), m.group(3) or None
    return None, s, None


def split_ticket(x):
    """'7360415302044672  9375' -> ('7360415302044672','9375')."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None, None
    s = str(x).strip()
    if not s:
        return None, None
    p = s.split()
    t = re.sub(r'\D', '', p[0]) or None
    c = p[1] if len(p) > 1 else None
    return t, c


def parse_ff(x):
    """'FF#SU 38116280' / 'FB 171388778' -> (airline, number)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None, None
    s = str(x)
    m = re.search(r'FF#\s*([A-Z0-9]{2})\s*(\d+)', s, re.IGNORECASE)
    if m:
        return m.group(1).upper(), m.group(2)
    m = re.match(r'^\s*([A-Z]{2})\s+(\d+)\s*$', s)
    if m:
        return m.group(1).upper(), m.group(2)
    return None, None


def parse_city_region(s):
    """'Boston MA' -> ('BOSTON','MA'); 'New York' -> ('NEW YORK', None)."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None, None
    s = str(s).strip()
    if not s:
        return None, None
    p = s.rsplit(' ', 1)
    if len(p) == 2 and len(p[1]) == 2 and p[1].isalpha():
        return p[0].strip().upper(), p[1].upper()
    return s.upper(), None


def parse_city_country(s):
    """'Aalborg, Denmark' -> ('AALBORG','DENMARK')."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None, None
    s = str(s).strip()
    if not s:
        return None, None
    p = [x.strip() for x in s.split(',')]
    return (p[0].upper(), p[1].upper()) if len(p) >= 2 else (s.upper(), None)


def parse_duration(s):
    """'1H25M' -> 85."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    s = str(s).strip().upper()
    m = re.match(r'^(\d+)H(\d+)M$', s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.match(r'^(\d+)H$', s)
    if m:
        return int(m.group(1)) * 60
    m = re.match(r'^(\d+)M$', s)
    if m:
        return int(m.group(1))
    return None


MONTHS = {m: i + 1 for i, m in enumerate(
    ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
     'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'])}


def parse_validity(s):
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return {}
    s = str(s)
    m = re.match(r'(\d{1,2})\s+([A-Za-z]{3})\s*-\s*(\d{1,2})\s+([A-Za-z]{3})', s)
    if not m:
        return {}
    return {
        'valid_from_day':   int(m.group(1)),
        'valid_from_month': MONTHS.get(m.group(2).upper()),
        'valid_to_day':     int(m.group(3)),
        'valid_to_month':   MONTHS.get(m.group(4).upper()),
    }


def read_csv_std(path, sep=SEP):
    return pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False) \
             .drop_duplicates().reset_index(drop=True)


def safe_split(df, col, default_cols):
    if col not in df.columns:
        return pd.DataFrame({c: [None] * len(df) for c in default_cols}, index=df.index)
    sp = df[col].fillna('').astype(str).str.split(n=1, expand=True)
    for i, c in enumerate(default_cols):
        if i not in sp.columns:
            sp[i] = None
    return sp[list(range(len(default_cols)))]

def normalize_boarding_pass(path):
    df = read_csv_std(path, sep='|')
    if 'PassengerFirstName' in df.columns:
        df = df[df['PassengerFirstName'].str.upper() != 'PASSENGERFIRSTNAME'].reset_index(drop=True)

    docs = safe_split(df, 'PassengerDocument', ['doc_series', 'doc_number'])
    fn = df['FlightNumber'].apply(split_flight) if 'FlightNumber' in df else [(None, None, None)] * len(df)

    out = pd.DataFrame({
        'pnr':              df.get('BookingCode', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'ticket_number':    df.get('TicketNumber', pd.Series([None]*len(df))).apply(lambda x: split_ticket(x)[0]),
        'passenger_last':   df.get('PassengerLastName',  pd.Series([None]*len(df))).apply(norm_name),
        'passenger_first':  df.get('PassengerFirstName', pd.Series([None]*len(df))).apply(norm_name),
        'passenger_middle': df.get('PassengerSecondName',pd.Series([None]*len(df))).apply(norm_name),
        'sex':              df.get('PassengerSex', pd.Series([None]*len(df)))
                              .astype(str).str.strip().str.upper()
                              .map({'MALE': 'M', 'FEMALE': 'F'}).where(lambda s: s.notna(), None),
        'birth_date':       df.get('PassengerBirthDate', pd.Series([None]*len(df))).apply(lambda x: norm_date(x, '%d/%m/%Y')),
        'doc_series':       docs[0].apply(lambda x: s_clean(x, True)),
        'doc_number':       docs[1].apply(lambda x: s_clean(x, True)),
        'baggage_code':     df.get('Baggage', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'flight_date':      df.get('FlightDate', pd.Series([None]*len(df))).apply(norm_date),
        'dep_time':         df.get('FlightTime', pd.Series([None]*len(df))).apply(norm_time),
        'airline_code':     [t[0] for t in fn],
        'flight_num':       [t[1] for t in fn],
        'codeshare':        df.get('CodeShare', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'arr_city':         df.get('Destination', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
    })
    return out


def normalize_cleaned(path):
    df = read_csv_std(path)
    fn = df['Номер_рейса'].apply(split_flight) if 'Номер_рейса' in df else [(None, None, None)] * len(df)
    ff = df['Бонусная_карта'].apply(parse_ff) if 'Бонусная_карта' in df else [(None, None)] * len(df)

    out = pd.DataFrame({
        'checkin_queue':    pd.to_numeric(df.get('Очередь_регистрации', pd.Series([None]*len(df))), errors='coerce'),
        'booking_class':    df.get('Класс_обслуживания', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'pnr':              df.get('PNR_бронь', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'ticket_number':    df.get('Номер_эл_билета', pd.Series([None]*len(df))).apply(lambda x: split_ticket(x)[0]),
        'ff_airline':       [t[0] for t in ff],
        'ff_number':        [t[1] for t in ff],
        'passenger_last':   df.get('Фамилия',  pd.Series([None]*len(df))).apply(norm_name),
        'passenger_first':  df.get('Имя',      pd.Series([None]*len(df))).apply(norm_name),
        'passenger_middle': df.get('Отчество', pd.Series([None]*len(df))).apply(norm_name),
        'dep_city':         df.get('Город_вылета',  pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'arr_city':         df.get('Город_прилета', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'dep_airport':      df.get('Код_аэропорта_вылета',  pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'arr_airport':      df.get('Код_аэропорта_прилета', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'flight_date':      df.get('Дата_вылета', pd.Series([None]*len(df))).apply(norm_date),
        'dep_time':         df.get('Время_вылета', pd.Series([None]*len(df))).apply(norm_time),
        'airline_code':     [t[0] for t in fn],
        'flight_num':       [t[1] for t in fn],
    })
    return out


def normalize_json(path):
    df = read_csv_std(path)
    fn = df['Flight'].apply(split_flight) if 'Flight' in df else [(None, None, None)] * len(df)
    dc = df['DepCity'].apply(parse_city_region) if 'DepCity' in df else [(None, None)] * len(df)
    ac = df['ArrCity'].apply(parse_city_region) if 'ArrCity' in df else [(None, None)] * len(df)

    cs = df.get('Codeshare', pd.Series([None]*len(df))).astype(str).str.strip().str.lower() \
           .map({'true': True, 'false': False}).where(lambda s: s.notna(), None)

    out = pd.DataFrame({
        'flight_date':  df.get('Date', pd.Series([None]*len(df))).apply(norm_date),
        'codeshare':    cs,
        'airline_code': [t[0] for t in fn],
        'flight_num':   [t[1] for t in fn],
        'dep_city':     [t[0] for t in dc],
        'dep_region':   [t[1] for t in dc],
        'dep_airport':  df.get('DepAirport', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'dep_country':  df.get('DepCountry', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'arr_city':     [t[0] for t in ac],
        'arr_region':   [t[1] for t in ac],
        'arr_airport':  df.get('ArrAirport', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'arr_country':  df.get('ArrCountry', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
    })
    return out


def normalize_sirena(path):
    df = read_csv_std(path)

    names   = df.get('PaxName', pd.Series([None]*len(df))).apply(lambda x: split_fio(x, translit=True))
    tickets = df.get('e-Ticket', pd.Series([None]*len(df))).apply(split_ticket)
    fn      = df.get('FlightCode', pd.Series([None]*len(df))).apply(split_flight)
    ff      = df.get('PaxAdditionalInfo', pd.Series([None]*len(df))).apply(parse_ff)

    td = df.get('TravelDoc', pd.Series(['']*len(df))).astype(str).str.replace('N/A', '', regex=False)
    docs = safe_split(df.assign(TravelDoc_=td), 'TravelDoc_', ['doc_number', 'doc_series'])

    out = pd.DataFrame({
        'pnr':              df.get('Code', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'ticket_number':    [t[0] for t in tickets],
        'ticket_coupon':    [t[1] for t in tickets],
        'passenger_last':   [t[0] for t in names],
        'passenger_first':  [t[1] for t in names],
        'passenger_middle': [t[2] for t in names],
        'birth_date':       df.get('PaxBirthDate', pd.Series([None]*len(df))).apply(norm_date),
        'doc_series':       docs[0].apply(lambda x: s_clean(x, True)),
        'doc_number':       docs[1].apply(lambda x: s_clean(x, True)),
        'flight_date':      df.get('DepartDate', pd.Series([None]*len(df))).apply(norm_date),
        'dep_time':         df.get('DepartTime', pd.Series([None]*len(df))).apply(norm_time),
        'arr_date':         df.get('ArrivalDate', pd.Series([None]*len(df))).apply(norm_date),
        'arr_time':         df.get('ArrivalTime', pd.Series([None]*len(df))).apply(norm_time),
        'dep_airport':      df.get('ShFrom', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'arr_airport':      df.get('Dest', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'airline_code':     [t[0] for t in fn],
        'flight_num':       [t[1] for t in fn],
        'flight_suffix':    [t[2] for t in fn],
        'seat':             df.get('Seat', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'meal':             df.get('Meal', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'booking_class':    df.get('TrvCls', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'fare_basis':       df.get('Fare', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'baggage_code':     df.get('Baggage', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'ff_airline':       [t[0] for t in ff],
        'ff_number':        [t[1] for t in ff],
        'agent_info':       df.get('AgentInfo', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
    })
    return out


def normalize_timetable(path):
    df = read_csv_std(path)
    fn = df['FLIGHT'].apply(split_flight) if 'FLIGHT' in df else [(None, None, None)] * len(df)
    dc = df['FROM_CITY'].apply(parse_city_country) if 'FROM_CITY' in df else [(None, None)] * len(df)
    ac = df['TO_CITY'].apply(parse_city_country)   if 'TO_CITY'   in df else [(None, None)] * len(df)
    vd = df['VALIDITY'].apply(parse_validity)      if 'VALIDITY'  in df else [{}] * len(df)

    out = pd.DataFrame({
        'validity_raw':     df.get('VALIDITY', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'days_raw':         df.get('DAYS', pd.Series([None]*len(df))).apply(s_clean),
        'dep_time':         df.get('DEP_TIME', pd.Series([None]*len(df))).apply(norm_time),
        'arr_time':         df.get('ARR_TIME', pd.Series([None]*len(df))).apply(norm_time),
        'airline_code':     [t[0] for t in fn],
        'flight_num':       [t[1] for t in fn],
        'aircraft':         df.get('AIRCRAFT', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'duration_min':     df.get('TRAVEL_TIME', pd.Series([None]*len(df))).apply(parse_duration),
        'dep_city':         [t[0] for t in dc],
        'dep_country':      [t[1] for t in dc],
        'dep_airport':      df.get('FROM_CODE', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'arr_city':         [t[0] for t in ac],
        'arr_country':      [t[1] for t in ac],
        'arr_airport':      df.get('TO_CODE', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'operated_by':      df.get('OPERATED_BY', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'valid_from_day':   [d.get('valid_from_day')   for d in vd],
        'valid_from_month': [d.get('valid_from_month') for d in vd],
        'valid_to_day':     [d.get('valid_to_day')     for d in vd],
        'valid_to_month':   [d.get('valid_to_month')   for d in vd],
    })
    return out


def normalize_xml(path):
    df = read_csv_std(path)
    fn = df['Code'].apply(split_flight)   if 'Code'       in df else [(None, None, None)] * len(df)
    ff = df['CardNumber'].apply(parse_ff) if 'CardNumber' in df else [(None, None)] * len(df)

    out = pd.DataFrame({
        'user_id':         df.get('UserId', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'passenger_first': df.get('FirstName', pd.Series([None]*len(df))).apply(norm_name),
        'passenger_last':  df.get('LastName',  pd.Series([None]*len(df))).apply(norm_name),
        'ff_airline':      [t[0] for t in ff],
        'ff_number':       [t[1] for t in ff],
        'bonus_program':   df.get('BonusProgram', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'airline_code':    [t[0] for t in fn],
        'flight_num':      [t[1] for t in fn],
        'flight_date':     df.get('Date', pd.Series([None]*len(df))).apply(norm_date),
        'dep_airport':     df.get('Departure', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'arr_airport':     df.get('Arrival',   pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'fare_basis':      df.get('Fare', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
    })
    return out


def normalize_yaml(path):
    df = read_csv_std(path)
    fn = df['Flight'].apply(split_flight) if 'Flight' in df else [(None, None, None)] * len(df)

    out = pd.DataFrame({
        'flight_date':   df.get('Date', pd.Series([None]*len(df))).apply(norm_date),
        'airline_code':  [t[0] for t in fn],
        'flight_num':    [t[1] for t in fn],
        'dep_airport':   df.get('From', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'arr_airport':   df.get('To',   pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'status':        df.get('Status', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'ff_airline':    df.get('FF_Airline', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'ff_number':     df.get('FF_Number',  pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'booking_class': df.get('Class', pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
        'fare_basis':    df.get('Fare',  pd.Series([None]*len(df))).apply(lambda x: s_clean(x, True)),
    })
    return out

def process_one(job):
    """
    Выполняется в отдельном процессе:
    прочитать → нормализовать → записать CSV.
    Возвращает (name, rows, cols, error_str|None).
    """
    name, fn, src_str, dst_str = job
    try:
        df = fn(Path(src_str))
        df.to_csv(Path(dst_str), sep='|', index=False, encoding='utf-8')
        return name, len(df), len(df.columns), None
    except Exception as e:
        return name, 0, 0, f"{type(e).__name__}: {e}"



def main():
    tasks = [
        ('BoardingData_parsed.csv',   normalize_boarding_pass),
        ('cleaned_boarding_pass.csv', normalize_cleaned),
        ('json_parsed.csv',           normalize_json),
        ('sirena_parsed.csv',         normalize_sirena),
        ('Skyteam_Timetable.csv',     normalize_timetable),
        ('xml_parsed.csv',            normalize_xml),
        ('yaml_parsed.csv',           normalize_yaml),
    ]

    jobs = []
    for name, fn in tasks:
        src = INPUT_DIR / name
        dst = OUT_DIR / (name[:-4] + "_norm.csv")
        if not src.exists():
            print(f"[skip] {name}: not found")
            continue
        jobs.append((name, fn, str(src), str(dst)))

    if not jobs:
        print("Нечего обрабатывать.")
        return

    # 7 файлов — многовато для 1 ядра, но мало для большого пула.
    max_workers = min(len(jobs), os.cpu_count() or 4)
    print(f"[parallel] {len(jobs)} files, workers={max_workers}")

    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(process_one, job): job[0] for job in jobs}
        for fut in as_completed(futures):
            name, rows, cols, err = fut.result()
            if err:
                print(f"[fail] {name}: {err}")
            else:
                print(f"[done] {name}: rows={rows}, cols={cols}")

    print("\n=== пример: правила транслитерации / латинской нормализации ===")
    for raw in ["ОЗЕРОВ ИЛЬДАР ДАНИИЛОВИЧ",
                "НАТАЛЬЯ ПЕТРОВНА",
                "ЮРИЙ ВАЛЕРЬЕВИЧ",
                "СЕРГЕЙ АЛЕКСЕЕВИЧ",
                "NATAL'YA SMIRNOVA",
                "ALEXEY MAXIMOV",
                "YURIY SERGEYEV"]:
        print(f"  {raw!r:40s} -> {split_fio(raw)}")

    for name in ('sirena_parsed.csv', 'BoardingPass_parsed.csv'):
        p = OUT_DIR / name
        if p.exists():
            df = pd.read_csv(p, sep='|', dtype=str, keep_default_na=False)
            ncols = [c for c in ('passenger_last', 'passenger_first', 'passenger_middle') if c in df.columns]
            if ncols:
                print(f"\n--- {name}: ФИО (пример) ---")
                print(df[ncols].head().to_string(index=False))

    for name, cols in [('json_parsed.csv',          ['dep_city', 'dep_country', 'arr_city', 'arr_country']),
                       ('Skyteam_Timetable.csv',    ['dep_city', 'dep_country', 'arr_city', 'arr_country'])]:
        p = OUT_DIR / name
        if p.exists():
            df = pd.read_csv(p, sep='|', dtype=str, keep_default_na=False)
            cols = [c for c in cols if c in df.columns]
            if cols:
                print(f"\n--- {name}: города/страны (пример) ---")
                print(df[cols].head().to_string(index=False))

if __name__ == '__main__':
    main()