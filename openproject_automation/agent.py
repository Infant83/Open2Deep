from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend, LocalShellBackend
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from openproject_automation.config import AppConfig
from openproject_automation.custom_tools import load_custom_tools
from openproject_automation.llm import build_text_model
from openproject_automation.mcp_loader import load_mcp_connections, load_mcp_tools
from openproject_automation.multimodal_tools import build_multimodal_tools
from openproject_automation.openproject_tools import build_openproject_tools


SYSTEM_PROMPT = """You are Open2Deep, an on-prem coding and operations agent focused on turning OpenProject work into deep operational context.

Execution model:
- Treat the current working directory as the main task root.
- You may use local filesystem tools, shell tools, MCP tools, custom tools, and OpenProject tools when available.
- Prefer the most direct tool for the task instead of re-deriving data manually.

Behavior:
- Keep context compact. Summarize large outputs into IDs, filenames, statuses, and short notes before continuing.
- If a result set is large, narrow it first.
- Before mutating external systems such as OpenProject, confirm the exact target and intended change unless the user has already been explicit.
- If both project-local and ~/.o2d guidance exist, follow the more specific project-local guidance for the current folder.
"""


OPENPROJECT_SUBAGENT_PROMPT = """You specialize in OpenProject operations.

Workflow:
- Resolve projects, types, statuses, priorities, and assignees before mutating tasks.
- Keep outputs concise and ID-driven.
- If the user asks to add, update, or comment, summarize what will change before doing it unless the instruction is already unambiguous.
"""


@dataclass
class AgentBundle:
    agent: Any
    config: AppConfig
    tool_names: list[str]
    mcp_server_names: list[str]


def _build_backend(config: AppConfig):
    root_dir = str(config.root_dir)
    if config.allow_execute:
        return lambda _: LocalShellBackend(
            root_dir=root_dir,
            virtual_mode=False,
            inherit_env=True,
        )
    return lambda _: FilesystemBackend(root_dir=root_dir, virtual_mode=False)


def _tool_name(tool: Any) -> str:
    return getattr(tool, "name", getattr(tool, "__name__", tool.__class__.__name__))


def _extra_prompt(config: AppConfig) -> str:
    sections: list[str] = []
    for path in config.system_prompt_files:
        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not content:
            continue
        sections.append(f"[{path.as_posix()}]\n{content}")
    if not sections:
        return ""
    return "\n\nAdditional Open2Deep prompt files:\n" + "\n\n".join(sections)


def build_agent_bundle(config: AppConfig | None = None) -> AgentBundle:
    resolved_config = config or AppConfig.from_env()
    openproject_tools = build_openproject_tools(resolved_config)
    multimodal_tools = build_multimodal_tools(resolved_config)
    custom_tools = load_custom_tools(resolved_config.custom_tool_dirs)
    mcp_tools = load_mcp_tools(resolved_config.mcp_config_paths)
    mcp_server_names = sorted(load_mcp_connections(resolved_config.mcp_config_paths).keys())
    tools: list[Any] = [*openproject_tools, *multimodal_tools, *custom_tools, *mcp_tools]

    subagents: list[dict[str, Any]] = []
    if openproject_tools:
        subagents.append(
            {
                "name": "openproject_ops",
                "description": "Use for OpenProject project/work package lookup, planning, creation, updates, and comments.",
                "system_prompt": OPENPROJECT_SUBAGENT_PROMPT,
                "tools": tools,
                "skills": list(resolved_config.skills_paths),
            }
        )

    memory_paths = list(resolved_config.memory_paths) or None
    skills_paths = list(resolved_config.skills_paths) or None

    agent = create_deep_agent(
        model=build_text_model(resolved_config),
        tools=tools,
        system_prompt=SYSTEM_PROMPT + _extra_prompt(resolved_config),
        subagents=subagents or None,
        skills=skills_paths,
        memory=memory_paths,
        backend=_build_backend(resolved_config),
        checkpointer=InMemorySaver(),
        name="o2d",
    )

    return AgentBundle(
        agent=agent,
        config=resolved_config,
        tool_names=sorted({_tool_name(tool) for tool in tools}),
        mcp_server_names=mcp_server_names,
    )


def extract_text(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            content = message.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(str(item.get("text", "")))
                return "\n".join(part for part in parts if part).strip()
            return str(content)
    return ""
