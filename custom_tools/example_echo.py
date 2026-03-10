from __future__ import annotations

from langchain_core.tools import tool


@tool
def echo_text(text: str) -> str:
    """Example custom tool. Replace this file or add new files in custom_tools/."""
    return text


TOOLS = [echo_text]
