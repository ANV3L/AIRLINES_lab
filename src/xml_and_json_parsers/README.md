## Сборка сразу двух парсеров
``` bash
cmake -S . -B build 
cmake --build build -j
```

## Сборка конкретного парсера
-DJSONP=OFF - отключает json-парсер\
-DXMLP=OFF - отключает xml-парсер

``` bash 
cmake -S . -B build -DJSONP=OFF # отключаем сборку JSON-парсера, соберется только XML
cmake --build build -j
```


## Запуск исполняемых файлов
Запуск json-парсера
``` bash
./build/bin/json_parser
```
Запуск xml-парсера
``` bash
./build/bin/xml_parser
```

## P.S.
Опции кешируются в build/CMakeCache.txt.\
Чтобы гарантированно вернуть сборку обоих парсеров, выполните:
```
cmake -S . -B build -DJSONP=ON -DXMLP=ON
```
или удалите build/ и сконфигурируйте заново.