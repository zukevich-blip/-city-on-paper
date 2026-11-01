# Кураторский реестр, первый шаг (Issue #6, PR A2) — 01.11.2026

Статус: **черновик для проверки человеком.** Все записи подготовил Claude (automated); у каждого состояния стоит `reviewer: "Claude (automated) — needs human review"`. Выставка не тронута, в `main` ничего не вливается. Ветка стоит поверх `claude/issue6-a-provider-matrix` (PR #7).

Файлы:

| Файл | Что это |
|---|---|
| `data/catalog/works/*.json` | 27 каталожных записей по `schemas/artwork.schema.json` |
| `data/catalog/ledger-2026-11-01.csv` | одна строка на работу: id, название, авторы и роли, дата, держатель, ссылка, статус атрибуции, статус прав, режим распространения, серия |
| `tools/catalog/validate.py` | валидатор (только stdlib): обязательные поля, значения enum, уникальность id, URL-доказательство у каждого статуса, кроме `candidate` |
| `tools/catalog/ledger.py` | собирает CSV из записей |
| `tests/test_catalog.py` | pytest: весь каталог проходит валидатор, CSV совпадает с записями, проверки на заведомо плохих записях |
| `schemas/artwork.schema.json` | **одно изменение:** в `agents[].role` добавлено значение `artist`. Оно нужно, когда держатель не указал роль («Artist» у Met, `dc:creator` без роли у Biblioteka Narodowa). Иначе пришлось бы выдумывать роль «рисовальщик» или «литограф». |

## 1. Метод

1. Отбор шёл из `data/candidates/candidates-2026-11-01.json` (PR A) с подсказками `felix` / `philippe` / `felix+philippe` и по ключевым словам Wilna / Wilno. Добавлены целевые запросы:
   - Europeana: `Benoist AND (Wilna OR Wilno …)`, `"Félix Benoist" AND (Bretagne OR Nantes)`, `"Paris dans sa splendeur"`, `"Bretagne contemporaine"`, `"Nantes et la Loire-Inférieure"`;
   - Met: `v1.1/search?q=Philippe Benoist`;
   - Rijksmuseum: `search/collection?creator=…`;
   - LoC: `photos/?fa=contributor:benoist, philippe`.
2. Каждую выбранную запись я перечитал **в записи держателя**:
   - LoC: `https://www.loc.gov/item/{id}/?fo=json`;
   - Europeana: `https://api.europeana.eu/record/v2/{id}.json?wskey=api2demo`. Читался прокси поставщика данных, то есть метаданные, которые сдал сам держатель: BnF, Šiaulių „Aušros“ muziejus, Biblioteka Narodowa, Bibliotheca Hertziana;
   - Met: `collectionapi…/v1/objects/{id}`.
   
   HTML-страницы держателей как доказательство не использовались, если они не отдавали содержимое (см. §6).
3. Правило статусов:
   - `verified` — атрибуцию прямо называет запись держателя (поле автора или транскрипция надписи);
   - `uncertain` — держатель сам сомневается (`?`) либо называет авторов только на уровне книги;
   - `candidate` — не проверено.
   
   Права: `verified` значит, что формулировку прав я прочитал в записи. Режим `redistribution`:
   - `allowed` — только для LoC («No known restrictions on publication») и Biblioteka Narodowa (Public Domain Mark);
   - `link_only` — для всего остального (условия Gallica для коммерческого использования, CC BY-NC-ND, InC, Met не-OA).
4. География: **координат нет ни в одной записи.** Держатели называют город или здание, но не точку. Поэтому `precision: "city"`, а гео-статус `verified` относится только к уровню города. Точки места европейских записей — это центроиды стран и место печати (Франция для литовских листов). Использовать их нельзя.
5. Ракурс (`viewpoint`) не оценивался, везде стоит `candidate`. У переплетённой книги Met — `not_applicable`.
6. Флаг `is_retrospective_reconstruction` не выставлен ни разу. Ни одна прочитанная запись не говорит, что композиция ретроспективная. Подзаголовок «scènes historiques» у «Paris dans sa splendeur» таким основанием не считается.

## 2. Счётчики

| | Кол-во |
|---|---|
| Записей | **27** |
| Атрибуция `verified` | **22** |
| Атрибуция `uncertain` | **5** (2 рисунка BnF с «[Philippe Benoist ?]», 3 листа «Rome dans sa grandeur» из Hertziana) |
| Атрибуция `candidate` / `blocked` | 0 / 0 |
| Права `verified` | 27 |
| `redistribution: allowed` | 6 (4 LoC, 2 Biblioteka Narodowa) |
| `redistribution: link_only` | 21 |

Держатели:

| Держатель | Записей |
|---|---|
| BnF (через Europeana) | 12 |
| Library of Congress | 4 |
| Šiaulių „Aušros“ muziejus (LIMIS) | 4 |
| Bibliotheca Hertziana | 3 |
| Biblioteka Narodowa | 2 |
| The Met | 2 |

По художникам:

- Philippe Benoist назван держателем отдельно в 17 записях: 15 `verified`, 2 `uncertain` (рисунки с «?»).
- Félix Benoist — в 4 листах BnF (`verified`).
- Félix и Philippe совместно — в 3 листах Hertziana (`uncertain`).
- **Контрольные записи «не Бенуа»: 3.** Это листы Album de Wilna работы Sadownikoff / Bichebois / V. Adam / Deroy / Rypiński / Zaleski. Они включены, чтобы такие листы альбома не приписали Бенуа.

Тематика: город, архитектура, площади. Один рынок — «Les Halles centrales» (Félix Benoist, BnF, `food_market`).

## 3. Различение Бенуа (что говорят сами держатели)

| Лицо | Wikidata (identity.py) | Что пишут держатели |
|---|---|---|
| Philippe Benoist | Q26309223, 1813 – 1896-11-01 | **LoC:** «1813-approximately 1905». **BnF:** «1813-1905» (рисунки), «1813-1905?» (книга «Paris dans sa splendeur»). **Biblioteka Narodowa:** «1813-ca 1905». **Met:** «Geneva 1813–ca. 1905» и ссылка на Q26309223. **Hertziana:** «Philippe (1813)». → **Конфликт:** у Wikidata смерть в 1896, у всех держателей около 1905. Ни один держатель не даёт 1896. |
| Félix Benoist | Q277187, 1818–1896 | **BnF:** «1818-1896» — совпадает с Wikidata. |
| Guillaume Philippe Benoist | Q5616064 | В этот реестр не входит. **Ловушка:** поиск Rijksmuseum `creator=Philippe Benoist` возвращает 40 объектов, первые из них — портреты Guillaume Philippe Benoist (XVIII в.). Совпадение строки «Philippe Benoist» не значит, что автор — Philippe Benoist (1813). |
| Antoine Benoist | Q18526511 | В этот реестр не входит. |
| A. Bayot (Adolphe Jean-Baptiste) | — | **LoC:** 1810–1871. Роль у держателей разная: в BnF «Dessinateur du modèle», хотя в той же записи строка издателя гласит «Fig. par A. Bayot». В записях роль взята по надписи (`figures`). Исключение — «Pavillon du Louvre»: там надписи нет, поэтому оставлено `draughtsman`, как у BnF. |

Совместные листы:

- «Vue officielle a vol d'oiseau de l'exposition universelle de 1867». Надпись: «Eug. Cicéri et Ph. Benoist del & lith.», то есть оба и рисовали, и литографировали. В `contributor_names` LoC указан только Cicéri — lithographer, Benoist — artist.
- Листы Félix Benoist у BnF имеют формулу «Félix Benoist del. J. Arnout / Eug. Ciceri / A Mathieu lith. Fig. par A. Bayot» с издательством «Nantes, lith. Charpentier».

## 4. Серии и альбомы

| Серия | Что говорит держатель | Записи |
|---|---|---|
| **Album de Wilna** (изд. J. K. Wilczyński, печать Lemercier, Париж) | **Biblioteka Narodowa:** «Album Wileńskie, wyd. J.K. Wilczyński, ser. 1, Paryż 1845-1875». Сводный том — «Album Wileńskie» [1845-1875], 3 vol., 83 + 133 + 12 листов, в том числе «Album de Kijów», «Album de Warsovie» (polona 5552568, прочитан; в реестр как работа не внесён). **Šiauliai:** на листе «Album de Wilna 2e Série 3e Liv.», «No 36», «Lith. par Ph. Benoist … Fig par Bayot». | 349256439 (Benoist — verified), 349391706 (Benoist — verified; принадлежность к альбому — кандидат), 349245981 и 349293272 (не Бенуа), polona 7047686 (не Бенуа) |
| **Album de Varsovie** | **Biblioteka Narodowa** относит лист «Widoki Warszawy: wnętrze pałacu zwanego Łazienki» к «Album Wileńskie ser. 1, poszyt 2». Надпись над композицией при этом: «Album de Varsovie 1er Serie 1er Liv.». | polona 9970636 |
| **Paris dans sa splendeur** (Charpentier) | **BnF:** книга 1861, «Dessins et lithographies par MM. Philippe Benoist,… Jules Arnout,…» (bpt6k6118590b, прочитан). **Heidelberg:** «Philippe Benoist [und 17 weitere]» (прочитан). Лист «Pavillon du Louvre – Place Napoléon III» BnF прямо называет «Première pl. et page de titre de l'album Paris dans sa splendeur». | btv1b53024785d — верифицировано. 4 листа Félix Benoist / Charpentier (Halles, Élysée, Tuileries, Conservatoire): **альбом в записи BnF не назван**, см. открытые вопросы. |
| **Rome dans sa grandeur** (Charpentier, 1870, текст F. de Champagny) | **Hertziana:** «dessins d'après nature par Philippe Benoist et Félix Benoist … Paris: Charpentier, 1870. Band 3: Rome moderne». Авторство указано для книги в целом, а не для листа. | 3 листа (Civitavecchia, Vatican, Villa Borghese) — `uncertain` |
| **Vues de Paris** (Gihaut frères) | **LoC:** «From series: Vues de Paris.» | LoC 2013650023 |
| **Promenade dans Paris et ses environs** | **LoC:** «Possibly from a later edition of: Promenade dans Paris et ses environs … J. Jacottet, avec figures par A. Bayot. Paris: Gihaut frères, [1838-1843]». Слово «possibly» — самого LoC. | LoC 2016652451 (pl. 6), 2016652452 (pl. 8) |
| **Nouvelles Vues de Paris** | **Met:** книга (ca. 1850; 1845–1855). В числе авторов Philippe Benoist (Artist), L. J. Jacottet («Drawn and lithographed by»), A. Provost, «Gibaut Frères», Auguste Bry. | Met 345889 |
| **Фонд Destailleur, «Province»** (BnF, EST RESERVE VE-26) | Рисунки Philippe Benoist, mine de plomb (графитный карандаш), 1842–1845 / «184.» / «18..». Ссылки: «Destailleur Province, t. 3/4, №…». | 7 рисунков (Senlis, Rouen ×2, Rue, Bayeux, Saint-Riquier, Caen) |
| **La Bretagne contemporaine** | Europeana: 1 результат — постороннее фото Joconde. Commons (там у PR A были кандидаты Félix Benoist, замки близ Нанта) → **429**, повторять не стал. | — (заблокировано) |
| **Nantes et la Loire-Inférieure** | Europeana дала только «La ville de Nantes et la Loire-Inférieure», 1898–1900, без имени Benoist (bpt6k164488r, прочитан). Это **не** альбом Félix Benoist. | — |

## 5. Расхождения и конфликты дат

1. **Год смерти Philippe Benoist:** Wikidata — 1896; LoC, BnF, BN, Met — около 1905 (у BnF в одной записи «1905?»).
2. **Датировка в кандидатах PR A вводит в заблуждение.** `date_display = 1845-01-01` у LoC — это лишь сортировочная дата. Сам LoC пишет «[between 1845 and 1860]». В реестре стоят 1845–1860.
3. **Альбом Wilna или Varsovie:** см. §4 (polona 9970636).
4. **Роли Lemercier и Wilczyński.** Šiauliai ставит Wilczyński в `dc:creator`, а Lemercier в `dc:publisher`. Надпись же называет Wilczyński «l'Editeur», а Lemercier «Imp.» (печатник). Biblioteka Narodowa: Wilczyński «Red.», Lemercier «Druk.». В записях роли взяты по надписи.
5. **Gihaut / Gibaut.** LoC: «Gihaut frères». Met: «Gibaut Frères». Скорее всего, это одна фирма, но это не проверено.
6. **Роль Bayot у BnF:** «Dessinateur du modèle» против надписи «Fig. par A. Bayot».
7. **Права в одном фонде расходятся.** Šiauliai: три листа под CC BY-NC-ND 4.0, а «Église Sainte Anne» (349391706) — под InC.
8. **Hertziana:** `dctermsCreated` «1986 (Zugangsdatum) (Fotografische Aufnahme)» — это дата фотографии, а не литографии. Права InC относятся к фото Hertziana.
9. **Halles centrales:** даты в записи BnF нет. Есть только рубрика «France -- 1848-1852 (2e République)». Датой листа я её не считаю.
10. **Met 656125:** дата только «19th century».
11. **Подсказка `felix+philippe`** у листов Hertziana в PR A — это авторство книги, а не листа.

## 6. Что заблокировано или не проверено

| Ресурс | Результат 01.11 | Что сделано |
|---|---|---|
| Gallica напрямую | 403 (известно по PR A) | Не повторял. Метаданные BnF взяты через Europeana. IIIF-адреса Gallica в записях **не проверены**. |
| Wikimedia Commons API | **429** | Не повторял. Кандидаты Commons (Vilnia Masalski «P. Benoist 1850», Rome dans sa grandeur, замки Félix Benoist) в реестр не вошли. |
| foto.biblhertz.it/obj08003574 | 200, но вместо содержимого страница «Proof-of-Work» | Не обходил. В доказательствах только запись Europeana. |
| loc.gov/item/… (HTML) | 403 | Использован JSON `?fo=json`: 200. |
| metmuseum.org (HTML) | 429 | Использован Collection API: 200. |
| limis.lt, polona.pl | 200, но это оболочка JS без данных | В доказательствах только записи Europeana. |
| LoC `manifest.json` | 403 (PR A) | В записях IIIF-манифестов LoC нет. |

## 7. Открытые вопросы для куратора

1. Год смерти Philippe Benoist: 1896 (Wikidata) или около 1905 (держатели)? Нужен первоисточник — акт о смерти или справочник (Bénézit, ULAN 500009717).
2. Входят ли листы Félix Benoist с выходными данными Charpentier (Nantes) и номерами 24 / 65 / 69 в «Paris dans sa splendeur»? В книге BnF среди литографов назван Jules Arnout, а у Heidelberg — «Philippe Benoist [und 17 weitere]». Нужна сверка со списком таблиц тома (Gallica bpt6k6118590b) из браузера владельца.
3. Какие листы «Rome dans sa grandeur» нарисовал Philippe, а какие Félix? Нужна подпись на самом листе — скан Hertziana или Gallica.
4. Рисунки Destailleur с «?» (Rouen, Saint-Ouen; Bayeux): подтвердить или снять атрибуцию.
5. Album de Wilna: составить полный список листов с участием Benoist по описи BN (G.50485–G.50712).
6. «La Bretagne contemporaine» и «Nantes et la Loire-Inférieure» (Charpentier) с Félix Benoist: держатели не найдены. Повторить, когда Commons снимет 429, и из браузера владельца в Gallica.
7. Проект коммерческий или нет? От этого зависит, можно ли переводить записи BnF из `link_only` в `allowed` (условия Gallica).
8. Ракурсы (`viewpoint`) для пар «тогда / сейчас» не оценивались. Кандидаты с узнаваемой точкой съёмки: Madeleine, Palais-Royal, Tuileries / Carrousel, Vilnius — университет и костёл Св. Анны.

## 8. Как воспроизвести

```bash
python3 -m tools.catalog.validate          # 27 records, 0 errors
python3 -m tools.catalog.ledger            # пересобрать CSV
python3 -m pytest -q tests
ruff check tools tests
```
