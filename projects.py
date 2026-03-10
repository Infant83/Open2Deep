#!/usr/bin/env python3
"""List OpenProject projects using the shared OpenProject client."""

from __future__ import annotations

import argparse
import json

from openproject_automation.config import AppConfig
from openproject_automation.openproject_client import OpenProjectClient


def format_table(rows: list[dict[str, object]]) -> str:
    headers = ["id", "identifier", "name", "href"]
    widths = {
        key: max(len(key), *(len(str(row.get(key, ""))) for row in rows)) if rows else len(key)
        for key in headers
    }

    lines = [
        "  ".join(key.upper().ljust(widths[key]) for key in headers),
        "  ".join("-" * widths[key] for key in headers),
    ]
    for row in rows:
        lines.append("  ".join(str(row.get(key, "")).ljust(widths[key]) for key in headers))
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name-contains", default="", help="Only print projects whose name or identifier contains this text.")
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of projects to return.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a table.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = AppConfig.from_openproject_env()
    client = OpenProjectClient(config)
    payload = client.list_projects(name_contains=args.name_contains, limit=args.limit)
    items = payload["items"]

    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        print(format_table(items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
