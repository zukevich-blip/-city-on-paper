# Руководство по интеграции модулей Gemini R&D в основной музей Claude Code

**Версия пакета:** `BENOIST LEGACY — INTEGRATION READY v10.0`  
**Архив:** `city-on-paper-benoist-integration-ready.zip`  
**Стратегический принцип:** художественная концепция, музейная атмосфера, вёрстка и повествовательный ритм основного музея **Claude Code** остаются нетронутой основой. Лаборатория Gemini поставляет **15 полностью автономных UI-независимых ESM-модулей**, восстановленные открытые архивы Филиппа и Феликса Бенуа, 48 Agent Skills и 42 Read-Only MCP инструмента для выборочного подключения без сборки и без React.

---

## 1. Что исправлено и усилено в v10.0 INTEGRATION READY

1. **100% подлинное наследие Филиппа (1813–1905) и Феликса (1818–1896) Бенуа (0 подмен):**
   - В `bookWorks` и в `flagshipStories3` полностью исключены подмены работ Бенуа произведениями Эдуарда Бальдюса, Джованни Паоло Панини, Франческо Гварди, Эдуарда Гау и Константина Ухтомского.
   - Другие мастера сохранены строго отдельно в `relatedMastersWorks` как исторический контекст.
   - Исключён гравёр XVIII века Guillaume-Philippe Benoist (`/guillaume[\s-]+philippe benoist/i`).
2. **Массовое восстановление подлинных изображений в каталогах и альбомах:**
   - **Базовый каталог 110 листов:** покрытие выросло с **8/110 (7.3%) → 99/110 (90.0%)** благодаря прямому восстановлению **72/72 (100%)** сканов **Paris Musées Official IIIF API (CC0)** и **19/22 (86.4%)** сканов **Rijksmuseum Amsterdam (CC0)**.
   - **Расширенный каталог Бенуа:** **287 / 298 оцифрованных листов** (включая подлинные титульные листы BnF Gallica *Paris dans sa splendeur* `btv1b53024785d`, *Nouvelles vues de Paris* `btv1b53088077g`, полную 20-листовую серию *Album de l'Île de Jersey*, *La Bretagne contemporaine*, *Rome dans sa grandeur*).
   - **Восстановленные исторические альбомы (9 альбомов):** покрытие выросло с **8/56 (14.3%) → 137/137 (100%)** оцифрованных страниц с реальными обложками/титульными листами и проверенными размерами.
3. **Эпистемическая чистота `packages/museum-context/index.mjs`:**
   - При передаче пустого или неполного объекта `resolveContextFromBenoistWork({})` больше НИКОГДА не фабрикует `"Philippe Benoist"`, `"Париж"`, `[2.3499, 48.853]`, `1855` или `"Public Domain / CC0"`. Все неизвестные поля честно равны `null` со статусами `"unknown"` в `epistemicAudit`.
4. **Эпистемическая чистота `packages/album-iiif-viewer/index.mjs`:**
   - Больше НИКОГДА не присваивает автоматически `https://creativecommons.org/publicdomain/mark/1.0/` при отсутствии подтверждённой лицензии.
   - Больше НИКОГДА не генерирует фиктивный `placeholder-plate.jpg` и вымышленные размеры `1600×1160` для неоцифрованных библиографических листов.
5. **100% проверенные пути в `packages/PORTABLE_PACKAGES_MANIFEST.json`:**
   - Исправлены оба отсутствовавших пути из v9.0; все 15 пакетов получили собственные переносимые файлы `packages/<package>/index.mjs` + живой статический пример `packages/examples/claude-static-museum-demo.html`.
   - Проверка `verifyPortablePackagesManifest()` подтверждает `0` отсутствующих файлов.

---

## 2. Три флагманские завершённые истории от подлинных литографий Бенуа

Каждая история в `benoist-legacy-v9.json → flagshipStories3.stories` строго начинается с подлинника Филиппа Бенуа и разворачивается по 8 ступеням (`произведение → город → историческая карта → архитектура → интерьер → повседневная жизнь → современный вид → связанные мастера`):

1. **Флагман #1 — Церковь Мадлен (Париж):** Филипп Бенуа (~1850, Library of Congress PD) + ранний оттиск 1843 г. (`RP-P-1905-5495`, Rijksmuseum CC0) + интерьер Мадлен № 42 (1855, Carnavalet CC0). Связанные мастера: Э. Бальдюс (1860-е), Пиранези.
2. **Флагман #2 — Собор Парижской Богоматери и остров Сите (Париж):** Филипп Бенуа (1843, Rijksmuseum CC0 `RP-P-1905-5500` — до реставрации Виолле-ле-Дюка!) + Сент-Шапель (1849, Paris Musées IIIF `320290066`) + 610 реальных парцелл ALPAGE. Связанные мастера: Э. Бальдюс (1858), Ш. Мерион (1853).
3. **Флагман #3 — Римский Форум (Campo Vaccino, 1865) и утраченный Порт Рипетта (1870):** Филипп Бенуа (*Rome dans sa grandeur*, Wikimedia Commons PD) + Вестибюль Св. Петра (`RP-P-1944-1699`, Rijksmuseum CC0) + план Нолли 1748 («Город без крыш»). Связанные мастера: Дж. П. Панини (1734), Дж. Б. Пиранези (1756).

---

## 3. Быстрое подключение в статический сайт Claude Code (0 сборщиков, 0 React)

Готовый рабочий эталон: **`packages/examples/claude-static-museum-demo.html`** — откройте его через любой статический сервер (`npx serve .` или `python3 -m http.server`).

### Пример подключения 4 ключевых модулей в `<script type="module">`

```html
<script type="module">
  import { createMuseumContextStore } from "./packages/museum-context/index.mjs";
  import { searchBenoistPlates, findRelatedBenoistEditions, getDigitizedCoverageStats } from "./packages/benoist-catalog/index.mjs";
  import { buildIiifPresentationV3Manifest, createAlbumController } from "./packages/album-iiif-viewer/index.mjs";
  import { applyNonDestructiveCanvasFilter, RESTORATION_FILTER_PRESETS } from "./packages/computer-vision/index.mjs";

  const [world, legacy] = await Promise.all([
    fetch("./data/chronos/chronos-world-explorer-v8.json").then((r) => r.json()),
    fetch("./data/chronos/benoist-legacy-v9.json").then((r) => r.json()),
  ]);

  // 1. Статистика восстановленных изображений Бенуа (287/298)
  const stats = getDigitizedCoverageStats(world.benoistWorldCatalog.verifiedPlates);
  console.log("Benoist digitized:", stats);

  // 2. Единый контекст без фабрикации дефолтов
  const store = createMuseumContextStore();
  store.subscribe((ctx) => console.log("Active Benoist work:", ctx.artworkId, ctx.artistName));
  store.selectBenoistWork(legacy.bookWorks[0], world);

  // 3. Поиск разных изданий одного памятника Бенуа (например, Мадлен 1843 ↔ 1850 ↔ 1855)
  const madeleine = world.benoistWorldCatalog.verifiedPlates.find((p) => p.id === "benoist-paris-madeleine-ext");
  const relatedEditions = findRelatedBenoistEditions(madeleine, world.benoistWorldCatalog.verifiedPlates);

  // 4. Честный IIIF Presentation 3.0 манифест и контроллер перелистывания альбома
  const album = legacy.restoredAlbums.albums[0];
  const iiifManifest = buildIiifPresentationV3Manifest(album, window.location.origin);
  const viewer = createAlbumController(album, "original");
</script>
```

---

## 4. Справочник всех 15 автономных пакетов (`packages/*/index.mjs`)

| # | Пакет | Автономный модуль | Назначение в музее Claude Code |
|---|---|---|---|
| 1 | `@city-on-paper/museum-data` | `packages/museum-data/index.mjs` | Загрузка и валидация канонического JSON-контракта |
| 2 | `@city-on-paper/benoist-catalog` | `packages/benoist-catalog/index.mjs` | Поиск по 287+ оцифрованным листам Бенуа и матчинг изданий |
| 3 | `@city-on-paper/museum-context` | `packages/museum-context/index.mjs` | Синхронизация активного листа без выдуманных дефолтов |
| 4 | `@city-on-paper/historical-cartography` | `packages/historical-cartography/index.mjs` | Allmaps SODUCO, TPS LOOCV и план Нолли 1748 |
| 5 | `@city-on-paper/temporal-system` | `packages/temporal-system/index.mjs` | 6-осевая хронология (постройка ≠ дата снимка) |
| 6 | `@city-on-paper/spatial-contours` | `packages/spatial-contours/index.mjs` | Проекция 2 252 GeoJSON-полигонов в чистый SVG |
| 7 | `@city-on-paper/computer-vision` | `packages/computer-vision/index.mjs` | Неразрушающие Canvas 2D фильтры (CLAHE/Retinex/UV/IR/Sobel) |
| 8 | `@city-on-paper/morphing` | `packages/morphing/index.mjs` | Слайдер 36 готовых JPEG-кадров + квадратичный контроль 0 инверсий |
| 9 | `@city-on-paper/interiors` | `packages/interiors/index.mjs` | 50 интерьеров с 6 честными категориями сопоставления |
| 10 | `@city-on-paper/historical-floorplans` | `packages/historical-floorplans/index.mjs` | SVG-конусы обзора художников на архивных планах |
| 11 | `@city-on-paper/3d-reconstructions` | `packages/3d-reconstructions/index.mjs` | Математика плоскостей среза (отделена от Three.js/React) |
| 12 | `@city-on-paper/historical-narratives` | `packages/historical-narratives/index.mjs` | 3 флагманские 8-ступенчатые истории, 12 глав, 17-пунктные досье |
| 13 | `@city-on-paper/audio-and-iiif-albums` | `packages/album-iiif-viewer/index.mjs` | Честный IIIF 3.0, OpenSeadragon tileSource, KMZ |
| 14 | `@city-on-paper/skills-and-mcp` | `packages/skills-and-mcp/index.mjs` | 48 SKILL.md, 42 Read-Only MCP инструмента, верификатор манифеста |
| 15 | `@city-on-paper/automated-tests` | `packages/automated-tests/index.mjs` | Регрессионные проверки и оффлайн-наборы `node --test` |

---

## 5. Подключение MCP (42 Read-Only инструмента) и 48 Skills в Claude Code

Добавьте в `.mcp.json` репозитория Claude Code:

```json
{
  "mcpServers": {
    "city-on-paper-benoist-integration-ready": {
      "command": "node",
      "args": ["exports/city-on-paper-handoff-20261125/mcp/museum_mcp_server.mjs"]
    }
  }
}
```

Новые инструменты v10.0: `search_benoist_digitized_plates`, `get_benoist_flagship_stories`, `verify_portable_packages_manifest`, `find_related_benoist_editions`. Все 42 инструмента работают строго в режиме **Read-Only** по stdio.

---

## 6. Проверка целостности и автоматические тесты перед переносом

Перед подключением модулей в репозиторий Claude Code выполните оффлайн-проверку всех 15 автономных пакетов, регрессионных тестов v10.0 и целостности контрольных архивов:

```bash
npm test
npm run test:checkpoints
```

Обе команды работают полностью автономно без платных API-ключей и подтверждают: отсутствие выдуманных дефолтов в `museum-context`, отсутствие `placeholder-plate.jpg` и фиктивных `1600×1160` в IIIF-манифестах, существование 100% путей из `PORTABLE_PACKAGES_MANIFEST.json`, отсутствие подмен наследия Бенуа, 48 Skills и 42 Read-Only MCP инструмента.


---

## 7. Прокси изображений и внешние домены

Все восстановленные изображения открытого доступа размещены на официальных музейных хостах (CC0 / Public Domain):
- `apicollections.parismusees.paris.fr` (Paris Musées / Musée Carnavalet 4K CC0)
- `thumb.wikimedia.org` и `upload.wikimedia.org` (Rijksmuseum CC0, BnF Gallica, LoC, Wikimedia PD)
- `images.metmuseum.org` (Metropolitan Museum of Art CC0 — только в `relatedMastersWorks`)

В статическом сайте эти URL можно рендерить напрямую в `<img src="...">` без обязательного бэкенда; при использовании прокси добавьте указанные домены в allowlist.
