## geosite-geoip-compact

Компактные `geoip.dat` и `geosite.dat` для Xray-core, собираемые на GitHub Actions.

### Идея

- **Совместимость конфига** — те же теги в правилах:
  - `geoip:ru`, `geoip:private`
  - `geosite:private`, **`geosite:category-ru`**, `geosite:category-ads`
- **Один тег `geosite:category-ru`** объединяет:
  1. Плоский **`category-ru`** из [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) (все `include:` развёрнуты рекурсивно).
  2. Дополнительно правила из [runetfreedom/russia-v2ray-rules-dat](https://github.com/runetfreedom/russia-v2ray-rules-dat) (`release/geosite.dat`):
     - **`category-gov-ru`**
     - **`ru-available-only-inside`** (домены, доступные только из РФ)
  3. Слияние **без повторов** (одинаковые строки правил отбрасываются).
- **`private`** и **`category-ads`** — из собранного `dlc.dat` community (как в `geoview`).
- **GeoIP** — срез [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat) только по **`RU`** и **`PRIVATE`**; перед релизом проверяется, что в `geoip-compact.dat` непустой список **`ru`**.

### Как это собирается (GitHub Actions)

Файл: `.github/workflows/build.yml`.

1. Клон **domain-list-community**.
2. **`scripts/flatten_category_ru.py`** — плоский `data/category-ru` из v2fly (рекурсивные `include:`).
3. Скачать **`geosite.dat`** с [raw …/russia-v2ray-rules-dat/release/geosite.dat](https://raw.githubusercontent.com/runetfreedom/russia-v2ray-rules-dat/release/geosite.dat).
4. **v2dat unpack** тегов `category-gov-ru`, `ru-available-only-inside`.
5. **`scripts/merge_runetfreedom_into_category_ru.py`** — дописывает в `category-ru` правила RunetFreedom, **дедупликация**.
6. **`go run ./`** в `domain-list-community` → **`dlc.dat`**.
7. Скачать **`geoip.dat`** Loyalsoldier.
8. **geoview** → `dist/geosite-compact.dat` (теги `private`, `category-ru`, `category-ads`) и `dist/geoip-compact.dat` (`RU`, `PRIVATE`).
9. Проверка: **v2dat** распаковывает `ru` из `geoip-compact.dat` (не пусто).
10. Экспорт текстов в **`dist/text/`** для контроля.
11. Коммит **`dist/`** при изменениях (`[skip ci]`).
12. **GitHub Release** [`latest`](https://github.com/raaad1on/geosite-geoip-compact/releases/tag/latest) после каждой успешной сборки на `main` (в т.ч. push, cron, ручной запуск):
    - тег **`latest`** принудительно переводится на **текущий HEAD** (включая коммит с обновлённым `dist/`), чтобы в интерфейсе GitHub отображался актуальный коммит;
    - к релизу прикрепляются **`geoip-compact.dat`**, **`geosite-compact.dat`** и **все `dist/text/*.txt`** (распакованные списки без упаковки в `.dat`);
    - описание релиза обновляется (время сборки UTC, SHA, ссылка на workflow).

### Структура `dist/`

- `dist/geoip-compact.dat` — только **`RU`**, **`PRIVATE`**.
- `dist/geosite-compact.dat` — **`private`**, **`category-ru`** (v2fly + RunetFreedom gov + only-inside, дедуп), **`category-ads`**.
- `dist/text/` — текстовые дампы для проверки.

### Пример в Xray

```json
"routing": {
  "geoip": { "path": "/path/to/geoip-compact.dat" },
  "geosite": { "path": "/path/to/geosite-compact.dat" }
}
```

```json
"DirectIp": ["geoip:private", "geoip:ru"],
"DirectSites": ["geosite:private", "geosite:category-ru"],
"BlockSites": ["geosite:category-ads"]
```

Используются только публичные списки и производные бинарники; секреты не нужны (`GITHUB_TOKEN`).

### Локальные скрипты

- `scripts/flatten_category_ru.py` — развернуть `include:` для v2fly `category-ru`.
- `scripts/merge_runetfreedom_into_category_ru.py` — подмешать RunetFreedom **после** flatten.
- `scripts/flatten_geosite_includes.py` — развернуть `include:` в текстовых списках v2dat (вспомогательно).
