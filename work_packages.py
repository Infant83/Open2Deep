#!/usr/bin/env python3
"""List OpenProject work packages using the shared OpenProject client."""

from __future__ import annotations

import argparse
import json

from openproject_automation.config import AppConfig
from openproject_automation.openproject_client import OpenProjectClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="", help="Project ID, identifier, or exact name.")
    parser.add_argument("--search", default="", help="Filter by subject/description text.")
    parser.add_argument("--limit", type=int, default=25, help="Maximum number of work packages to return.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a compact table.")
    return parser.parse_args()


def format_table(rows: list[dict[str, object]]) -> str:
    headers = ["id", "subject", "status", "assignee", "dueDate"]
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


def main() -> int:
    args = parse_args()
    config = AppConfig.from_openproject_env()
    client = OpenProjectClient(config)
    payload = client.list_work_packages(
        project=args.project or None,
        search=args.search,
        limit=args.limit,
    )
    items = payload["items"]

    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        print(format_table(items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
