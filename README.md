# Запуск скриптов

## 📋 Требования

- **Python 3.10+**
- **make**

## 🚀 Установка и запуск

### 1. Скачать данные с дисков:

```bash
make fetch_all
```

### 1.1. Чтобы скачать только processed:

```bash
make fetch_only_processed
```

### 2. Преобразовать все данные в .csv
```bash
make convert_to_csv
```

### 2.1 Преобразовать конкретные файлы

```bash
make xml_json_to_csv
```
```bash
make yaml_to_csv
```
```bash
make tab_to_csv
```
```bash
make xlsx_to_csv
```
```bash
make pdf_to_csv #пока сломано
```


### 3. Чтобы очистить каталоги в resources:

```bash
make clean_all
```

### 3.1. Чтобы очистить конкретные каталоги в resources:

Обработанные данные:
```bash
make clean_processed
```
Сырые данные:
```bash
make clean_raw
```
Промежуточные данные:
```bash
make clean_interim
```