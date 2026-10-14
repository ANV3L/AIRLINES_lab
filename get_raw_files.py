from pathlib import Path
import gdown

# Ссылка на твою папку Google Drive
DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/19bCT5pKF-QnfW05FW0Eb2dUsMrrnbUSD"

# Путь, куда сохраняем сырые данные
RAW_DATA_DIR = Path("resources/raw")


def download_raw_dataset(folder_url: str, output_dir: Path) -> None:
    """Скачивает всю папку с Google Drive в указанную директорию."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Начинаю скачивание папки в: {output_dir.resolve()}...")

    # gdown.download_folder автоматически скачивает все файлы из папки по ссылке
    gdown.download_folder(
        url=folder_url,
        output=str(output_dir),
        quiet=False,
        use_cookies=False,
    )

    print("\nЗагрузка завершена! Скачанные файлы:")
    for file in output_dir.glob("*"):
        if file.is_file():
            # Выводим имя и размер файла в МБ
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f" - {file.name} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    download_raw_dataset(DRIVE_FOLDER_URL, RAW_DATA_DIR)