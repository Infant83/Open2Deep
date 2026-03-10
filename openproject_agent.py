#!/usr/bin/env python3
"""Backward-compatible wrapper for the Open2Deep CLI."""

from openproject_automation.o2d_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
