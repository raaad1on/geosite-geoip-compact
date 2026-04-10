#!/usr/bin/env python3
"""
Дополняет уже сгенерированный плоский domain-list-community/data/category-ru
правилами из RunetFreedom geosite.dat:
  - category-gov-ru
  - ru-available-only-inside

Порядок: база (flatten category-ru) → gov-ru → only-inside; дубликаты строк отбрасываются.
"""
from __future__ import annotations

import pathlib
import sys


def iter_rules_from_file(path: pathlib.Path) -> list[str]:
    out: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "#" in line:
                line = line.split("#", 1)[0].rstrip()
            if line:
                out.append(line)
    return out


def find_runet_file(unpack_dir: pathlib.Path, suffix: str) -> pathlib.Path | None:
    """suffix: 'category-gov-ru' или 'ru-available-only-inside' → *_<suffix>.txt"""
    matches = sorted(unpack_dir.glob(f"*_{suffix}.txt"))
    if not matches:
        return None
    if len(matches) > 1:
        print(f"warning: multiple matches for {suffix}, using {matches[0].name}", file=sys.stderr)
    return matches[0]


def main() -> None:
    if len(sys.argv) != 3:
        print(
            "Usage: merge_runetfreedom_into_category_ru.py <domain-list-community/data/category-ru> <v2dat-unpack-dir>",
            file=sys.stderr,
        )
        sys.exit(1)

    category_ru = pathlib.Path(sys.argv[1]).resolve()
    unpack_dir = pathlib.Path(sys.argv[2]).resolve()

    if not category_ru.is_file():
        print(f"category-ru file not found: {category_ru}", file=sys.stderr)
        sys.exit(1)
    if not unpack_dir.is_dir():
        print(f"unpack dir not found: {unpack_dir}", file=sys.stderr)
        sys.exit(1)

    seen: set[str] = set()
    merged: list[str] = []

    for line in iter_rules_from_file(category_ru):
        if line not in seen:
            seen.add(line)
            merged.append(line)

    gov = find_runet_file(unpack_dir, "category-gov-ru")
    inside = find_runet_file(unpack_dir, "ru-available-only-inside")

    if gov is None:
        print("error: *_category-gov-ru.txt not found in unpack dir", file=sys.stderr)
        sys.exit(1)
    if inside is None:
        print("error: *_ru-available-only-inside.txt not found in unpack dir", file=sys.stderr)
        sys.exit(1)

    n_gov = n_in = 0
    for path, label in (gov, "category-gov-ru"), (inside, "ru-available-only-inside"):
        for line in iter_rules_from_file(path):
            if line not in seen:
                seen.add(line)
                merged.append(line)
                if label == "category-gov-ru":
                    n_gov += 1
                else:
                    n_in += 1

    with category_ru.open("w", encoding="utf-8") as w:
        w.write(
            "# AUTO-GENERATED: flattened category-ru (v2fly) + RunetFreedom "
            "category-gov-ru + ru-available-only-inside (deduped).\n"
        )
        for r in merged:
            w.write(r + "\n")

    print(
        f"Wrote {category_ru}: {len(merged)} rules total "
        f"(+{n_gov} new from gov-ru, +{n_in} new from ru-available-only-inside)"
    )


if __name__ == "__main__":
    main()
