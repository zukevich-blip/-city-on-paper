# Карта источников и коннекторы (Issue #6, PR A) — 01.11.2026

Статус: **только исследование и инструменты.** Выставка не тронута, в `main` ничего не вливается. Исходник выставки по-прежнему **BLOCKED** (#1): бандла `city-on-paper-2026-10-29.bundle` и коммитов `ae296cbc…` / `1f975375…` в GitHub нет.

Все результаты ниже получены из облачного контейнера Claude Code через egress-прокси 01.11.2026. Из другой сети ответы могут отличаться: например, Gallica отдаёт 403 именно этому контейнеру.

## 1. Что в этом PR

| Файл | Назначение |
|---|---|
| `tools/sources/connectors.py` | 9 коннекторов поиска + Panoramax (современные фото) + Wikidata (только сверка личностей). Только stdlib. Кэш на диске, пауза по хосту, бюджет запросов, честный журнал ошибок; ключи API вырезаются из выгрузки |
| `tools/sources/identity.py` | подсказки для различения Félix / Philippe / Guillaume Philippe / Antoine Benoist (это подсказка, не атрибуция) |
| `tools/sources/harvest.py` | воспроизводимый сбор → JSON + CSV + ошибки провайдеров |
| `tools/sources/probe.py` | один GET на каждый маршрут, без повторов и обходов → `data/providers/probe-2026-11-01.json` |
| `tools/sources/queries.json` | план запросов первого шага (FR / IT / PL / EN, исторические написания: Wilna, Wilno) |
| `schemas/artwork.schema.json` | схема каталожной записи (раздел 4 Issue #6) |
| `data/candidates/candidates-2026-11-01.{json,csv}` | **333 реальные записи метаданных из 45 учреждений** (9 провайдеров) |
| `data/candidates/food-culture-shortlist-2026-11-01.json` | 22 кандидата «рынки / кафе / меню» из 7 учреждений, заголовки прочитаны вручную |
| `tests/test_sources.py` | 24 офлайн-теста (без сети); после обновления 2 — 53 |

## 2. Матрица провайдеров (28 маршрутов, 21 учреждение / сервис)

PASS — маршрут ответил JSON и реально дал записи в сборе. Код — HTTP-статус пробы.

| # | Провайдер | Маршрут | Ключ | Проба 01.11 | В сборе | Права (гранулярность) |
|---|---|---|---|---|---|---|
| 1 | **The Met** | `collectionapi…/v1.1/search` + `/v1/objects/{id}` | нет | **PASS** 200; старый `/v1/search` → **410 Gone** | 18 | `isPublicDomain` по объекту → CC0; остальное — только метаданные |
| 2 | **Art Institute of Chicago** | `api.artic.edu/api/v1/artworks/search` | нет, но обязателен заголовок `AIC-User-Agent` | **PASS** 200 с заголовком; **403 без него** | 27 | `is_public_domain` по объекту; изображения PD — CC0, IIIF Image API 2 |
| 3 | **Cleveland Museum of Art** | `openaccess-api.clevelandart.org/api/artworks/` | нет | **PASS** 200 | 8 | `share_license_status` = CC0 по объекту |
| 4 | **Europeana** (агрегатор: BnF/Gallica, Marciana, Biblioteka Narodowa, LNDM, Deutsche Fotothek…) | `api.europeana.eu/record/v2/search.json` | демо-ключ `api2demo` работает; для объёма нужен свой бесплатный ключ (`EUROPEANA_API_KEY`) | **PASS** 200 | 162 (из 37 учреждений) | `rights` по записи: rightsstatements.org / CC. BnF — в основном **NoC-OKLR** (коммерческое использование по условиям Gallica) |
| 5 | **Library of Congress** | `loc.gov/photos/?fo=json&at=results,pagination`; права — `item.rights_advisory` (уже есть в выдаче P&P) или `loc.gov/item/{id}/?fo=json&at=item` | нет | **PASS** 200; `…/item/{id}/?fo=json&at=item` → 200; `…/item/{id}/manifest.json` → **403** | 63 → **206** (обновление 2) | `rights_advisory` по предмету (P&P). «No known restrictions on publication» → `open`; «Publication may be restricted» → `restricted`; «Rights status not evaluated» и предметы без advisory (World Digital Library) → `unknown` |
| 6 | **Rijksmuseum** (Linked Art, data services 2025+) | `data.rijksmuseum.nl/search/collection?creator=` + `id.rijksmuseum.nl/{id}` | нет | **PASS** 200 | 12 | Public Domain Mark / CC0 по цифровому объекту, IIIF через `iiif.micr.io` |
| 7 | **Victoria and Albert Museum** | `api.vam.ac.uk/v2/objects/search` | нет | **PASS** 200 | 4 | изображения V&A — некоммерческие условия (не CC) → `restricted`, только ссылки |
| 8 | **Wikimedia Commons** | `w/api.php` generator=search + `imageinfo/extmetadata` | нет | в сборе **PASS**; в пробе через 40 минут → **429** | 38 | по файлу; права на произведение, скан и фото надо читать на странице файла |
| 8a | **Wikimedia Commons, категории-альбомы** (обновление 2) | `w/api.php` generator=categorymembers (ns 6) + `imageinfo/extmetadata`, с продолжением `gcmcontinue` | нет | **PASS** для 3 категорий; `Category:Philippe Benoist` → **429** три запуска подряд | 128 | как у Commons; членство в категории ≠ атрибуция |
| 9 | **Smithsonian Open Access** | `api.si.edu/openaccess/api/v1.0/search` | `DEMO_KEY` — сильный лимит; нужен ключ api.data.gov (`SI_API_KEY`) | в сборе 200; в пробе → **429** | 1 | `usage.access` = CC0 по медиафайлу |
| 10 | **Panoramax** (современные уличные фото) | `api.panoramax.xyz/api/search?bbox=` (STAC) | нет | **PASS** 200 | — (для пар) | по снимку: CC-BY-SA-4.0 / etalab-2.0; есть азимут, дата, автор |
| 11 | **Wikidata** (только сверка личностей и мест) | `wbsearchentities`, `wbgetentities`, SPARQL | нет | SPARQL 200; `wbsearchentities` в пробе → 429 (в работе 200) | — | CC0 |
| 12 | **BnF Gallica** | SRU, IIIF `info.json` | нет | **FAIL 403** (Cloudflare) на оба маршрута | — | условия Gallica: некоммерческое использование бесплатно, коммерческое — по лицензии. **Записи Gallica доступны через Europeana** (36 записей BnF в сборе) |
| 13 | **Getty** (Open Content) | `data.getty.edu/museum/collection/…` | нет | **FAIL**: ошибка TLS (`unable to get local issuer certificate`) из контейнера; `www.getty.edu` — 200, но это HTML | — | Open Content — CC0 для изображений PD. Проверить из браузера владельца |
| 14 | **NYPL** | новый `api-collections.nypl.org` (документация 200); старый `api.repo.nypl.org` | новый API — нужен токен (не проверено) | docs 200; старый API → **401** | — | NYPL Menus — главный кандидат для меню; нужен токен и проверка условий |
| 15 | **Harvard Art Museums** | `api.harvardartmuseums.org/object` | **нужен ключ** | 401 | — | по объекту |
| 16 | **DPLA** | `api.dp.la/v2/items` | **нужен ключ** | 403 | — | по записи (агрегатор США) |
| 17 | **British Library** | `api.bl.uk` | — | **FAIL**: прокси отказал в соединении (502), хост закрыт для этой сессии | — | не проверено |
| 18 | **Deutsche Digitale Bibliothek** | `api.deutsche-digitale-bibliothek.de/2/search…` | ключ (по документации) | 500 | — | не проверено |
| 19 | **ÖNB** (Австрийская национальная библиотека) | `iiif.onb.ac.at` | — | **FAIL**: connection reset | — | часть фондов доступна через Europeana |
| 20 | **Polona** (Biblioteka Narodowa) | `polona.pl/api/` | — | 404 (маршрут не тот) | — | 9 записей BN уже пришли через Europeana |
| 21 | **ETH-Bibliothek, Bildarchiv** | `ba.e-pics.ethz.ch` | — | 200, но HTML (портал, не API) | — | не проверено |

**Итог по критерию Issue #6:** изучены 21 учреждение / сервис (нужно ≥ 12); **рабочих маршрутов поиска метаданных — 9** (Met, AIC, Cleveland, Europeana, LoC, Rijksmuseum, V&A, Commons, Smithsonian) плюс Panoramax и Wikidata (нужно ≥ 5). Commons и Smithsonian работают **с ограничением частоты**.

## 3. Оценка качества источников (суждение Claude, 1–5)

| Провайдер | Авторитет | Разрешение | Стабильность доступа | Ясность прав | Охват XIX в. (города) | Точность гео | Приоритет |
|---|---|---|---|---|---|---|---|
| Europeana → BnF / Marciana / BN / LNDM | 5 | 4 (IIIF у держателя) | 4 | 4 | **5** | 2 | **1** — основной путь к Gallica и европейским альбомам |
| Library of Congress (P&P) | 5 | 5 | 4 | 3 | 4 (Ph. Benoist, Lemercier) | 2 | **1** |
| Rijksmuseum | 5 | 5 (IIIF) | 4 | 5 | 3 | 1 | 2 |
| Wikimedia Commons | 2 (агрегатор) | 4 | 2 (429) | 3 | 4 | 3 (GPS у фото) | 2 — после сверки с держателем |
| Met / AIC / Cleveland | 5 | 5 | 5 | 5 | 2 (мало видов городов) | 1 | 3 |
| V&A | 5 | 5 | 5 | 2 (некоммерческие условия) | 3 | 1 | 3 — только ссылки |
| Panoramax | 3 | 4 | 4 | 5 | — (современные) | **5** (азимут) | 1 для фото «сейчас» |
| Gallica напрямую | 5 | 5 | **1 из облака** | 4 | 5 | 2 | после проверки из браузера владельца |

## 4. Найденные ошибки и ловушки

1. **Нерелевантная выдача.** AIC по `q=Benoist` вернул 24 работы, и ни в одной нет Benoist (Walter Shirlaw и др.). Cleveland по тому же запросу вернул Le Pautre. Прототип из PR #5 записал бы их как кандидатов. Теперь запись сохраняется, только если все токены запроса есть в её собственных полях; по фамилии ищется только в поле автора. Отброшено как нерелевантное: 181 запись (см. `counts.dropped_as_irrelevant`).
2. **Met `/v1/search` — 410 Gone**, работает `/v1.1/search` (так и было в PR #5, подтверждено).
3. **AIC без `AIC-User-Agent` → 403.** Это документированное требование AIC, а не обход защиты. В PR #5 заголовка не было, поэтому AIC там не работал бы.
4. **Личности Бенуа** (Wikidata, 01.11):
   - Félix Benoist — **Q277187**, 1818–1896, ULAN 500104203.
   - Philippe Benoist — **Q26309223**, 1813 – 1896 по Wikidata. У LoC и Commons «около 1905», у BnF через Europeana «1813–1905» → **конфликт дат**.
   - Guillaume Philippe Benoist — **Q5616064**, гравёр XVIII века. У Wikidata годы 1725–1770, у Met 1725–1800 → **конфликт**.
   - Antoine Benoist — **Q18526511** (1721–1770), отдельный человек.
   - **Исправление к PR #3:** Q117312510 — композитор эпохи Возрождения, **а не дубль** Филиппа Бенуа.
   - Метка «P. Benoist, French, 18th century» у Met — `uncertain`: возможно, Guillaume Philippe.
5. **Омонимы «Benoist»** в Europeana: портреты Benoist-Méchin (это сюжет, не автор), Benoist J.-L. (гравёр). Поиск по полю автора их отсекает.
6. **Тематические ключевые слова — только подсказка.** Пример: французское «marche» (марш, ходьба) против «marché» (рынок). Ложные срабатывания: «Market Street», «coffee pot». Сюжеты «невольничьего рынка» исключены из «food culture» и помечены как требующие отдельного кураторского решения.
7. **Записи 1994–2026 годов** (фото LoC) попадают в выдачу. Это не исторические работы, но их можно использовать как источники «сейчас».

## 5. Счётчики (из `candidates-2026-11-01.json`)

- **333** записи, **45** учреждений, 9 провайдеров. Дубли по `provider:id` объединены. Межпровайдерные возможные дубли помечены `possible_duplicates` — это только подсказка, не утверждение идентичности.
- Права:
  - `open` — 119;
  - `restricted` — 165 (только метаданные и ссылка, `preview_url` пуст);
  - `unknown` — 49 (в основном LoC: rights advisory не входит в выдачу поиска).
- Подсказки по личностям Бенуа:
  - Philippe — 30;
  - Guillaume Philippe — 24;
  - Antoine — 14;
  - Félix — 11;
  - Félix + Philippe — 6 (*Rome dans sa grandeur*);
  - uncertain — 2;
  - другие или неясные Benoist — 13.
- Ключевые слова тем: `food_market` 47, `cafe_restaurant` 84, `architecture` 51, `city_view` 84, `square_street` 52. Вручную отобраны **22** исторические записи о еде, рынках, кафе и меню из 7 учреждений: BnF (меню 1894 и 1895, Писсарро «Marché à Pontoise» 1895), LoC (рыбный рынок в Кантоне 1856, кафе Парижа 1889–1903), AIC, Cleveland («Café des Ambassadeurs», Дега, 1877–78), IMAGO (рынок в Невшателе, 1859), Chester Beatty, Museu Marès.
- **Ни одна запись не одобрена.** У всех `status.*` = `candidate` / `not_checked`, `published: false`. Байты изображений не скачивались и в git не добавлены.

## 6. Воспроизведение

```sh
python3 -m pip install pytest==9.1.1 ruff==0.16.9   # только для проверок; харвестеру зависимости не нужны
ruff check tools tests && pytest -q                 # офлайн, без сети
python3 -m tools.sources.probe --out data/providers/probe-$(date +%F).json
python3 -m tools.sources.harvest --plan tools/sources/queries.json \
    --out data/candidates/candidates-$(date +%F) --cache .cache/sources --budget 450 --delay 1.0
# повтор из кэша, без сети:
python3 -m tools.sources.harvest --plan tools/sources/queries.json \
    --out data/candidates/candidates-2026-11-01 --cache .cache/sources --offline
```
Кэш `.cache/` в git не входит. Необязательные ключи: `EUROPEANA_API_KEY`, `SI_API_KEY`. Без них используются публичные демо-ключи.

## 7. Нужно решение или действие владельца

1. **Бандл или экспорт выставки** для #1 — без него миграция остаётся BLOCKED.
2. **Бесплатный ключ Europeana** (сейчас работаем на демо-ключе) и, по желанию, ключи api.data.gov (Smithsonian), Harvard и DPLA.
3. **Gallica и Getty** — проверить из браузера владельца. Из облака: Gallica 403, у Getty ошибка TLS. Ничего не обходилось.
4. **NYPL Menus**: нужен токен нового API и проверка условий. Старый API закрыт 01.08.2026 (проба: 401).
5. Политика для BnF **NoC-OKLR** (некоммерческий показ или лицензия) и для изображений V&A (только ссылка).

## 8. Обновление 2 (консилиум: источники) — 01.11.2026, вечер

Новый файл: `data/candidates/candidates-2026-11-01b.{json,csv}`. Старый `candidates-2026-11-01.*` не тронут.
Сбор шёл тремя живыми запусками (156 + 11 + 4 = **171 запрос** харвестера; плюс около 15 ручных проб curl). Пауза 1 с, для `commons.wikimedia.org` — 6 с. Повтор из кэша (`--offline`) дал тот же набор id.

**Счётчики (из `counts` файла):**
- **1019** записей из **117** учреждений, 8 провайдеров + категории Commons. По провайдерам: Europeana 604, LoC 206, Commons 132, AIC 35, Met 18, Rijksmuseum 12, Cleveland 8, V&A 4.
- Права: `open` 506, `restricted` 481, `unknown` 32.
- **LoC:** 206 записей. У 171 права взяты из `rights_advisory` самого предмета: 116 `open`, 58 `restricted`. Ещё 32 остались `unknown`:
  - 23 предмета World Digital Library: advisory на уровне предмета нет, записано «no rights advisory on item». Текст коллекции сохранён в `rights_collection_note`, но как лицензия не используется.
  - остальные — «Rights status not evaluated».

  Запрос `item/{id}/?fo=json&at=item` сделан для всех 32 `unknown`: ни один не перешёл в `open`. Из 49 LoC-записей, которые в старом файле были `unknown`: 20 → `open`, 8 → `restricted`, 21 остаются `unknown`.
- **Темы (ключевые слова, только подсказка):** `food_market` 162, `cafe_restaurant` 150, `city_view` 407, `architecture` 191, `square_street` 204.
- **Подсказки Бенуа:**
  - Félix — 62;
  - Philippe — 28;
  - Félix + Philippe — 25;
  - Guillaume Philippe — 5;
  - Antoine — 12;
  - uncertain — 4;
  - другие — 14;
  - **`category_only_not_attribution` — 23**: файл лежит в категории Бенуа, но в поле Artist Бенуа нет.

**Новые маршруты и запросы:**
- исторические и местные названия: Rome dans sa grandeur / Roma, Venezia / Venise / Venice, Napoli / Naples, Firenze / Florence, Saint-Pétersbourg / Петербург / St. Petersburg, Wilno / Вильна / Vilnius / Wilna, Nantes et la Loire-Inférieure, Bretagne contemporaine (LoC), Lisboa / Lisbon, Praha / Prague, Kraków / Cracovie, Constantinople / İstanbul;
- рынки, кафе и меню: Les Halles, marché aux fleurs, mercato, Marktplatz, rynek, caffè, Kaffeehaus, kawiarnia, menu dîner, Speisekarte, bill of fare, fish market.

**Защита от омонимов:** поле `exclude` в плане. LoC отдаёт St. Petersburg во Флориде, Lisbon в Нью-Гэмпшире и Wilna в Мэриленде; 17 таких записей отброшено (`counts.dropped_as_homonym_place`). Даже после фильтра часть фото XX века (например, Lisbon 1946) остаётся в выдаче: это источники для «сейчас» или промежуточного периода, а не литографии.

**Категории Commons** (имена проверены через `prop=categoryinfo`):
- `Category:Félix Benoist` — 63 файла;
- `Category:La Bretagne contemporaine` — 46 файлов (44 записаны с этой категорией; 2 файла уже попали в набор раньше, из категории Félix Benoist или поиска, и в поле `commons_category` у них первая категория);
- `Category:Paris dans sa splendeur` — 22 файла (21 записан с этой категорией, 1 уже был в наборе);
- `Category:Philippe Benoist` — 160 файлов. Существует, но **не собрана**: три запуска подряд получили 429.

Категорий `Album de Wilna`, `Rome dans sa grandeur`, `Nantes et la Loire-Inférieure` и `Guillaume Philippe Benoist` на Commons **нет** (`missing`). Поиск подходящих имён категорий упёрся в 429. Подсказка о личности считается **только** по полю Artist самого файла. Поэтому гравюры Guillaume Philippe Benoist из категории Philippe не становятся работами Philippe.

**Дедупликация (только подсказки, записи не сливаются):**
- `identifiers` — номера LoC: `lc-repro:lc-dig-pga-14314`, `lc-hdl:pga.14314`, `lccn:…`. Берутся из полей LoC и из описания или Credit файла Commons.
- нормализованное название + фамилия автора;
- старый хэш «название + автор + дата». Голое название без автора и даты («Istanbul», «Menu») больше не считается дублем.

В этом сборе межпровайдерная связь одна: BnF (Europeana) ↔ Commons, «Pavillon du Louvre» из *Paris dans sa splendeur*. Связей LoC ↔ Commons по номеру репродукции — **0**: файлы Commons, которые ссылаются на LoC, лежат в непрочитанной категории Philippe Benoist. Механизм покрыт тестами на фикстурах.

**Ошибки провайдеров в этом сборе:**
- Commons — 429 (`Philippe Benoist`: поиск и категория). `Retry-After` 35–56 с; при паузе больше 30 с запрос больше не повторяется.
- Smithsonian `DEMO_KEY` — 429, `Retry-After` 1966–72725 с.
- Met — в первом запуске 403 на `market lithograph`, во втором 200.
- Wikidata — 429 при попытке проверить Q2853671.

**Исправления по ревью (SHA b413124):**
1. Panoramax: лицензия классифицируется через `rights_category`. CC-BY-NC-SA теперь `restricted`, а не `open`.
2. Кэш: перед записью удаляются поля `apikey` / `wskey` / `token`, а в строках вырезаются `wskey=` и `utm_campaign=`. Europeana повторяет ключ в `utm_campaign` каждого `guid`. Существующий кэш перечищен.
3. LoC: автор берётся из `contributor_names` (регистр и даты как в каталоге), а не из фасета в нижнем регистре. Права — по предмету, без общей заглушки. Если advisory нет — `unknown` с текстом «no rights advisory on item».
4. Antoine Benoist с датой раньше 1735 года или с годом 16xx в имени → `uncertain`. LoC имеет в виду Antoine Benoist 1632–1717, а не Q18526511 (1721–1770). QID Q2853671 взят из ревью и **не перепроверен**: Wikidata ответила 429.
5. HTTP: при `Retry-After` больше 30 с — сразу `ProviderError` без сна.
6. `rights_category`: «InC», «InC-EDU» без URI и «Attribution-NonCommercial» → `restricted`.

```sh
ruff check tools tests && python3 -m pytest -q tests          # 53 passed
python3 -m tools.sources.harvest --plan tools/sources/queries.json \
    --out data/candidates/candidates-2026-11-01b --cache .cache/sources --budget 420 --delay 1.0
python3 -m tools.sources.harvest --plan tools/sources/queries.json \
    --out /tmp/check --cache .cache/sources --offline          # 1019, 0 requests
```
