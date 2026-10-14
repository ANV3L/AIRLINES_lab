## 📋 Требования

- Python **3.10+**

## 🚀 Установка и запуск

### 1. Создать виртуальное окружение

```bash
python -m venv .venv
```

### 2. Активировать его

**Linux / macOS:**

```bash
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

**Windows (cmd):**

```cmd
.venv\Scripts\activate.bat
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Подгрузить все данные с Google Drive
Ссылка на Google Drive, откуда будут скачаны обработанные файлы:
    https://drive.google.com/drive/folders/1fDevjQeHCYMPit5-NtZZj6srkdTIcAv9?usp=drive_link

Скачивание вообще всех файлов:
```bash
python fetch_resources.py
```

Скачивание всех кроме RAW (исходных):
```bash
python fetch_resources.py --only_processed=True
```

