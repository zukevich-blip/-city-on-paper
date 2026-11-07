# Город на бумаге 2.0 — технологическая матрица (Frontend/GIS + performance)

Роль: Frontend/GitHub Pages и performance-инженер (Issue #34, разделы 2, 5, 6). Это субагент Claude Code, а не человек-эксперт. Всё ниже проверено 2026-11-07 реальными запросами и прогонами Playwright, если явно не помечено «НЕ ПРОВЕРЕНО».
Сырые данные лежат в `probe.json` (URL, HTTP-статусы, байты, gzip, SHA-384, логи Playwright). Тестовые страницы `t-*.html`, скриншоты в `shots/`.

Среда: Playwright 1.63.0 со встроенным Chromium (headless, SwiftShader WebGL). Режим без WebGL запускался с флагами `--disable-webgl --disable-webgl2 --disable-gpu`. Локальный сервер `scripts/serve.py` — это `http.server` с поддержкой HTTP Range на 127.0.0.1:8790. Обычный `python3 -m http.server` не умеет Range, а GitHub Pages умеет: проверено, `206`, `accept-ranges: bytes`, `cache-control: max-age=600`.

## 1. Матрица

Размер gzip — это `gzip -9` от точного файла, скачанного с jsDelivr. Хэши SHA-384 совпали с unpkg: проверено для leaflet.js и maplibre-gl.mjs.

| # | Технология (версия, дата выпуска) | Что делает → где у нас | Лицензия (по файлу LICENSE) | Цена / лимиты | Файл: байт / gzip | Тест | Вердикт |
|---|---|---|---|---|---|---|---|
| 1 | **MapLibre GL JS 6.15.0** (2026-10-18; на 20 дней старше «сегодня») | Векторная карта на WebGL2: режим «точная карта города», слои эпох (OHM), Allmaps | BSD-3-Clause (LICENSE.txt включает и BSD-3 Mapbox для кода ≤ v1.13) | бесплатно | `maplibre-gl.mjs` 1 098 062 / **292 144**; `maplibre-gl-worker.mjs` 518 806 / **147 120**; `.css` 71 596 / 10 191 | ✅ PMTiles и OpenFreeMap отрисованы (`shots/maplibre-pmtiles-local.png`, `maplibre-ofm-cdn.png`, `maplibre-390.png`); ❌ без WebGL — см. §3 | **ВНЕДРЯТЬ**, но только с проверкой WebGL2 и запасным режимом |
| 1a | ⚠ Важно про v6 | Версия 6 поставляется **только как ESM** (`.mjs` и отдельный module-worker); UMD `maplibre-gl.js` в 6.x нет (404). Последний UMD — 5.24.0 (1 056 837 / 275 161) | — | — | — | ESM по CDN с SRI через `importmap.integrity`: работает, неверный хэш блокируется (`shots/sri_negative.json`). Копия в репозитории с именами `.js` и `setWorkerUrl()`: работает (`shots/maplibre-localjs.png`) | Класть в репозиторий как `.js` |
| 2 | **Leaflet 1.9.4** (2023-05-18) | Лёгкая 2D-карта на DOM/Canvas без WebGL: «карта-портал» (старинная карта в `CRS.Simple`), запасной режим | BSD-2-Clause | бесплатно | `leaflet.js` 147 552 / **42 434**; `.css` 14 806 / 3 522 | ✅ портал с WebGL и без него (`leaflet-portal*.png`); ✅ запасной режим (`maplibre-nowebgl-fallback.png`) | **ВНЕДРЯТЬ** как портал и запасной режим |
| 2a | protomaps-leaflet 5.1.0 (2025-06-18) | Рисует векторный PMTiles в Leaflet через Canvas 2D, без WebGL | BSD-3-Clause | бесплатно | 128 171 / **37 642** | ✅ тот же `paris-z14.pmtiles` без WebGL | **ВНЕДРЯТЬ** для запасного режима |
| 3 | OpenLayers 10.11.0 (2026-10-04) | Полноценная GIS-библиотека, ImageStatic, проекции | BSD-2-Clause | бесплатно | `ol.js` 1 070 771 / **297 882** (полный UMD) | ✅ ImageStatic (`shots/ol.png`) | **НЕТ** для пилота: тяжелее Leaflet в 7 раз и не даёт нужного нам сверх MapLibre и Leaflet |
| 4 | **OpenSeadragon 6.1.1** (2026-09-09) | Глубокое увеличение оригиналов; IIIF Image API (`info.json`) | BSD-3-Clause | бесплатно | `openseadragon.min.js` 352 735 / **87 190** | ✅ IIIF Image API 2 (Digital Commonwealth): `drawer=webgl`; **без WebGL сам переключился на `drawer=canvas`** (`osd-iiif*.png`) | **ВНЕДРЯТЬ** для литографий и карт |
| 5 | **Allmaps**: @allmaps/maplibre 1.0.0-beta.44, @allmaps/leaflet 1.0.0-beta.55 (2026-09-22) | Трансформирует IIIF-карту по Georeference Annotation (расширение IIIF georef) прямо в браузере, через WebGL2 | MIT (LICENSE.md) | бесплатно; annotations.allmaps.org отдаёт `200`, `ACAO *` | В npm только ESM с «голыми» импортами; через jsDelivr `+esm` вышло ~347 КБ трафика за 40 запросов (zod, @allmaps/render и др.). **jsDelivr прямо пишет: SRI для `+esm` не использовать** | ✅ пример из документации (`maps/2d49b3ecd1ba6346`, Гент) трансформирован клиентом поверх MapLibre 6.15 (`allmaps-maplibre.png`); ✅ серверные растровые тайлы `allmaps.xyz/maps/{id}/{z}/{x}/{y}.png` в Leaflet **без WebGL** (`leaflet-allmaps-xyz-nowebgl.png`) | **МОЖНО** (пакеты в бете): клиентская трансформация только при WebGL2, без WebGL — растровые тайлы. Для продакшена положить сборку в репозиторий |
| 6 | Тайлы: см. §2 | — | — | — | — | — | — |
| 7 | **Panoramax** API + @panoramax/web-viewer 5.3.1 | Современные уличные снимки по bbox; `assets.thumb/sd/hd`; лицензия у каждого снимка своя | Просмотрщик — MIT. Снимки: в тестовых выборках только CC-BY-SA-4.0 и etalab-2.0 | бесплатно, без ключа | Модуль photoviewer 1 601 740 / **521 717** (cjs) | ✅ `/api/search?bbox=` → 200, thumb → 200. Охват: Нотр-Дам 100+ снимков (87 CC-BY-SA-4.0, 13 etalab-2.0; 30 панорам 360°), Дуомо Флоренции 13, набережная Неаполя 5 (2018 г.) | **ВНЕДРЯТЬ API** (превью с подписью и лицензией, ссылка на снимок); **встраивать просмотрщик — НЕТ** (0,5 МБ gzip). Встраивание не проверялось |
| 8 | Изображения: AVIF/WebP/JPEG (Pillow 12.3.0) | Превью литографий и фото | — | офлайн | см. §5 | ✅ | **ВНЕДРЯТЬ** AVIF + WebP + JPEG через `<picture>` |
| 9 | Service Worker / PWA | Офлайн для одного города | — | Квота Chromium в тесте ≈3–4 ГБ; `persisted=false` | `sw.js` ≈1,6 КБ | ✅ закэшировал оболочку и `paris-z14.pmtiles`, карта отрисована **офлайн** (`pwa-offline-maplibre.png`); Range отдаётся нарезкой из кэша | **МОЖНО** (после пилота) |
| 10a | Tesseract 5.3.4 (Apache-2.0) | OCR легенд и надписей | Apache-2.0 | офлайн | — | ✅ легенда «EXPLANATION» на карте Гента: распознано примерно 50 % слов («S#Wicolas», «Couvent de Doorseele», «Theresiennes»); курсив гравюры распознаётся плохо | **МОЖНО** как подсказка для поиска; всегда нужна ручная выверка |
| 10b | imagehash 4.3.2 (BSD-2) | pHash для поиска дубликатов | BSD-2-Clause | офлайн | — | ✅ оригинал и перекодированный WebP-960: расстояние **0**; несвязанное фото: 30; зеркальная копия: 32 | **ВНЕДРЯТЬ** в каталожный валидатор |
| 10c | OpenCV 4.10 ORB (Apache-2.0; ORB без патентов; SIFT в основной OpenCV с 4.4, патент истёк в 2020) | Подсказка о совпадении ракурса | Apache-2.0 | офлайн | — | ✅ два соседних кадра Panoramax: 37 RANSAC-инлайеров; контроль «панорама против карты»: 8 | **МОЖНО** только как подсказка; дистанция 37 против 8 слишком мала для автоматического решения. Никаких автоматических «совпадений» (п. 6 Issue) |
| — | OHM maplibre-gl-dates 2.0.0 (2026-10-21) | Фильтрует векторный стиль OHM по дате | CC0-1.0 (npm) | бесплатно | 7 316 / 2 296 | ✅ `date=1850` убирает Exposition Universelle и Gare d'Orsay (`maplibre-ohm.png` и `maplibre-ohm-1850.png`) | **МОЖНО** как контекстный слой. Данные по Парижу 1850 г. неполные |

## 2. Источники тайлов: можно ли легально использовать с GitHub Pages для небольшого некоммерческого музея

| Источник | Тест (HTTP) | Условия (прочитаны) | Атрибуция | Вердикт |
|---|---|---|---|---|
| **OSM tile.openstreetmap.org** | `GET /5/16/11.png` → 200, 46 КБ, `ACAO *` (один запрос) | Tile Usage Policy: обязательны видимая атрибуция, корректный Referer и запрет `Referrer-Policy: no-referrer`; **запрещены офлайн и предзагрузка**, а также «headless bots that pan/zoom»; доступность без SLA | «© OpenStreetMap contributors» | **Только как резерв** для живых пользователей. Нельзя использовать в CI и Playwright, нельзя в SW-кэше. Поэтому в тестах OSM-тайлы не использовались |
| **OpenFreeMap** (`tiles.openfreemap.org/styles/positron`) | style 200, tile 200, `ACAO *`, `max-age=86400` | ToS от 2026-10-14: бесплатно, без ключей и cookie, без лимитов просмотров; **коммерческое использование разрешено**; офлайн до 3 000 тайлов или 50 МБ на загрузку, не больше 4 параллельных запросов, нужен уникальный User-Agent; без SLA, сервис могут отключить без уведомления; спор по праву Венгрии | «OpenFreeMap © OpenMapTiles Data from OpenStreetMap» (MapLibre добавляет её автоматически) | **ВНЕДРЯТЬ как резервную подложку** для обзора Европы и мира |
| **Protomaps / PMTiles, свой файл** | API без ключа → `403 Missing key` (обходить не пытались). Дневная сборка `build.protomaps.com/20261106.pmtiles` (139,35 ГБ, v4.15.2): **Range-выборка центра Парижа z0–14 = 102 тайла, 411 range-запросов, 24 МБ трафика → файл 9 228 120 байт** | Документация: ODbL Produced Work, нужна атрибуция OSM; **ссылаться напрямую на сборки не рекомендуют** — файл надо копировать к себе | «© OpenStreetMap» (+ Protomaps) | **ВНЕДРЯТЬ как основную подложку пилота**: один файл на город в репозитории, без ключей, без третьих лиц, работает офлайн. Лимиты GitHub Pages (по документации): сайт ≤ 1 ГБ, мягкий лимит трафика 100 ГБ в месяц, файл < 100 МБ |
| **Stadia Maps** | без ключа → **401** (обходить не пытались) | Бесплатный тариф «may only be used for non-commercial or evaluation purposes»; для веба нужна регистрация домена или ключ; подмена Referer запрещена | Stadia + OpenMapTiles + OSM | **НЕТ**: регистрация и риск, если проект станет коммерческим (раздел 7 Issue) |
| **MapTiler** | без ключа → **403 «Missing key»** | Требуется ключ и аккаунт (на ценах не останавливались) | MapTiler + OSM | **НЕТ** для пилота |
| **OpenHistoricalMap** (vtiles) | style `main.json` 200 (258 КБ); `vtiles…/maps/osm/5/16/11.pbf` → 200; `ACAO *` | /copyright: данные **CC0** (отдельные объекты могут быть CC BY или CC BY-SA, см. тег `license=*`); стили CC0; атрибуция «greatly appreciated». Отдельной политики нагрузки на vtiles не нашёл (**НЕ ПРОВЕРЕНО**) | В стиле поле `attribution` **пустое**: «OpenHistoricalMap» нужно добавлять самим через `customAttribution` (в тесте сделано) | **МОЖНО**: слой «эпоха», только для контекста и с подписью «неполные данные» |
| maplibre demotiles | style 200 | демо | — | Только для разработки |
| allmaps.xyz (тайлы трансформированных карт) | `.png` 200, tiles.json 200 | Политику нагрузки на allmaps.xyz **не нашёл** | Allmaps + владелец IIIF | **МОЖНО** как резерв без WebGL; при росте трафика согласовать или пререндерить |

## 3. Поведение без WebGL (проверено)

- **MapLibre 6.15.0 требует именно WebGL2.** Конструктор `Map` бросает исключение: *«WebGL2 is required to display this map…»*. Контейнер остаётся пустым, а **1,1 МБ JS уже скачан впустую** (`maplibre-nowebgl-raw.png`, 4 запроса, 1 122 212 байт).
- Решение (реализовано в `t-maplibre.html`, проверено):
  1. **до** импорта MapLibre проверить `canvas.getContext('webgl2')`;
  2. если WebGL2 нет, загрузить Leaflet 1.9.4 и protomaps-leaflet 5.1.0, которые рисуют **тот же `.pmtiles`** через Canvas 2D: отрисовано за ~2,9 с, 823 519 байт, 15 запросов (`maplibre-nowebgl-fallback.png`);
  3. кроме того, `try/catch` вокруг конструктора тоже переключает на запасной режим.
- Без WebGL работают **Leaflet-портал** на старинной карте и **OpenSeadragon** (сам выбирает `canvas`-drawer), а трансформированную карту даёт **Allmaps XYZ**. Клиентский Allmaps без WebGL2 работать не будет.
- **НЕ ПРОВЕРЕНО**: настоящий Safari на iOS/iPadOS, VoiceOver, режим энергосбережения iOS. Все результаты получены в Chromium.

## 4. Предлагаемый минимальный стек пилота (версии закреплены)

Принцип: **никакой сборки**. Сайт остаётся статическим HTML и JS. Библиотеки один раз кладутся в `vendor/` репозитория: один origin, нет зависимости от CDN, worker грузится с того же origin. Ссылки на CDN с SRI ниже — запасной вариант и способ сверить хэши.

```html
<!-- Leaflet 1.9.4 (портал + запасной режим), BSD-2 -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css"
  integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H" crossorigin="anonymous">
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"
  integrity="sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH" crossorigin="anonymous"></script>

<!-- protomaps-leaflet 5.1.0 (PMTiles на Canvas 2D без WebGL), BSD-3 -->
<script src="https://cdn.jsdelivr.net/npm/protomaps-leaflet@5.1.0/dist/protomaps-leaflet.js"
  integrity="sha384-pAKrddYWxjFAIJwatOtmmtq9ebz3ZwluHCEg3pqOMpOporUofLqz/l5hs+0LAWaH" crossorigin="anonymous"></script>

<!-- MapLibre GL JS 6.15.0 (только ESM), BSD-3; грузится ТОЛЬКО при наличии WebGL2 -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/maplibre-gl@6.15.0/dist/maplibre-gl.css"
  integrity="sha384-S+OnE5M4U3Qc2nR0RgljGrVs06xqfRg8L7uFk/pOF5+sRuSDG4oKkqKZmFrx7w09" crossorigin="anonymous">
<script type="importmap">{
  "imports": { "maplibre-gl": "https://cdn.jsdelivr.net/npm/maplibre-gl@6.15.0/dist/maplibre-gl.mjs" },
  "integrity": { "https://cdn.jsdelivr.net/npm/maplibre-gl@6.15.0/dist/maplibre-gl.mjs":
                 "sha384-f3IomKpQJ9QgLFg9JJeeIXKzhYFCZFLXDs4FbQLY13Y1uiaEctrT8RHbumCfpsAc" } }</script>
<!-- worker: https://cdn.jsdelivr.net/npm/maplibre-gl@6.15.0/dist/maplibre-gl-worker.mjs
     sha384-bFMCdo+41ozOqjqQ5s+XmCW14ORz7o11KR04vuUouko65bE1KkGqbN3/z4wUS5Q4
     (integrity на worker не навешивается — поэтому в продакшене копия в vendor/ + maplibregl.setWorkerUrl()) -->

<!-- PMTiles 4.5.0 (протокол для MapLibre), BSD-3 -->
<script src="https://cdn.jsdelivr.net/npm/pmtiles@4.5.0/dist/pmtiles.js"
  integrity="sha384-pbKNZbDshUsLnZMIVsn/t+j3xEY9PGfuX5Z22l5rcy/obXz3EwaMx1F5d9sRsJMn" crossorigin="anonymous"></script>

<!-- OpenSeadragon 6.1.1 (глубокое увеличение + IIIF), BSD-3 -->
<script src="https://cdn.jsdelivr.net/npm/openseadragon@6.1.1/build/openseadragon/openseadragon.min.js"
  integrity="sha384-KKly+4vqqBHitr2XfNKWa3+0asIVpzYs2HijkM/zz0X6rgnyLuQEVERX9HqkM5/P" crossorigin="anonymous"></script>

<!-- опционально: OHM date filter 2.0.0, CC0 -->
<script src="https://cdn.jsdelivr.net/npm/@openhistoricalmap/maplibre-gl-dates@2.0.0/index.js"
  integrity="sha384-OZPcmCmpsigXt1i54ISoTJpMmD5AHDE/ecZjrw9o2rJLF8UraXBMVmoe3gTTaICZ" crossorigin="anonymous"></script>
```

Архитектура экранов:
1. **Портал** — старинная карта в Leaflet `CRS.Simple` с горячими точками городов. Без WebGL, ~46 КБ JS gzip. Честно подписано, что карта декоративная и не геометрически точная.
2. **Город** — MapLibre с PMTiles города (бумажный стиль; см. `maplibre-pmtiles-local.png`). Без WebGL2 тот же файл показывается через Leaflet и protomaps-leaflet.
3. **Эпоха** — точка съёмки на карте; литография открывается в OpenSeadragon (IIIF или статические тайлы). Опционально наложение Allmaps (WebGL2) или его растровый XYZ вариант.
4. **Сегодня** — превью Panoramax (thumb/sd) с автором, датой, лицензией и ссылкой на снимок. Без встраивания просмотрщика.

Allmaps в продакшене: зафиксировать `@allmaps/maplibre@1.0.0-beta.44` и **положить в репозиторий** граф `+esm` (40 файлов, ~347 КБ трафика) с собственными хэшами. Это бета: перед обновлением проверять тестом `t-allmaps.html`.

## 5. Изображения и бюджет байтов

Литография 2000 px из IIIF, перекодировано Pillow 12.3.0 (JPEG q80 progressive, WebP q75 m6, AVIF q50 speed6):

| ширина | JPEG | WebP | AVIF |
|---|---|---|---|
| 480 | 50 676 | 38 694 | **21 487** |
| 960 | 187 389 | 133 024 | **73 426** |
| 1600 | 480 308 | 320 276 | **179 717** |

AVIF примерно в 2,5 раза меньше JPEG. Кодирование занимает до 0,6 с на кадр (офлайн, не страшно). Качество метрикой (SSIM) **не измерялось**: параметры типовые, нужен визуальный контроль куратора.
Разметка: `<picture>` с `<source type="image/avif" srcset="…480w, …960w, …1600w" sizes="(max-width: 600px) 100vw, 50vw">`, затем WebP и JPEG как запасной. Плюс `loading="lazy"` и `decoding="async"` везде, кроме первого изображения; явные `width/height` против прыжков вёрстки.
Глубокое увеличение: IIIF-тайлы стороннего сервера по 1024 px весили **3,39 МБ за первый вид** (OSD, 12 тайлов). Для своих оригиналов нужны статические тайлы 512 px (IIIF level0 или DZI, сгенерированные офлайн) и загрузка только по кнопке «Увеличить». Генерация статических тайлов **НЕ ПРОВЕРЕНА**.

**Бюджет на мобильный (первый вид страницы города, трафик по сети):**
- оболочка (HTML + CSS + свой JS) ≤ **60 КБ** gzip;
- карта: MapLibre (292 + 147 + 10 КБ gzip) + pmtiles 8 КБ ≈ **460 КБ**, либо запасной Leaflet и protomaps-leaflet ≈ **84 КБ**;
- данные карты: **≤ 800 КБ** (замер: первый вид z13 из PMTiles 796 005 байт; у OpenFreeMap 1,09 МБ; у OHM 0,52 МБ);
- изображения над первым экраном: **≤ 150 КБ** (AVIF 960 ≈ 73 КБ плюс 2–3 превью);
- **итого ≤ 1,5 МБ** до взаимодействия, повторный визит — из кэша. OpenSeadragon (87 КБ) и Allmaps (~347 КБ) грузятся лениво, только по действию пользователя. Портал без карты-подложки: замер 376 754 байт с изображением 1394 px.

## 6. Офлайн и PWA на GitHub Pages

- SW регистрируется в подпапке проекта (`/-city-on-paper/sw.js`), область действия — эта подпапка. Заголовок `Service-Worker-Allowed` на GitHub Pages выставить нельзя, но для подпапки он и не нужен.
- Cache API не хранит ответы `206`. Поэтому SW кэширует **целый** `.pmtiles` и сам отдаёт Range-нарезку. Это проверено: офлайн-перезагрузка отрисовала карту.
- `max-age=600` у GitHub Pages: кэш SW нужно версионировать (`cop-pilot-vN`).
- **Риск**: origin `zukevich-blip.github.io` общий для всех Pages-репозиториев этого пользователя, поэтому квота хранилища и SW-скоупы делятся между ними. `persisted=false`: браузер может очистить кэш.
- OSM-тайлы кэшировать в SW нельзя (политика OSM). OpenFreeMap разрешает до 3 000 тайлов или 50 МБ. Свой PMTiles — без ограничений.

## 7. Риски

1. MapLibre 6 требует WebGL2 и поставляется только как ESM: обязательны детектор и запасной режим, а копии в репозитории лучше называть `.js`. Отдаёт ли GitHub Pages `.mjs` с JS-MIME — **НЕ ПРОВЕРЕНО**.
2. Allmaps — бета (`1.0.0-beta.x`); `+esm` нельзя закрепить через SRI. Нужно положить в репозиторий и закрепить версию.
3. У OpenFreeMap и OHM нет SLA. Основная подложка пилота — свой PMTiles: 9,2 МБ на центр Парижа до z14; Флоренция и Неаполь будут сопоставимы, **но не измерены**.
4. Панорамы Panoramax в основном CC-BY-SA-4.0: при показе нужны автор, лицензия и ссылка. Share-alike касается производных изображений (например, «открыток»), это нужно учесть в матрице прав. Во Флоренции и Неаполе снимков мало (13 и 5 в тестовых bbox).
5. OHM-данные по эпохам неполные; в стиле нет атрибуции.
6. Safari, iOS и VoiceOver **не проверялись**. `importmap.integrity` в Safari **НЕ ПРОВЕРЕН**; если не поддерживается, MapLibre лучше брать из своей копии в репозитории.
7. OCR и ORB дают только подсказки: точность низкая (см. §1). Автоматических выводов о «совпадении ракурса» не делать.
8. Тестовая карта Гента (Digital Commonwealth) использована **только как тестовая фикстура**; права на публикацию не проверялись.

## 8. Состав папки

- `t-maplibre.html` (`?src=pmtiles|ofm|ohm&lib=local|localjs|cdn&fallback=0|1&date=YYYY`), `t-leaflet.html`, `t-leaflet-allmaps-xyz.html`, `t-allmaps.html`, `t-osd.html`, `t-ol.html`, `t-pwa.html` + `sw.js`, `t-sri-negative.html`
- `shots/*.png` (17 скриншотов) + `shots/*.json` (логи Playwright: запросы, байты, ошибки)
- `data/paris-z14.pmtiles` (9 228 120 байт, ODbL produced work, © OpenStreetMap)
- `vendor/` — точные файлы, по которым считались размеры и SRI
- `img/out/` — AVIF/WebP/JPEG, визуализация ORB, `img_bench.json`, `ocr.txt`
- `scripts/` — `serve.py`, `run_pw.js`, `run_pwa.js`, `probe_net.py`, `extract_pmtiles.py`, `img_bench.py`, `compile_probe.py`
