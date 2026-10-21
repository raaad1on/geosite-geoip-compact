#!/usr/bin/env python3
"""Convert dist/text/*.txt domain/CIDR lists into JSON arrays (same basename)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def lines_from_txt(path: Path) -> list[str]:
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
        out.append(line)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dir",
        type=Path,
        default=Path("dist/text"),
        help="directory with unpacked .txt lists",
    )
    ap.add_argument(
        "--glob",
        default="*.txt",
        help="which text files to convert (README* skipped)",
    )
    args = ap.parse_args()

    root: Path = args.dir
    if not root.is_dir():
        raise SystemExit(f"missing directory: {root}")

    written = 0
    for txt in sorted(root.glob(args.glob)):
        if not txt.is_file():
            continue
        if txt.name.upper().startswith("README"):
            continue
        items = lines_from_txt(txt)
        out = txt.with_suffix(".json")
        out.write_text(
            json.dumps(items, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"{out}: {len(items)} items")
        written += 1

    if written == 0:
        raise SystemExit(f"no list files matched in {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
