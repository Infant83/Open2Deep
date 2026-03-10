from __future__ import annotations

"""Compatibility shim for older imports."""

from openproject_automation.o2d_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
