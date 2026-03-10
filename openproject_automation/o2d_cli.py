from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from textwrap import dedent

from openproject_automation.config import AppConfig


GLOBAL_CONFIG_TEMPLATE = dedent(
    """\
    [llm]
    base_url = "https://your-llm-endpoint.example/v1"
    model = "Qwen3-Coder-480B-A35B-Instruct"
    vision_model = "Llama-4-Scout"
    context_window_tokens = 128000
    timeout_seconds = 120

    [agent]
    enable_execute = true
    max_items_per_tool_call = 25
    max_text_chars = 1600

    [openproject]
    base_url = ""
    api_key = ""
    timeout_seconds = 30
    """
)

GLOBAL_AGENTS_TEMPLATE = dedent(
    """\
    # Global Open2Deep Instructions

    - Prefer concise reasoning and compact summaries.
    - Use ~/.o2d/skills and ~/.o2d/tools before reinventing repeatable workflows.
    - Confirm destructive or external mutations unless the user is already explicit.
    """
)

PROJECT_AGENTS_TEMPLATE = dedent(
    """\
    # Project Open2Deep Instructions

    - Put project-specific conventions here.
    - This file is loaded in addition to ~/.o2d/AGENTS_O2D.md.
    """
)

GLOBAL_PROMPT_TEMPLATE = dedent(
    """\
    Add extra system prompt guidance here when you want Open2Deep to consistently follow it.
    """
)

MCP_TEMPLATE = dedent(
    """\
    {
      "example_stdio": {
        "transport": "stdio",
        "command": "python",
        "args": ["/absolute/path/to/server.py"]
      }
    }
    """
)

EXAMPLE_TOOL = dedent(
    """\
    from __future__ import annotations

    from langchain_core.tools import tool


    @tool
    def echo_text(text: str) -> str:
        \"\"\"Example Open2Deep custom tool.\"\"\"
        return text


    TOOLS = [echo_text]
    """
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open2Deep: on-prem deepagents CLI with ~/.o2d and AGENTS_O2D.md support.")
    parser.add_argument("tokens", nargs="*", help="Subcommand or prompt text.")
    parser.add_argument("--message", help="Legacy single message execution.")
    parser.add_argument("--thread-id", default="o2d-session", help="Conversation thread ID for this process.")
    parser.add_argument("--list-tools", action="store_true", help="Legacy alias for 'o2d tools'.")
    parser.add_argument("--list-mcp", action="store_true", help="Legacy alias for 'o2d mcp'.")
    parser.add_argument("--global", dest="init_global", action="store_true", help="Used with 'init' to scaffold ~/.o2d.")
    parser.add_argument("--project", dest="init_project", action="store_true", help="Used with 'init' to scaffold ./.o2d.")
    return parser.parse_args()


def _write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def init_global_layout(o2d_home: Path) -> None:
    (o2d_home / "skills").mkdir(parents=True, exist_ok=True)
    (o2d_home / "tools").mkdir(parents=True, exist_ok=True)
    _write_if_missing(o2d_home / "config.toml", GLOBAL_CONFIG_TEMPLATE)
    _write_if_missing(o2d_home / "AGENTS_O2D.md", GLOBAL_AGENTS_TEMPLATE)
    _write_if_missing(o2d_home / "PROMPT_O2D.md", GLOBAL_PROMPT_TEMPLATE)
    _write_if_missing(o2d_home / "mcp_servers.json", MCP_TEMPLATE)
    _write_if_missing(o2d_home / "tools" / "example_echo.py", EXAMPLE_TOOL)


def init_project_layout(project_dir: Path) -> None:
    o2d_dir = project_dir / ".o2d"
    (o2d_dir / "skills").mkdir(parents=True, exist_ok=True)
    (o2d_dir / "tools").mkdir(parents=True, exist_ok=True)
    _write_if_missing(project_dir / "AGENTS_O2D.md", PROJECT_AGENTS_TEMPLATE)
    _write_if_missing(o2d_dir / "mcp_servers.json", MCP_TEMPLATE)
    _write_if_missing(o2d_dir / "tools" / "example_echo.py", EXAMPLE_TOOL)


def run_once(bundle, message: str, thread_id: str) -> str:
    from openproject_automation.agent import extract_text

    result = bundle.agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return extract_text(result)


def repl(bundle, thread_id: str) -> int:
    print(f"Open2Deep ready. cwd={bundle.config.cwd}")
    print(f"Thread: {thread_id}")
    print("Type 'exit' or 'quit' to stop.")
    while True:
        try:
            message = input("> ").strip()
        except EOFError:
            print()
            return 0

        if not message:
            continue
        if message.lower() in {"exit", "quit"}:
            return 0

        try:
            response = run_once(bundle, message, thread_id)
        except Exception as exc:  # pragma: no cover
            print(f"[error] {exc}")
            continue

        print(response or "[no text response]")


def doctor(config: AppConfig) -> int:
    print(f"cwd: {config.cwd}")
    print(f"o2d_home: {config.o2d_home}")
    print(f"local_o2d_dir: {config.local_o2d_dir}")
    print(f"model: {config.openai_model}")
    print(f"vision_model: {config.openai_model_vision}")
    print(f"base_url: {config.openai_base_url}")
    print(f"context_window_tokens: {config.context_window_tokens}")
    print(f"allow_execute: {config.allow_execute}")
    print(f"openproject_enabled: {config.has_openproject}")
    print("memory_paths:")
    for path in config.memory_paths:
        print(f"  - {path}")
    print("skills_paths:")
    for path in config.skills_paths:
        print(f"  - {path}")
    print("custom_tool_dirs:")
    for path in config.custom_tool_dirs:
        print(f"  - {path}")
    print("mcp_config_paths:")
    for path in config.mcp_config_paths:
        print(f"  - {path}")
    print("system_prompt_files:")
    for path in config.system_prompt_files:
        print(f"  - {path}")
    return 0


def main() -> int:
    args = parse_args()
    cwd = Path.cwd().resolve()
    o2d_home = Path(os.getenv("O2D_HOME") or os.getenv("ORDO_HOME") or os.getenv("OPUS_HOME") or "~/.o2d").expanduser().resolve()

    tokens = list(args.tokens)
    command = ""
    if args.list_tools:
        command = "tools"
    elif args.list_mcp:
        command = "mcp"
    if tokens and tokens[0] in {"init", "doctor", "tools", "mcp"}:
        command = tokens.pop(0)

    if command == "init":
        if not args.init_global and not args.init_project:
            args.init_global = True
        if args.init_global:
            init_global_layout(o2d_home)
            print(f"Initialized {o2d_home}")
        if args.init_project:
            init_project_layout(cwd)
            print(f"Initialized {cwd / '.o2d'} and {cwd / 'AGENTS_O2D.md'}")
        return 0

    try:
        config = AppConfig.from_env(cwd)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if command == "doctor":
        return doctor(config)

    try:
        from openproject_automation.agent import build_agent_bundle

        bundle = build_agent_bundle(config)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if command == "tools":
        for name in bundle.tool_names:
            print(name)
        return 0

    if command == "mcp":
        if not bundle.mcp_server_names:
            print("(no MCP servers configured)")
            return 0
        for name in bundle.mcp_server_names:
            print(name)
        return 0

    if args.message:
        print(run_once(bundle, args.message, args.thread_id))
        return 0

    if tokens:
        print(run_once(bundle, " ".join(tokens), args.thread_id))
        return 0

    return repl(bundle, args.thread_id)


if __name__ == "__main__":
    raise SystemExit(main())
