# Схема записи фонда Бенуа (общая для всех поисковых агентов) · 21.11.2026

Каждый поисковый файл: `{"version":1,"source":"<площадка>","fetched_at":"<ISO>","coverage":{...},"records":[...]}`.
`coverage` обязателен: `queries` (список реальных запросов), `pages_walked`, `hits_total_reported_by_source`, `records_kept`, `blocked` (что не открылось и почему: HTTP-код), `notes`.

Запись (`records[]`). Незнание = `null`, не догадка. Не копировать утверждения одного листа на весь том.
- `record_id` — `<площадка>:<идентификатор источника>`
- `artist_id` — `philippe-benoist` | `felix-benoist` | `uncertain-benoist` | `other` (Филипп и Феликс — разные лица; если из источника не ясно, `uncertain-benoist` и пояснение в `attribution_note`)
- `participants[]` — `{name, role_as_stated, role_normalized}` (`designer`/`lithographer`/`printer`/`publisher`/`engraver`/`author_of_text`/`unspecified`), `role_as_stated` дословно
- `original_title`, `translated_title_ru` (только если уверен), `series` (например «Paris dans sa splendeur», «Promenade dans Paris et ses environs», «Vues de Paris»), `plate_number`, `volume`
- `city`, `place` (здание/площадь), `country`, `geo_confidence` (`building`/`city`/`unknown`)
- `date_as_stated`, `technique_as_stated`, `object_type` (`print`/`drawing`/`book`/`volume`/`page_in_book`/`album`)
- `institution`, `accession`, `record_url` (страница записи; обязательна, проверенная), `iiif_manifest`, `image_url` (URL файла, если источник даёт), `image_width`, `image_height` (только реальные пиксели, иначе `null`)
- `rights_statement` (дословно из источника) и `rights_status`: `open_confirmed` (CC0/PDM/CC BY/CC BY-SA и т.п. именно на файл) | `rights_pending` | `link_only` | `unknown`
- `duplicate_hint` — строка-ключ композиции (нормализованное название + серия + номер), чтобы можно было сгруппировать оттиски; `impression_note`
- `verification_status`: `source_record_read` (запись открыта и прочитана) | `search_hit_only`
- `attribution_confidence`: `high`/`medium`/`low` + `attribution_note`

Границы: НИКАКИХ изображений с `rights_status` ≠ `open_confirmed` в git. Для `open_confirmed` картинки не скачивать (это делает отдельный этап), только URL. Вежливо: ≥1 с между запросами, UA `CityOnPaperResearch/0.9 (non-commercial museum atlas; github.com/zukevich-blip/-city-on-paper)`, 403/429/CAPTCHA не обходить — записать в `coverage.blocked`.
Писать только в свои файлы (указаны в поручении). Не коммитить, не пушить, не переключать ветки.
