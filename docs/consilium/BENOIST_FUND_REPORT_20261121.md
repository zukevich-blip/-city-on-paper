# Фонд Бенуа · отчёт по наряду №92 · 21.11.2026

Ветка `claude/consilium-wander`. На основной сайт опубликована версия `bdfcd1d` (PR №94–97); позднейшие коммиты не опубликованы.

## Реестр (data/research/benoist/registry-v1.json)

| Показатель | Значение |
|---|---|
| Найдено записей (4 файла поиска) | 927 |
| Разных листов (верхняя оценка: дубли между BnF, Gallica и Europeana склеены грубо) | 669 |
| Повторные оттиски / записи тех же листов | 258 |
| Записи, прочитанные на странице источника | 437 |
| Листы с открытым по лицензии файлом (по записи источника) | 191 |
| Листы, показанные картинкой в книге | 49 |
| Только ссылка на хранителя / без файла | 478 / 471 |
| Филипп / Феликс / автор неясен | 418 / 117 / 134 |

По источникам: старый сбор 174, BnF+Europeana+Heidelberg+Internet Archive 416, музеи (LoC, NGA, Met, Rijks, V&A, Brown, Europeana) 261, Paris Musées 76.

## Изображения

- В публичной книге: 36 листов (14 Paris Musées CC0 на файл по манифесту, 22 Rijksmuseum PDM), файлы лежат в `book/img/benoist/`.
- Ждут загрузки: 19 листов Paris Musées с CC0 по манифесту. Сайт музея обрывает передачу больших файлов, прогоны 21.11 добавили 3. Повторить: `python3 tools/world/ingest_parismusees.py --delay 3`.
- Остальное (BnF/Gallica, LoC «No known restrictions», NGA, V&A, Brown и др.) только ссылки и метаданные.

## Не удалось / не сделано

- Gallica, Morgan, British Museum, Yale, BNE, HathiTrust: 403/challenge. Commons, Google Books: 429. Том 3 «Paris dans sa splendeur» не перечислен.
- 52 записи Paris Musées прочитаны только по карточке (включая 9 листов Феликса).
- Склейка каталожных арок BnF с арками Gallica не сделана.
- Пластины Heidelberg: авторство не установлено, том 1 написан 18 иллюстраторами.
- Личный просмотрщик `private-archive/` не сделан (граница и скрипт есть: `tools/private/fetch_private_archive.py`).

## Границы публичного и личного контуров

`private-archive/` и `data/private/` в `.gitignore`; `tools/release/build_public_site.py` запрещает `private-archive`, `data/private`, `data/research/benoist`, `research`; тесты `tests/test_public_boundary.py` проверяют, что каждая картинка книги заявлена как открытая, что workflow не копируют личные пути и что скрипт отказывается работать в CI.

## Проверки

- PASS: `ruff check tools tests`, `pytest -q tests` (351), CI `Then/Now responsive Chromium` и `Sources, catalog, image geometry` на `bdfcd1d`.
- PASS (Chromium, 320/390/1280): `tests/browser/qa_book.js` (87 проверок), `qa_first_impression.js`, `qa_compare.js`, на собранном публичном сайте тоже.
- NOT TESTED: iPhone/iPad Safari, 820 px для новых страниц книги (реестр, лист, места), реальное чтение живого сайта глазами.
