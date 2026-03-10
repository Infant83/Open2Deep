from __future__ import annotations

from collections.abc import Mapping
import asyncio
import json
import os
from pathlib import Path
import re
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient


_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda match: os.getenv(match.group(1), ""), value)
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _expand_env(item) for key, item in value.items()}
    return value


def _load_one_config(config_path: Path) -> dict[str, Any]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"MCP config must be a JSON object: {config_path}")
    return _expand_env(payload)


def load_mcp_connections(config_paths: tuple[Path, ...]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for config_path in config_paths:
        if not config_path.exists():
            continue
        merged.update(_load_one_config(config_path))
    return merged


async def _aload_mcp_tools(config_paths: tuple[Path, ...]) -> list[BaseTool]:
    connections = load_mcp_connections(config_paths)
    if not connections:
        return []
    client = MultiServerMCPClient(connections, tool_name_prefix=True)
    return await client.get_tools()


def load_mcp_tools(config_paths: tuple[Path, ...]) -> list[BaseTool]:
    return asyncio.run(_aload_mcp_tools(config_paths))
