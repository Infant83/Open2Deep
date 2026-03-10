from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from types import ModuleType
from typing import Any

from langchain_core.tools import BaseTool


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"custom_tool_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load custom tool module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_tools(module: ModuleType) -> list[Any]:
    if hasattr(module, "TOOLS"):
        tools = getattr(module, "TOOLS")
        if isinstance(tools, list):
            return tools
        raise RuntimeError(f"TOOLS must be a list in custom tool module: {module.__file__}")

    discovered: list[Any] = []
    for _, value in inspect.getmembers(module):
        if isinstance(value, BaseTool):
            discovered.append(value)
    return discovered


def load_custom_tools(custom_tools_dirs: tuple[Path, ...]) -> list[Any]:
    loaded_by_name: dict[str, Any] = {}
    for custom_tools_dir in custom_tools_dirs:
        if not custom_tools_dir.exists():
            continue
        for path in sorted(custom_tools_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            for tool in _extract_tools(_load_module(path)):
                name = getattr(tool, "name", getattr(tool, "__name__", path.stem))
                loaded_by_name[name] = tool
    return list(loaded_by_name.values())
