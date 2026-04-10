#!/usr/bin/env python3
"""
Оставляет исходный domain-list-community/data/category-ru (с include: и полной логикой go run).

Добавляет в конец файла только те строки из RunetFreedom, которых нет в эталонном распакованном
category-ru из уже собранного dlc.dat (сравнение по нормализованной строке правила).

Так не теряются resolveList / polishList для основной части списка.
"""
from __future__ import annotations

import argparse
import pathlib
import sys


def strip_comment(line: str) -> str:
    line = line.strip()
    if "#" in line:
        line = line.split("#", 1)[0].rstrip()
    return line


def iter_rules(path: pathlib.Path) -> list[str]:
    out: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = strip_comment(raw)
            if not line or line.startswith("#"):
                continue
            out.append(line)
    return out


def norm(s: str) -> str:
    return s.strip().lower()


def find_runet_file(unpack_dir: pathlib.Path, suffix: str) -> pathlib.Path | None:
    m = sorted(unpack_dir.glob(f"*_{suffix}.txt"))
    return m[0] if m else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("original_category_ru", type=pathlib.Path, help="unchanged data/category-ru from clone")
    ap.add_argument("official_unpack_txt", type=pathlib.Path, help="v2dat unpack category-ru from first dlc.dat")
    ap.add_argument("runet_unpack_dir", type=pathlib.Path)
    ap.add_argument("-o", "--output", type=pathlib.Path, required=True, help="path to write merged category-ru")
    args = ap.parse_args()

    if not args.original_category_ru.is_file():
        print(f"missing {args.original_category_ru}", file=sys.stderr)
        sys.exit(1)
    if not args.official_unpack_txt.is_file():
        print(f"missing {args.official_unpack_txt}", file=sys.stderr)
        sys.exit(1)
    if not args.runet_unpack_dir.is_dir():
        print(f"missing {args.runet_unpack_dir}", file=sys.stderr)
        sys.exit(1)

    official_norm = {norm(x) for x in iter_rules(args.official_unpack_txt)}
    extras: list[str] = []
    seen_extra: set[str] = set()

    for suffix in ("category-ru", "category-gov-ru", "ru-available-only-inside"):
        p = find_runet_file(args.runet_unpack_dir, suffix)
        if p is None:
            print(f"warning: no *_{suffix}.txt in runet unpack", file=sys.stderr)
            continue
        for line in iter_rules(p):
            k = norm(line)
            if not k or k in official_norm or k in seen_extra:
                continue
            seen_extra.add(k)
            extras.append(line)

    base = args.original_category_ru.read_text(encoding="utf-8")
    if not base.endswith("\n"):
        base += "\n"
    out = (
        base
        + "\n# APPENDED: RunetFreedom extras not present in official category-ru (v2fly dlc unpack).\n"
    )
    for e in extras:
        out += e + "\n"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(out, encoding="utf-8")
    print(f"Wrote {args.output}: +{len(extras)} runet lines (official unpack had {len(official_norm)} rules)")


if __name__ == "__main__":
    main()
