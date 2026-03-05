#!/usr/bin/env python3
import sys
import pathlib


def load_flattened(data_dir: pathlib.Path, start_name: str) -> list[str]:
    visited: set[str] = set()
    collected: list[str] = []

    def process(name: str) -> None:
        if name in visited:
            return
        visited.add(name)

        path = data_dir / name
        if not path.exists():
            # если файла нет (например, опциональный список) — пропускаем.
            return

        with path.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                if line.startswith("include:"):
                    # include:category-ecommerce-ru @attr1 @-attr2
                    rest = line[len("include:") :].strip()
                    if not rest:
                        continue
                    target = rest.split()[0]
                    process(target)
                else:
                    # отбрасываем хвостовой комментарий
                    if "#" in line:
                        line = line.split("#", 1)[0].rstrip()
                    if line:
                        collected.append(line)

    process(start_name)

    # дедупликация с сохранением порядка
    seen: set[str] = set()
    unique: list[str] = []
    for rule in collected:
        if rule not in seen:
            seen.add(rule)
            unique.append(rule)
    return unique


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: flatten_category_ru.py <path-to-domain-list-community-data>", file=sys.stderr)
        sys.exit(1)

    data_dir = pathlib.Path(sys.argv[1]).resolve()
    if not data_dir.is_dir():
        print(f"Data dir not found: {data_dir}", file=sys.stderr)
        sys.exit(1)

    rules = load_flattened(data_dir, "category-ru")

    out_path = data_dir / "category-ru"
    with out_path.open("w", encoding="utf-8") as f:
        f.write("# AUTO-GENERATED: flattened category-ru with all includes resolved.\n")
        for r in rules:
            f.write(r + "\n")

    print(f"Wrote flattened category-ru with {len(rules)} rules to {out_path}")


if __name__ == "__main__":
    main()

