from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tomllib
from typing import Any


def _first_non_empty(*values: object, default: str = "") -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _env(*names: str) -> str:
    return _first_non_empty(*(os.getenv(name) for name in names))


def _env_bool(*names: str, default: bool = False) -> bool:
    value = _env(*names)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(*names: str, default: int) -> int:
    value = _env(*names)
    if not value:
        return default
    return int(value)


def _env_float(*names: str, default: float) -> float:
    value = _env(*names)
    if not value:
        return default
    return float(value)


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Config file must contain a TOML table: {path}")
    return payload


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _merge_toml_chain(paths: list[Path]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for path in paths:
        merged = _merge_dicts(merged, _read_toml(path))
    return merged


def _nested_get(payload: dict[str, Any], *path: str, default: Any = None) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def _absolute_posix(path: Path) -> str:
    return path.expanduser().resolve().as_posix()


def _collect_existing_paths(candidates: list[Path]) -> tuple[Path, ...]:
    existing: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        key = resolved.as_posix()
        if key in seen or not resolved.exists():
            continue
        seen.add(key)
        existing.append(resolved)
    return tuple(existing)


@dataclass(frozen=True)
class AppConfig:
    cwd: Path
    o2d_home: Path
    local_o2d_dir: Path
    root_dir: Path
    openproject_base_url: str
    openproject_api_key: str
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    openai_model_vision: str
    context_window_tokens: int
    max_items_per_tool_call: int
    max_text_chars: int
    allow_execute: bool
    memory_paths: tuple[str, ...]
    skills_paths: tuple[str, ...]
    custom_tool_dirs: tuple[Path, ...]
    mcp_config_paths: tuple[Path, ...]
    system_prompt_files: tuple[Path, ...]
    openproject_timeout_seconds: float
    llm_timeout_seconds: float

    @property
    def has_openproject(self) -> bool:
        return bool(self.openproject_base_url and self.openproject_api_key)

    @property
    def global_agents_file(self) -> Path:
        return self.o2d_home / "AGENTS_O2D.md"

    @property
    def project_agents_file(self) -> Path:
        return self.cwd / "AGENTS_O2D.md"

    @property
    def local_agents_file(self) -> Path:
        return self.local_o2d_dir / "AGENTS_O2D.md"

    @classmethod
    def _base_paths(cls, root_dir: str | Path | None = None) -> tuple[Path, Path, Path]:
        cwd = Path(root_dir or os.getcwd()).resolve()
        o2d_home = Path(os.getenv("O2D_HOME") or os.getenv("ORDO_HOME") or os.getenv("OPUS_HOME") or "~/.o2d").expanduser().resolve()
        local_o2d_dir = (cwd / ".o2d").resolve()
        return cwd, o2d_home, local_o2d_dir

    @classmethod
    def _base_files(
        cls,
        cwd: Path,
        o2d_home: Path,
        local_o2d_dir: Path,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[Path, ...], tuple[Path, ...], tuple[Path, ...]]:
        legacy_ordo_home = Path(os.getenv("ORDO_HOME") or "~/.ordo").expanduser().resolve()
        legacy_opus_home = Path(os.getenv("OPUS_HOME") or "~/.opus").expanduser().resolve()
        memory_candidates = [
            o2d_home / "AGENTS_O2D.md",
            cwd / "AGENTS_O2D.md",
            local_o2d_dir / "AGENTS_O2D.md",
            legacy_ordo_home / "AGENTS_ORDO.md",
            cwd / "AGENTS_ORDO.md",
            cwd / ".ordo" / "AGENTS_ORDO.md",
            legacy_opus_home / "AGENTS_OPUS.md",
            cwd / "AGENTS_OPUS.md",
            cwd / ".opus" / "AGENTS_OPUS.md",
            cwd / "AGENTS.md",
        ]
        memory_paths = tuple(_absolute_posix(path) for path in _collect_existing_paths(memory_candidates))

        skill_candidates = [
            o2d_home / "skills",
            local_o2d_dir / "skills",
            legacy_ordo_home / "skills",
            cwd / ".ordo" / "skills",
            legacy_opus_home / "skills",
            cwd / ".opus" / "skills",
            cwd / "skills",
        ]
        skills_paths = tuple(_absolute_posix(path) for path in _collect_existing_paths(skill_candidates))

        custom_tool_dirs = _collect_existing_paths(
            [
                o2d_home / "tools",
                local_o2d_dir / "tools",
                legacy_ordo_home / "tools",
                cwd / ".ordo" / "tools",
                legacy_opus_home / "tools",
                cwd / ".opus" / "tools",
                cwd / "custom_tools",
            ]
        )

        mcp_config_paths = _collect_existing_paths(
            [
                o2d_home / "mcp_servers.json",
                local_o2d_dir / "mcp_servers.json",
                legacy_ordo_home / "mcp_servers.json",
                cwd / ".ordo" / "mcp_servers.json",
                legacy_opus_home / "mcp_servers.json",
                cwd / ".opus" / "mcp_servers.json",
                cwd / "mcp_servers.json",
            ]
        )

        system_prompt_files = _collect_existing_paths(
            [
                o2d_home / "PROMPT_O2D.md",
                local_o2d_dir / "PROMPT_O2D.md",
                legacy_ordo_home / "PROMPT_ORDO.md",
                (cwd / ".ordo" / "PROMPT_ORDO.md").resolve(),
                legacy_opus_home / "PROMPT_OPUS.md",
                (cwd / ".opus" / "PROMPT_OPUS.md").resolve(),
                cwd / "PROMPT_O2D.md",
                cwd / "PROMPT_ORDO.md",
                cwd / "PROMPT_OPUS.md",
            ]
        )

        return memory_paths, skills_paths, custom_tool_dirs, mcp_config_paths, system_prompt_files

    @classmethod
    def _global_config_paths(cls, o2d_home: Path) -> list[Path]:
        legacy_ordo_home = Path(os.getenv("ORDO_HOME") or "~/.ordo").expanduser().resolve()
        legacy_opus_home = Path(os.getenv("OPUS_HOME") or "~/.opus").expanduser().resolve()
        return [legacy_opus_home / "config.toml", legacy_ordo_home / "config.toml", o2d_home / "config.toml"]

    @classmethod
    def _local_config_paths(cls, cwd: Path, local_o2d_dir: Path) -> list[Path]:
        return [
            (cwd / ".opus" / "config.toml").resolve(),
            (cwd / ".ordo" / "config.toml").resolve(),
            local_o2d_dir / "config.toml",
        ]

    @classmethod
    def from_openproject_env(cls, root_dir: str | Path | None = None) -> "AppConfig":
        cwd, o2d_home, local_o2d_dir = cls._base_paths(root_dir)
        memory_paths, skills_paths, custom_tool_dirs, mcp_config_paths, system_prompt_files = cls._base_files(
            cwd, o2d_home, local_o2d_dir
        )
        openproject_base_url = _env("OPENPROJECT_BASE_URL")
        openproject_api_key = _env("OPENPROJECT_API_KEY")
        if not openproject_base_url or not openproject_api_key:
            raise RuntimeError("Missing OPENPROJECT_BASE_URL or OPENPROJECT_API_KEY")
        return cls(
            cwd=cwd,
            o2d_home=o2d_home,
            local_o2d_dir=local_o2d_dir,
            root_dir=cwd,
            openproject_base_url=openproject_base_url,
            openproject_api_key=openproject_api_key,
            openai_api_key="",
            openai_base_url="",
            openai_model="",
            openai_model_vision="",
            context_window_tokens=128000,
            max_items_per_tool_call=_env_int("OPENPROJECT_AGENT_MAX_ITEMS", "O2D_MAX_ITEMS", "ORDO_MAX_ITEMS", "OPUS_MAX_ITEMS", default=25),
            max_text_chars=_env_int("OPENPROJECT_AGENT_MAX_TEXT_CHARS", "O2D_MAX_TEXT_CHARS", "ORDO_MAX_TEXT_CHARS", "OPUS_MAX_TEXT_CHARS", default=1600),
            allow_execute=False,
            memory_paths=memory_paths,
            skills_paths=skills_paths,
            custom_tool_dirs=custom_tool_dirs,
            mcp_config_paths=mcp_config_paths,
            system_prompt_files=system_prompt_files,
            openproject_timeout_seconds=_env_float("OPENPROJECT_AGENT_OPENPROJECT_TIMEOUT", "O2D_OPENPROJECT_TIMEOUT", "ORDO_OPENPROJECT_TIMEOUT", "OPUS_OPENPROJECT_TIMEOUT", default=30.0),
            llm_timeout_seconds=0.0,
        )

    @classmethod
    def from_env(cls, root_dir: str | Path | None = None) -> "AppConfig":
        cwd, o2d_home, local_o2d_dir = cls._base_paths(root_dir)

        global_config = _merge_toml_chain(cls._global_config_paths(o2d_home))
        local_config = _merge_toml_chain(cls._local_config_paths(cwd, local_o2d_dir))
        merged_config = _merge_dicts(global_config, local_config)

        llm_model = _first_non_empty(
            _env("OPENAI_MODEL", "O2D_MODEL", "ORDO_MODEL", "OPUS_MODEL"),
            _nested_get(merged_config, "llm", "model"),
        )
        if not llm_model:
            raise RuntimeError("Missing model configuration. Set OPENAI_MODEL or configure [llm].model in ~/.o2d/config.toml.")

        llm_base_url = _first_non_empty(
            _env("OPENAI_BASE_URL", "O2D_BASE_URL", "ORDO_BASE_URL", "OPUS_BASE_URL"),
            _nested_get(merged_config, "llm", "base_url"),
        )
        if not llm_base_url:
            raise RuntimeError("Missing LLM base URL. Set OPENAI_BASE_URL or configure [llm].base_url.")

        llm_api_key = _first_non_empty(
            _env("OPENAI_API_KEY", "OPENAI_APIK_KEY", "O2D_API_KEY", "ORDO_API_KEY", "OPUS_API_KEY"),
            _nested_get(merged_config, "llm", "api_key"),
        )
        if not llm_api_key:
            raise RuntimeError("Missing LLM API key. Set OPENAI_API_KEY or configure [llm].api_key.")

        openproject_base_url = _first_non_empty(
            _env("OPENPROJECT_BASE_URL"),
            _nested_get(merged_config, "openproject", "base_url"),
        )
        openproject_api_key = _first_non_empty(
            _env("OPENPROJECT_API_KEY"),
            _nested_get(merged_config, "openproject", "api_key"),
        )

        memory_paths, skills_paths, custom_tool_dirs, mcp_config_paths, system_prompt_files = cls._base_files(
            cwd, o2d_home, local_o2d_dir
        )

        return cls(
            cwd=cwd,
            o2d_home=o2d_home,
            local_o2d_dir=local_o2d_dir,
            root_dir=cwd,
            openproject_base_url=openproject_base_url,
            openproject_api_key=openproject_api_key,
            openai_api_key=llm_api_key,
            openai_base_url=llm_base_url,
            openai_model=llm_model,
            openai_model_vision=_first_non_empty(
                _env("OPENAI_MODEL_VISION", "VISION_MODEL", "O2D_VISION_MODEL", "ORDO_VISION_MODEL", "OPUS_VISION_MODEL"),
                _nested_get(merged_config, "llm", "vision_model"),
                llm_model,
            ),
            context_window_tokens=_env_int(
                "OPENPROJECT_AGENT_CONTEXT_WINDOW",
                "O2D_CONTEXT_WINDOW",
                "ORDO_CONTEXT_WINDOW",
                "OPUS_CONTEXT_WINDOW",
                default=int(_nested_get(merged_config, "llm", "context_window_tokens", default=128000)),
            ),
            max_items_per_tool_call=_env_int(
                "OPENPROJECT_AGENT_MAX_ITEMS",
                "O2D_MAX_ITEMS",
                "ORDO_MAX_ITEMS",
                "OPUS_MAX_ITEMS",
                default=int(_nested_get(merged_config, "agent", "max_items_per_tool_call", default=25)),
            ),
            max_text_chars=_env_int(
                "OPENPROJECT_AGENT_MAX_TEXT_CHARS",
                "O2D_MAX_TEXT_CHARS",
                "ORDO_MAX_TEXT_CHARS",
                "OPUS_MAX_TEXT_CHARS",
                default=int(_nested_get(merged_config, "agent", "max_text_chars", default=1600)),
            ),
            allow_execute=_env_bool(
                "OPENPROJECT_AGENT_ENABLE_EXECUTE",
                "O2D_ENABLE_EXECUTE",
                "ORDO_ENABLE_EXECUTE",
                "OPUS_ENABLE_EXECUTE",
                default=bool(_nested_get(merged_config, "agent", "enable_execute", default=True)),
            ),
            memory_paths=memory_paths,
            skills_paths=skills_paths,
            custom_tool_dirs=custom_tool_dirs,
            mcp_config_paths=mcp_config_paths,
            system_prompt_files=system_prompt_files,
            openproject_timeout_seconds=_env_float(
                "OPENPROJECT_AGENT_OPENPROJECT_TIMEOUT",
                "O2D_OPENPROJECT_TIMEOUT",
                "ORDO_OPENPROJECT_TIMEOUT",
                "OPUS_OPENPROJECT_TIMEOUT",
                default=float(_nested_get(merged_config, "openproject", "timeout_seconds", default=30.0)),
            ),
            llm_timeout_seconds=_env_float(
                "OPENPROJECT_AGENT_LLM_TIMEOUT",
                "O2D_LLM_TIMEOUT",
                "ORDO_LLM_TIMEOUT",
                "OPUS_LLM_TIMEOUT",
                default=float(_nested_get(merged_config, "llm", "timeout_seconds", default=120.0)),
            ),
        )
