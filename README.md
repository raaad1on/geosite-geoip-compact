## geosite-geoip-compact

Компактные `geoip.dat` / `geosite.dat` для Xray-core и **`.srs` rule-set** для sing-box, собираемые на GitHub Actions.

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

### sing-box SRS (как у [SagerNet/sing-geosite](https://github.com/SagerNet/sing-geosite))

После сборки compact `.dat`:

1. **geoview** конвертирует теги в rule-set JSON (`domain` / `domain_suffix` / `ip_cidr`).
2. Версия rule-set нормализуется до **`1`** (поля домен/IP совместимы с sing-box **1.8+**; сырой geoview может писать version 3).
3. **`sing-box rule-set compile`** → бинарные **`dist/srs/*.srs`**.
4. CI валидирует:
   - `sing-box rule-set match` — `nalog.ru`, `gosuslugi.ru`, `yandex.ru` **матчатся** (через `domain_suffix: ru`); `google.com` — нет;
   - IP из списка RU матчится, `8.8.8.8` — нет;
   - `sing-box check` с local binary `rule_set` на оба файла.

Локально (нужны `geoview` и `sing-box` в `PATH`):

```bash
./scripts/build_and_validate_srs.sh
```

### Сборка (GitHub Actions)

`.github/workflows/build.yml`: клон → `category-ru` → `go run ./` → RunetFreedom extras → geoview compact `.dat` → **SRS + validate** → dist → релиз **`latest`**.

### Почему в `geosite-compact_category-ru.txt` нет `nalog.ru`, `gosuslugi.ru` и многих других `.ru`

Рекурсия **`include:`** и **`category-gov-ru` отрабатывают** — домены попадают в промежуточный набор при сборке [domain-list-community](https://github.com/v2fly/domain-list-community).

Дальше срабатывает **`polishList`** в `go run ./`: если в списке уже есть правило корневого домена **`ru`** (из `include:tld-ru`), то отдельные сайты вида **`*.ru`** считаются **избыточными** и **удаляются из protobuf**, потому что зона **`.ru` целиком** уже покрыта одним правилом. В Xray / sing-box это тот же смысл: **`domain_suffix: ru`** матчит и `nalog.ru`, и `gosuslugi.ru`.

Итого: **отсутствие строки в текстовом дампе ≠ отсутствие в бинарнике и ≠ «не матчится»**.

### `dist/` и релиз `latest`

Каждый успешный прогон на `main` (push / schedule ежедневно 03:00 UTC / workflow_dispatch):

1. Пересобирает `.dat` + `.srs` + `.txt`
2. Считает **краткий дифф** списков vs предыдущий коммит (`scripts/generate_dist_changelog.py`) и пишет в notes + `dist/CHANGELOG.md`
3. Коммитит `dist/` при изменениях (`[skip ci]`)
4. Всегда обновляет релиз **`latest`** (тег → HEAD, ассеты overwrite)
5. Если базы реально изменились — дополнительно создаёт dated-релиз `YYYY.MM.DD` (история в Releases)

Стабильные URL (всегда актуальные файлы):

```
https://github.com/raaad1on/geosite-geoip-compact/releases/download/latest/geoip-compact.dat
https://github.com/raaad1on/geosite-geoip-compact/releases/download/latest/geosite-compact.dat
https://github.com/raaad1on/geosite-geoip-compact/releases/download/latest/geoip-ru.srs
https://github.com/raaad1on/geosite-geoip-compact/releases/download/latest/geosite-category-ru.srs
https://github.com/raaad1on/geosite-geoip-compact/releases/download/latest/geoip-private.srs
https://github.com/raaad1on/geosite-geoip-compact/releases/download/latest/geosite-private.srs
https://github.com/raaad1on/geosite-geoip-compact/releases/download/latest/geosite-category-ads.srs
```

В репозитории: `dist/geoip-compact.dat`, `dist/geosite-compact.dat`, `dist/srs/*.srs`, `dist/text/*.txt`.

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

### sing-box

```json
{
  "route": {
    "rule_set": [
      {
        "type": "local",
        "tag": "geosite-category-ru",
        "format": "binary",
        "path": "/path/to/geosite-category-ru.srs"
      },
      {
        "type": "local",
        "tag": "geoip-ru",
        "format": "binary",
        "path": "/path/to/geoip-ru.srs"
      }
    ],
    "rules": [
      { "rule_set": "geosite-category-ru", "outbound": "direct" },
      { "rule_set": "geoip-ru", "outbound": "direct" }
    ]
  }
}
```

### Скрипты

- **`scripts/append_runet_extras_to_category_ru.py`** — основной для CI (Xray geosite).
- **`scripts/build_and_validate_srs.sh`** — compact `.dat` → `.srs` + проверка sing-box.
- **`scripts/flatten_category_ru.py`** — устарело для прод-сборки; только эксперименты.
- **`scripts/flatten_geosite_includes.py`** — вспомогательно для текстов v2dat.
