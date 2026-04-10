#!/usr/bin/env python3
"""
Разворачивает строки include: в текстовых списках geosite (формат v2dat / domain-list-community).

Ищет теги в файлах пула вида «<basename_dat>_<tag>.txt» (как выдаёт v2dat unpack).
Можно передать несколько каталогов пула: сначала локальный .dat, затем полный geosite-4.
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


def build_pool_maps(pool_dirs: list[pathlib.Path]) -> dict[str, pathlib.Path]:
    """tag (lower) -> path к файлу; последний пул перекрывает предыдущий."""
    m: dict[str, pathlib.Path] = {}
    for d in pool_dirs:
        if not d.is_dir():
            continue
        for p in d.iterdir():
            if not p.is_file() or not p.name.endswith(".txt"):
                continue
            stem = p.name[:-4]
            if "_" not in stem:
                continue
            # префикс = имя .dat без расширения: geosite-4 или geosite-ru-only
            tag: str | None = None
            for prefix in ("geosite-ru-only", "geosite-4"):
                sep = prefix + "_"
                if stem.startswith(sep):
                    tag = stem[len(sep) :]
                    break
            if tag is None:
                continue
            m[tag.lower()] = p
    return m


def load_flattened(pool: dict[str, pathlib.Path], start_path: pathlib.Path) -> list[str]:
    visited_files: set[pathlib.Path] = set()
    visited_includes: set[str] = set()
    collected: list[str] = []

    def process_file(path: pathlib.Path) -> None:
        rp = path.resolve()
        if rp in visited_files:
            return
        visited_files.add(rp)
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = strip_comment(raw)
                if not line or line.startswith("#"):
                    continue
                if line.startswith("include:"):
                    rest = line[len("include:") :].strip()
                    if not rest:
                        continue
                    target = rest.split()[0].strip().lower()
                    if target in visited_includes:
                        continue
                    visited_includes.add(target)
                    inc_path = pool.get(target)
                    if inc_path and inc_path.is_file():
                        process_file(inc_path)
                    # отсутствующий include — пропускаем (как в flatten_category_ru.py)
                else:
                    collected.append(line)

    process_file(start_path)

    seen: set[str] = set()
    out: list[str] = []
    for r in collected:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Flatten geosite text lists with include: resolution")
    ap.add_argument("input", type=pathlib.Path, help="входной .txt (одна категория)")
    ap.add_argument("-o", "--output", type=pathlib.Path, required=True)
    ap.add_argument(
        "-p",
        "--pool",
        type=pathlib.Path,
        action="append",
        default=[],
        help="каталог с разобранным geosite (можно несколько раз)",
    )
    args = ap.parse_args()
    if not args.pool:
        print("need at least one --pool", file=sys.stderr)
        sys.exit(1)
    pool = build_pool_maps(args.pool)
    rules = load_flattened(pool, args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as w:
        w.write(f"# flattened from {args.input.name}; rules={len(rules)}\n")
        for r in rules:
            w.write(r + "\n")
    print(f"wrote {args.output} ({len(rules)} rules)")


if __name__ == "__main__":
    main()
