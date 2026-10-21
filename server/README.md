# Запуск

```
python3 app.py
```

# За что отвечает каждый файл

## app.py

Этот файлик трогать не надо, тут все хорошо

## index.html

На 931 строке добавлять новые кнопки в BUTTONS
```
    const BUTTONS = [
        { command: "download_raw_data", label: "Download raw data", secondary: true },
        { command: "download_processed_data", label: "Download processed data", secondary: true },
        { divider: true },
        <!-- Ниже добавлять новые кнопки -->
        { command: "Count rows in files", label: "Count rows in files" },
    ];
```

## commands.py

Здесь надо добавить в словарь { "имя кнопки" : ваша_функция }

## functions.py

Если функция маленькая или служебная ( Чтобы через неё обратиться к вашему коду ), то добавляйте её сюда

### КОНТРАКТ
- Принимает 0 аргументов
- Возвращает str: "0" при успехе и "1" при ошибке
- Результат вашей функции в report.md должен быть записан, чтобы UI мог его вывести