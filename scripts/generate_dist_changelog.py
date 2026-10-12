#!/usr/bin/env python3
"""Compare previous vs new dist/text lists and write a short changelog."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import subprocess
from pathlib import Path


LISTS = (
    ("geosite category-ru", "dist/text/geosite-compact_category-ru.txt"),
    ("geosite category-ads", "dist/text/geosite-compact_category-ads.txt"),
    ("geosite private", "dist/text/geosite-compact_private.txt"),
    ("geoip ru", "dist/text/geoip-compact_ru.txt"),
    ("geoip private", "dist/text/geoip-compact_private.txt"),
)

BINARY = (
    ("geoip-compact.dat", "dist/geoip-compact.dat"),
    ("geosite-compact.dat", "dist/geosite-compact.dat"),
    ("geoip-ru.srs", "dist/srs/geoip-ru.srs"),
    ("geosite-category-ru.srs", "dist/srs/geosite-category-ru.srs"),
)

SAMPLE = 12
HISTORY_KEEP = 40


def load_lines(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    out: set[str] = set()
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line)
    return out


def git_show(rel: str, rev: str = "HEAD") -> bytes | None:
    try:
        return subprocess.check_output(
            ["git", "show", f"{rev}:{rel}"],
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None


def write_prev_from_git(prev_root: Path, rev: str = "HEAD") -> None:
    prev_root.mkdir(parents=True, exist_ok=True)
    for _, rel in (*LISTS, *BINARY):
        data = git_show(rel, rev)
        if data is None:
            continue
        dest = prev_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def fmt_sample(items: list[str], limit: int = SAMPLE) -> str:
    if not items:
        return "—"
    shown = items[:limit]
    extra = len(items) - len(shown)
    body = ", ".join(f"`{x}`" for x in shown)
    if extra > 0:
        body += f" … (+{extra})"
    return body


def build_section(prev_root: Path, new_root: Path) -> tuple[str, bool]:
    lines: list[str] = []
    changed = False

    lines.append("### Изменения в базах")
    lines.append("")
    lines.append("| Список | Было | Стало | + | − |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")

    details: list[str] = []
    for title, rel in LISTS:
        old = load_lines(prev_root / rel)
        new = load_lines(new_root / rel)
        added = sorted(new - old)
        removed = sorted(old - new)
        if added or removed or (not old and new):
            changed = True
        lines.append(
            f"| {title} | {len(old)} | {len(new)} | {len(added)} | {len(removed)} |"
        )
        if added or removed:
            details.append(f"**{title}**")
            if added:
                details.append(f"- добавлено: {fmt_sample(added)}")
            if removed:
                details.append(f"- удалено: {fmt_sample(removed)}")

    lines.append("")
    lines.append("| Файл | sha256 (было) | sha256 (стало) |")
    lines.append("| --- | --- | --- |")
    for title, rel in BINARY:
        old_h = sha256(prev_root / rel)
        new_h = sha256(new_root / rel)
        if old_h != new_h:
            changed = True
        lines.append(f"| `{title}` | `{old_h or '—'}` | `{new_h or '—'}` |")

    lines.append("")
    if details:
        lines.append("<details><summary>Примеры +/− (кратко)</summary>")
        lines.append("")
        lines.extend(details)
        lines.append("")
        lines.append("</details>")
        lines.append("")
    elif not changed:
        lines.append("_Содержимое списков и хеши бинарников не изменились относительно предыдущего коммита._")
        lines.append("")
    else:
        lines.append("_Изменились только бинарники/прочие артефакты (без диффа текстовых списков)._")
        lines.append("")

    return "\n".join(lines), changed


def prepend_history(changelog_path: Path, entry: str, keep: int = HISTORY_KEEP) -> None:
    import re

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    block = f"## {stamp}\n\n{entry.rstrip()}\n"
    old = changelog_path.read_text(encoding="utf-8") if changelog_path.is_file() else ""
    old_entries = re.findall(r"(?ms)^## .+?(?=^## |\Z)", old)
    merged = [block] + [e.rstrip() + "\n" for e in old_entries]
    merged = merged[:keep]
    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    changelog_path.write_text(
        "# История изменений compact geo\n\n" + "\n".join(merged).rstrip() + "\n",
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prev", type=Path, default=Path("work/prev-dist"))
    ap.add_argument("--new", type=Path, default=Path("."))
    ap.add_argument("--out", type=Path, default=Path("work/changelog_section.md"))
    ap.add_argument("--history", type=Path, default=Path("dist/CHANGELOG.md"))
    ap.add_argument("--rev", default="HEAD", help="git rev for previous dist")
    ap.add_argument("--skip-git-prev", action="store_true")
    ap.add_argument(
        "--history-only-if-changed",
        action="store_true",
        help="Append dist/CHANGELOG.md only when lists/binaries changed",
    )
    args = ap.parse_args()

    if not args.skip_git_prev:
        write_prev_from_git(args.prev, args.rev)

    section, changed = build_section(args.prev, args.new)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(section, encoding="utf-8")
    if changed or not args.history_only_if_changed:
        prepend_history(args.history, section)
    elif not args.history.is_file():
        args.history.parent.mkdir(parents=True, exist_ok=True)
        args.history.write_text(
            "# История изменений compact geo\n\n"
            "_Пока нет зафиксированных изменений: запись появится при первом диффе списков/бинарников._\n",
            encoding="utf-8",
        )

    flag = Path("work/dist_materially_changed")
    flag.write_text("1\n" if changed else "0\n", encoding="utf-8")

    print(section)
    print(f"materially_changed={int(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
