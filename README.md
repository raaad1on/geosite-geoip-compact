## geosite-geoip-compact

Компактные `geoip.dat` и `geosite.dat` для Xray-core, собираемые на GitHub Actions.

### Идея

- **Сохранить совместимость конфига**:
  - вы по‑прежнему используете только:
    - `geoip:ru`, `geoip:private`
    - `geosite:private`, `geosite:category-ru`, `geosite:category-ads`
  - конфиг вида:
    ```json
    "DirectIp": [
      "geoip:private",
      "geoip:ru"
    ],
    "DirectSites": [
      "geosite:private",
      "geosite:category-ru"
    ],
    "BlockSites": [
      "geosite:category-ads"
    ]
    ```
    остаётся без изменений.

- **Урезать базы**, оставив только нужные теги.
- **Корректно развернуть все `include:` для `category-ru`** рекурсивно (любой глубины), чтобы
  `geosite:category-ru` фактически включал:
  - `tld-ru`
  - `category-ecommerce-ru`
  - `category-entertainment-ru`
  - `category-gov-ru`
  - `category-retail-ru`
  - `category-travel-ru`
  - `mailru-group`
  - `yandex`
  - `category-bank-ru`
  - и все их вложения (например `avito`, `ozon`, `wildberries`, gov-домены и т.д.).

### Как это собирается в GitHub Actions

Workflow: `.github/workflows/build.yml`.

1. **Клонируем** [`v2fly/domain-list-community`](https://github.com/v2fly/domain-list-community).
2. **Плоско разворачиваем `category-ru`**:
   - скрипт `scripts/flatten_category_ru.py` рекурсивно обходит все `include:` в `data/category-ru`
     и связанных файлах (включая [`category-gov-ru`](https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/category-gov-ru)),
     и генерирует новый `data/category-ru` без `include:`, только с доменными правилами.
3. **Скачиваем оригинальные базы Loyalsoldier**:
   - `geoip.dat`, `geosite.dat` из `Loyalsoldier/v2ray-rules-dat`.
4. **Из `geosite.dat` распаковываем** только:
   - `private`
   - `category-ads`
   с помощью `v2dat` (в текстовый формат).
5. **Собираем свой `geosite-compact.dat`** (Go-программа `cmd/build-geosite-flat`):
   - тег `private` — из `geosite_private.txt`;
   - тег `category-ads` — из `geosite_category-ads.txt`;
   - тег `category-ru` — из плоского `domain-list-community/data/category-ru`
     (со всеми рекурсивными `include:`).
6. **Собираем компактный `geoip-compact.dat`** через `geoview`:
   - оставляем только `RU` и `PRIVATE`.
7. **Экспортируем текстовые списки** для верификации:
   - `dist/text/geoip-compact_private.txt`
   - `dist/text/geoip-compact_ru.txt`
   - `dist/text/geosite-compact_private.txt`
   - `dist/text/geosite-compact_category-ru.txt`
   - `dist/text/geosite-compact_category-ads.txt`
8. **Коммитим результат в `dist/`** в этот же репозиторий (без использования каких‑либо секретов;
   только стандартный `GITHUB_TOKEN`).

Workflow запускается:

- по `push` в `main/master` (кроме изменений только в `dist/**`);
- по расписанию (cron);
- вручную через `workflow_dispatch`.

### Структура `dist/`

- `dist/geoip-compact.dat` — бинарный GeoIP для Xray:
  - содержит только теги `RU` и `PRIVATE`.
- `dist/geosite-compact.dat` — бинарный GeoSite для Xray:
  - теги:
    - `private`
    - `category-ru` (со всеми `include:` и вложениями)
    - `category-ads`
- `dist/text/` — человекочитаемые экспортированные списки (для проверки/отладки).

### Как использовать в Xray

Подставьте в конфиг Xray пути/URL до файлов из этого репозитория, например:

```json
"routing": {
  "geoip": {
    "path": "/path/to/geoip-compact.dat"
  },
  "geosite": {
    "path": "/path/to/geosite-compact.dat"
  }
}
```

и оставьте ваши правила такими, как сейчас:

```json
"DirectIp": [
  "geoip:private",
  "geoip:ru"
],
"DirectSites": [
  "geosite:private",
  "geosite:category-ru"
],
"BlockSites": [
  "geosite:category-ads"
]
```

Никаких чувствительных данных в репозиторий не отправляется: используются только публичные списки
и их производные бинарные файлы.

