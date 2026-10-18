.PHONY: venv_up clean_raw fetch_all send_reports notify

# Находим ВСЕ файлы requirements.txt в подпапках scripts/
ALL_REQS = $(shell find . -name "requirements.txt")
NOTEBOOK_PATH1 = src/pdf_parser/pdf_process.ipynb
NOTEBOOK_PATH2 = src/pdf_parser/ETL.ipynb

# 1. Создание venv, если его нет
.venv/bin/activate:
	python3 -m venv .venv
	echo $(ALL_REQS)

# 2. Установка зависимостей. Шаг сработает, если изменился ХОТЯ БЫ ОДИН из requirements.txt
.venv/bin/pip: $(ALL_REQS) .venv/bin/activate
	.venv/bin/pip install --upgrade pip
	@# Цикл устанавливает пакеты из каждого найденного файла
	@for req in $(ALL_REQS); do \
		echo "Установка зависимостей из $$req..."; \
		.venv/bin/pip install -r $$req; \
	done
	.venv/bin/pip install jupyter nbconvert
	@touch .venv/bin/pip

# Алиас для подготовки окружения
venv_up: .venv/bin/pip





fetch_only_processed: .venv/bin/pip
	.venv/bin/python scripts/fetch_resources/fetch_resources.py --only_processed=True

fetch_all: .venv/bin/pip
	.venv/bin/python scripts/fetch_resources/fetch_resources.py
	mv resources/raw/Airlines/* resources/raw/
	rmdir resources/raw/Airlines


convert_to_csv: xml_json_to_csv yaml_to_csv xlsx_to_csv tab_to_csv # pdf_to_csv <-- добавить когда починят pdf_parser

xml_json_to_csv: .venv/bin/pip
	cd src/xml_and_json_parsers && \
	cmake -S . -B build  && \
	cmake --build build -j && \
	./build/bin/json_parser && \
	./build/bin/xml_parser

xlsx_to_csv: .venv/bin/pip
	.venv/bin/python src/xlsx_parser/parse_xlsx.py --folder resources/raw/YourBoardingPassDotAero
	mv boarding_pass_raw.csv resources/interim/YourBoardingPassDotAero/
	mv cleaned_boarding_pass.csv resources/processed/

tab_to_csv: .venv/bin/pip
	.venv/bin/python src/tab_parser/convert_tab_csv.py --input resources/raw/Sirena-export-fixed.tab
	mv sirena_parsed.csv resources/processed

yaml_to_csv: .venv/bin/pip
	cd src/yaml_parser && \
	cmake -S . -B build  && \
	cmake --build build -j && \
	./build/yaml_parser

#pdf_to_csv: .venv/bin/pip # <-- пока что сломано
#	.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.kernel_name=python3 --inplace $(NOTEBOOK_PATH1)
#	.venv/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.kernel_name=python3 --inplace $(NOTEBOOK_PATH2)

normalize: .venv/bin/pip
	.venv/bin/python src/normalization/normalize.py

server: .venv/bin/pip
	.venv/bin/python server/app.py

clean_raw:
	find resources/raw/ -mindepth 1 ! -name 'README.md' -delete

clean_processed:
	find resources/processed/ -mindepth 1 ! -name 'README.md' -delete

clean_interim:
	find resources/interim/ -mindepth 1 ! -name 'README.md' -delete


clean_all: clean_processed clean_raw clean_interim