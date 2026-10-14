import argparse
import os
import zipfile
import gdown

'''
Установка зависимостей:
  pip install -r requirements.txt;
  
Скачивание вообще всех файлов:
  python fetch_resources.py
  
Скачивание всех кроме RAW
  python fetch_resources.py --only_processed=True  
'''

# Путь, куда сохраняем сырые данные
RAW_DATA_DIR = "resources/raw"
# Ссылка на архив с сырыми данными (конкретный файл)
RAW_DATA_URL = (
    "https://drive.google.com/file/d/1LkvceJHziGFI9abUb2qe8uErI4oudkbb/view?usp=drive_link"
)

PROCESSED_DATA_DIR = "resources/processed"
# Ссылка на ОБЩУЮ ПАПКУ с processed файлами
PROCESSED_DATA_URL = (
    "https://drive.google.com/drive/folders/1fDevjQeHCYMPit5-NtZZj6srkdTIcAv9?usp=drive_link"
)


def extract_nested_archives(directory):
  """Рекурсивно ищет и распаковывает все ZIP-архивы внутри указанной директории."""
  print("🔍 Проверяем наличие вложенных архивов...")

  extracted_anything = True
  while extracted_anything:
    extracted_anything = False
    for root, dirs, files in os.walk(directory):
      for file in files:
        if file.lower().endswith(".zip"):
          archive_path = os.path.join(root, file)

          # Создаем папку для содержимого этого вложенного архива (с именем файла без .zip)
          sub_extract_dir = os.path.join(root, os.path.splitext(file)[0])
          os.makedirs(sub_extract_dir, exist_ok=True)

          print(f"📦 Найдено вложенное: {file} -> распаковываем...")
          try:
            with zipfile.ZipFile(archive_path, "r") as inner_zip:
              inner_zip.extractall(sub_extract_dir)

            os.remove(archive_path)
            print(f"🗑️ Вложенный архив удален: {file}")

            extracted_anything = (
                True  # запускаем цикл заново на случай архивов внутри архивов
            )
          except Exception as e:
            print(f"❌ Ошибка при распаковке вложенного архива {file}: {e}")


def download_and_extract_file(url, extract_to):
  """Скачивает конкретный архив-файл и распаковывает его."""
  output_archive = "downloaded_archive.zip"

  print("🔄 Скачиваем файл с Google Диска...")
  try:
    gdown.download(url, output_archive)
    print("✅ Файл успешно скачан.")
  except Exception as e:
    print(f"❌ Ошибка при скачивании: {e}")
    return

  if not os.path.exists(output_archive):
    print("❌ Не удалось найти скачанный архив.")
    return

  print(f"🔄 Распаковываем главный архив в '{extract_to}'...")
  try:
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(output_archive, "r") as zip_ref:
      zip_ref.extractall(extract_to)
    print("✅ Главный архив успешно распакован.")
  except Exception as e:
    print(f"❌ Ошибка при распаковке главного архива: {e}")
  finally:
    if os.path.exists(output_archive):
      os.remove(output_archive)

  # Запускаем распаковку вложенных архивов
  extract_nested_archives(extract_to)
  print("🎉 Готово! Все архивы распакованы.")


def download_folder_contents(url, extract_to):
  """Скачивает всю папку с Google Диска и распаковывает архивы внутри неё."""
  print(f"🔄 Скачиваем папку с Google Диска в '{extract_to}'...")
  try:
    os.makedirs(extract_to, exist_ok=True)
    gdown.download_folder(url, output=extract_to, quiet=False)
    print("✅ Папка успешно скачана.")
  except Exception as e:
    print(f"❌ Ошибка при скачивании папки: {e}")
    return

  # Запускаем распаковку всех архивов, которые приехали вместе с папкой
  extract_nested_archives(extract_to)
  print("🎉 Готово! Все файлы и архивы из папки обработаны.")


if __name__ == "__main__":
  p = argparse.ArgumentParser()
  p.add_argument('--only_processed', type=bool, default=False, help='Флаг для скачивания только обработанных данных')
  args = p.parse_args()

  if not args.only_processed:
    download_and_extract_file(RAW_DATA_URL, RAW_DATA_DIR)

  download_folder_contents(PROCESSED_DATA_URL, PROCESSED_DATA_DIR)