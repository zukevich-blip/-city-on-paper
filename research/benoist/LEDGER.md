# Реестр источников: литографии Феликса Бенуа (Félix Benoist) — 31.10.2026

Статус: **исследование, не приложение.** Issue #1 требует сначала восстановить исходную выставку; исходников в репозитории нет (см. ниже). Поэтому здесь только проверяемые данные об источниках. Изображения не изменялись и в git не сохранены: нужна ссылка на страницу Commons и контрольная сумма.

## 0. Восстановление выставки — BLOCKED

- В `main` (`1c541f0`) только `README.md` и `MIGRATION.md`.
- Коммитов `ae296cbc…` и `1f975375…` из `MIGRATION.md` на GitHub нет: `upload-pack: not our ref`.
- Бандл `city-on-paper-2026-10-29.bundle` хранится у владельца. Среди опубликованных страниц Claude (artifacts) аккаунта выставки тоже нет.

**Что нужно от владельца:** загрузить `.bundle` (например, приложить к Issue #1 или отправить в ветку) или указать, где лежит экспорт Sites. Без этого старые работы и пары не сравнить, и «ничего не потеряно» не доказать.

## 1. Подлинные работы Бенуа, найденные на Wikimedia Commons

Данные — из API Commons (`imageinfo`/`extmetadata`) 31.10.2026. Атрибуция взята с Commons и **не сверена** с каталогом музея или Gallica.

| # | Файл Commons | Автор (по Commons) | Дата | Источник / собрание | Лицензия | Сюжет (категории Commons) |
|---|---|---|---|---|---|---|
| B1 | [Hennebont église par félix benoist 1.jpg](https://commons.wikimedia.org/wiki/File:Hennebont_%C3%A9glise_par_f%C3%A9lix_benoist_1.jpg) | Félix Benoist (1818–1896) | 1865 | Musée de Bretagne, Arts graphiques | Public domain | Церковь Нотр-Дам-де-Паради, Энбон, с рыночной площадью |
| B2 | [Notre-Dame de Kernascléden vers 1845.jpg](https://commons.wikimedia.org/wiki/File:Notre-Dame_de_Kernascl%C3%A9den_vers_1845.jpg) | рисунок F. Benoist, литография Eugène Cicéri | около 1845 | Musée de Bretagne | Public domain | Церковь Нотр-Дам, Кернаскледен |
| B3 | [Porche et clocher de Saint-Houardon Landerneau.jpg](https://commons.wikimedia.org/wiki/File:Porche_et_clocher_de_Saint-Houardon_Landerneau.jpg) | Félix Benoist | 1867 (издание) | «La Bretagne contemporaine», т. Finistère | Public domain | Южный портал и колокольня Сен-Уардон, Ландерно |
| B4 | [Saint Denis Félix Benoist 1844 1845.jpg](https://commons.wikimedia.org/wiki/File:Saint_Denis_F%C3%A9lix_Benoist_1844_1845.jpg) | Félix Benoist | 1844–1845 | скан оригинала | Public domain | Западный фасад базилики Сен-Дени |
| B5 | [Chateau Clisson au XIXe.jpg](https://commons.wikimedia.org/wiki/File:Chateau_Clisson_au_XIXe.jpg) | L.-A. Bicheois **по рисунку** F. Benoist | около 1864 | Duruy, «Histoire de France», т. 1, с. 433 | Public domain | Замок Клиссон |
| B6 | [Felix Benoist - Le Palais du Luxembourg et son Jardin](https://commons.wikimedia.org/wiki/File:Felix_Benoist_-_Le_Palais_du_Luxembourg_et_son_Jardin_-_Google_Art_Project.jpg) | Félix Benoist | — | Google Arts & Culture, Сенат | Public domain | Люксембургский дворец, вид с птичьего полёта над rue de Tournon |

**Где важно не перепутать авторство:**
- B2 и B5 — не «чистый Бенуа»: B2 литографировал Cicéri, B5 гравировал Bicheois по его рисунку. В каталоге указывать обоих.
- Филипп Бенуа (Philippe Benoist) — отдельный автор. Его работ здесь пока нет: Commons ограничил число запросов раньше, чем дошла очередь.

## 2. Пары «тогда / сейчас» — статус

| Пара | Историческое | Сравнение | Ракурс | Статус |
|---|---|---|---|---|
| P1 | B1 (1865) | [Hennebont place du marché et église.jpg](https://commons.wikimedia.org/wiki/File:Hennebont_place_du_march%C3%A9_et_%C3%A9glise.jpg) — **открытка около 1900**, автор неизвестен, PD, источник delcampe.net | Визуально близок: западный фасад с порталом и шпилем по оси улицы, дома справа. Проверил Claude по превью 800 px | **КАНДИДАТ**. Это открытка, а не современное фото. Точка съёмки и состав зданий справа не подтверждены |
| P2 | B2 | современные фото фасада в категории Commons | — | **NOT TESTED**: не скачаны (HTTP 429 Wikimedia) |
| P3 | B3 | современные фото портала Сен-Уардон | — | **NOT TESTED**: то же |

Ни одна пара **не подтверждена**. Для подтверждения нужны:
1. Современное фото с подходящей лицензией (CC BY / CC BY-SA, с автором и датой).
2. Одна и та же точка съёмки: координаты фото и азимут, сверка по 3–4 устойчивым ориентирам — оси портала, карнизам, углам соседних домов.
3. Пометка о спорном: на B1 справа деревянные дома, которых на открытке уже нет. Совмещение показывает изменения и ничего не дорисовывает.
4. Проверка человеком: владелец или специалист.

## 3. Инструменты из каталога — решение на этом этапе

| Инструмент | Решение | Почему |
|---|---|---|
| Wikimedia Commons API | использован | открытые метаданные и лицензии. Ограничение — частота запросов (429): нужен медленный загрузчик с паузами |
| OpenSeadragon, Mirador / IIIF | отложено | нечем просматривать, пока нет восстановленного приложения. Gallica IIIF из облака Claude отвечает HTTP 403 |
| OpenCV (контрольные точки, гомография) | после выбора пары | совмещение только обратимое, по ручным контрольным точкам; исходный скан не меняется |
| img-comparison-slider | после восстановления приложения | только если в старом приложении нет своего ползунка |
| Leaflet / MapLibre / DistortableImage | отложено | понадобится для карты точек съёмки, когда пар будет больше трёх |

## 4. Воспроизведение

Метаданные и SHA-256 скачанных превью лежат в `commons_fetch_meta.json`. Превью качались через `thumb.wikimedia.org` с паузами; сами файлы в репозиторий не добавлялись.
