## geosite-geoip-compact

Компактные `geoip.dat` и `geosite.dat` для Xray-core, собираемые на GitHub Actions.

### Идея

- **Совместимость конфига** — те же теги:
  - `geoip:ru`, `geoip:private`
  - `geosite:private`, **`geosite:category-ru`**, `geosite:category-ads`
- **`geosite:category-ru`**:
  1. Сохраняется **исходный** `data/category-ru` из [domain-list-community](https://github.com/v2fly/domain-list-community) со всеми **`include:`** — дальше работает штатный **`go run ./`**: **`resolveList`**, фильтры **`@` / `@-`** на включениях, **`polishList`**, **`&`**.
  2. Собирается **эталонный** `dlc.dat`, из него **v2dat unpack** `category-ru` (уже полностью развёрнутый список).
  3. Из [runetfreedom/russia-v2ray-rules-dat](https://github.com/runetfreedom/russia-v2ray-rules-dat) распаковываются **`category-ru`**, **`category-gov-ru`**, **`ru-available-only-inside`**.
  4. В конец **оригинального** `category-ru` дописываются только строки RunetFreedom, **которых нет** в эталонном unpack (нормализованное сравнение), см. **`scripts/append_runet_extras_to_category_ru.py`**.
  5. Снова **`go run ./`** → финальный **`dlc.dat`**.

**Почему не «плоский flatten» в Python:** скрипт `flatten_category_ru.py` обходил только текст и **не** повторял логику Go (фильтры атрибутов на `include:`, `polishList`). **Почему не подмена всего файла распакованным списком:** повторный `go run` снова прогоняет `polishList` и может **схлопнуть** уже корректный набор правил (число записей падало).

- **`private`**, **`category-ads`** — из финального `dlc.dat` (**geoview**).
- **GeoIP** — срез [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat): **`RU`**, **`PRIVATE`**.

### Сборка (GitHub Actions)

`.github/workflows/build.yml`: клон → копия `category-ru` → `go run ./` → unpack эталона → RunetFreedom → append extras → `go run ./` → geoview → dist → релиз **`latest`**.

### `dist/`

- `dist/geoip-compact.dat`, `dist/geosite-compact.dat`, `dist/text/*.txt`

### Xray

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

### Скрипты

- **`scripts/append_runet_extras_to_category_ru.py`** — основной для CI.
- **`scripts/flatten_category_ru.py`** — устарело для прод-сборки; только эксперименты.
- **`scripts/flatten_geosite_includes.py`** — вспомогательно для текстов v2dat.
