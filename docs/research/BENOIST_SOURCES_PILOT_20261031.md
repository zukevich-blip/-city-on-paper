# Литографии Бенуа: источники, первые пары, стек и схема (31.10.2026)

**Автор:** Claude Code, независимый аудит. Только исследование: код выставки не создаётся, пока по Issue #1 не восстановлен исходник.

## 1. Состояние репозитория
- **`main` @ 1c541f0:** `README.md` и `MIGRATION.md`. MIGRATION ссылается на `city-on-paper-2026-10-29.bundle` у владельца и на коммиты `ae296cbc…` (база) и `1f975375…` (функции). **В GitHub этих коммитов нет**: запрос `commits/<sha>` возвращает 422.
- **PR #2 (черновик):** только правила — `.claude/skills/city-source-and-visual-qa/SKILL.md` и `docs/ECC_LITE_ART_MIGRATION_20261030.md`. Сохраняем как есть.
- **Исходной выставки в GitHub нет:** ни изображений, ни каталога, ни пар, ни настроек совмещения. **Восстановление = BLOCKED.** Нужно одно из трёх:
  - (a) `.bundle` — проверить `git bundle verify` и sha256;
  - (b) экспорт Google Sites (Takeout);
  - (c) ссылка на живой сайт.

## 2. Источники (проверено запросами 31.10)

| Источник | Без ключа | Права | Что видно |
|---|---|---|---|
| Wikimedia Commons API (`categorymembers`, `imageinfo`+`extmetadata`, `geosearch`) | да; часто отвечает 429 — нужны пауза и User-Agent | по файлу: старые листы — PD, фото — CC BY-SA, CC BY, CC0 | Category:Philippe_Benoist — 163 файла, Category:Félix_Benoist — 50+ |
| Wikidata SPARQL | да | CC0 | Félix Benoist Q277187; Philippe Benoist Q26309223 (есть дубль Q117312510) |
| Gallica SRU / IIIF | **403 (Cloudflare) из облака** | BnF: некоммерческое использование бесплатно, коммерческое — по лицензии | перепроверить из браузера владельца |
| Europeana Search API | нужен бесплатный ключ (демо-ключ `api2demo` работает) | поле `rights` у каждой записи | по Félix Benoist 41 запись: BnF — NoC-OKLR, Hertziana «Rome dans sa grandeur» — InC |
| LoC IIIF `tile.loc.gov/image-services/iiif/…` | да | «No known restrictions on publication» | `…/manifest.json` отвечает 403, работает `?fo=json` |
| Mapillary Graph API | **нет**, нужен бесплатный токен | CC BY-SA 4.0 (по документации, не проверено) | — |
| Panoramax STAC `api.panoramax.xyz/api/search?bbox=` | да | у каждого снимка: CC-BY-SA-4.0 или etalab-2.0 | есть азимут, дата, автор |

**Риски атрибуции:**
- В Category:Philippe_Benoist попадает гравёр XVIII века **Guillaume Philippe Benoist**. Категорию **никогда не импортировать целиком**.
- Дата смерти Филиппа расходится: 1896 у Wikidata, ок. 1905 у Commons и LoC.
- Парижские «compositions rétrospectives» — реконструкции, а не натура. Помечать `is_retrospective`.

## 3. Кандидаты в первые пары
Лицензии и координаты проверены; **совпадение ракурса ещё НЕ проверено глазами**.
1. **Вильнюс, Большой двор университета.**
   - Лист: `File:Vilnia,_Universyteckaja,_Vialiki_Dvor._…_(P._Benoist,_1850).jpg` — PD, Ph. Benoist и A. Bayot, *Album de Wilna*, 3086×3906.
   - Фото: `File:Vilnius_University_Great_Courtyard_1,_Vilnius,_Lithuania_-_Diliff.jpg` — CC BY-SA 3.0, 54.682671/25.287236.
2. **Вандомская колонна с улицы Кастильоне.**
   - Лист: `File:Colonne_Vendôme_vue_de_la_rue_de_Castiglione.jpg` — PD, 1862, Gallica bpt6k5606784d/f37.
   - Фото: `File:Castiglione_12.jpg` (CC BY-SA 4.0) или `File:Colonne_Vendôme_(1).jpg` (CC BY-SA 3.0).
3. **Мадлен, Париж.**
   - Лист: `File:Paris._La_Madeleine_-_Ph._Benoist_del._;_Imp._Lemercier,_Paris._LCCN2016652452.jpg` — LoC, без ограничений.
   - Фото: НЕ НАЙДЕНО.
4. **Замок Шатобриан (Félix Benoist, *Nantes et la Loire-Inférieure*, 1850).**
   - Лист: `File:Chateau_chateaubriant_1850.jpg` — PD, всего 757×521, нужен лучший скан.
   - Фото: Panoramax `35d528a6-e392-4ed8-9a68-6659ca0cf816` (CC-BY-SA-4.0).
5. **Римский форум, «Campo Vaccino» (*Rome dans sa grandeur*, 1865).** Скан слабый (730 px), фото не найдено.

**Не годятся для точных пар:** Porto di Ripetta (снесён в 1890-х) и устье Эрдре в Нанте (засыпано).

## 4. Минимальный стек (лицензии сверены по файлам LICENSE)
- **В браузере, с CDN, без сборки:**
  - Leaflet 1.9.4 (BSD-2) — карта;
  - OpenSeadragon 6.1.1 (BSD-3) — увеличение и IIIF, второй слой для полупрозрачного наложения;
  - img-comparison-slider 8.0.7 (MIT) — «было / стало».
- **Совмещение:** сохранённая гомография применяется как CSS `matrix3d`. Изображения не перезаписываются.
- **OpenCV (Apache-2.0)** — только офлайн: `findHomography` по 4–8 контрольным точкам, RMS-ошибка, проверка H·H⁻¹.
- **Отложены:**
  - Mirador — тяжёл для пилота;
  - MapLibre — нужен источник векторных тайлов;
  - Leaflet.DistortableImage — LICENSE BSD-2, а package.json MIT; не обновлялся с 2022.

## 5. Схема записи пары (один JSON на пару; оригиналы не меняются)
```json
{"id":"vilnius-vu-great-courtyard","status":"candidate|verified|uncertain",
 "work":{"title_original":"","artist":{"name":"Philippe Benoist","wikidata":"Q26309223","role":"del. & lith."},
  "co_artists":[{"name":"Adolphe Bayot","role":"figures"}],"album":"Album de Wilna","plate":null,"date":"1850",
  "holding":{"institution":"","shelfmark":""},"source":{"page_url":"","iiif_manifest":null,"file_sha256":""},
  "rights":{"statement":"","uri":"","checked":"2026-10-31"},"is_retrospective":false},
 "place":{"name":"","wikidata":"","lat":0,"lon":0,"geo_confidence":"exact|street|approx"},
 "photo":{"page_url":"","author":"","date":"","licence":"","licence_uri":"","attribution":"","lat":0,"lon":0,"azimuth":null,"file_sha256":"","source":"commons|panoramax"},
 "viewpoint":{"confidence":"high|medium|low|mismatch","observations":[],"evidence_urls":[],"reviewer":"","date":""},
 "alignment":{"type":"homography","maps":"photo->lithograph pixels","H":[[1,0,0],[0,1,0],[0,0,1]],"H_inverse":[[1,0,0],[0,1,0],[0,0,1]],
  "control_points":[{"litho":[0,0],"photo":[0,0],"label":""}],"rms_px":null,"tool":"opencv findHomography",
  "derived_label":"Совмещённый показ, не документ"}}
```

## 6. План пилота
1. Владелец присылает bundle, экспорт или ссылку. Сверяем sha256, импортируем в ветку `claude/restore-*`, составляем опись работ и пар со скриншотами. До этого — BLOCKED в Issue #1.
2. Только при необходимости: бесплатные ключ Europeana и токен Mapillary. Gallica — проверить из браузера владельца.
3. Реестр источников для пар 1–4, лучший скан из держателя (LNDM, Gallica, LoC).
4. Ракурс проверяется глазами по общим ориентирам. Нет уверенности — статус `uncertain`.
5. Контрольные точки, H через OpenCV офлайн, порог RMS, обратимость.
6. Статическая страница Leaflet + OpenSeadragon + слайдер, у каждой пары лицензии.
7. QA: 375 px, iPad, десктоп, reduced motion. Итог: PASS / FAIL / NOT TESTED.
8. Черновой PR, решение владельца.

**НЕ ПРОВЕРЕНО:**
- Gallica (закрыта из облака);
- фото для Мадлен и Форума;
- совпадение ракурсов;
- лицензия Mapillary;
- листы с видами Санкт-Петербурга.
