from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from openproject_automation.config import AppConfig
from openproject_automation.llm import build_vision_model


def _to_data_url(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path.name)
    mime_type = mime_type or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _resolve_image_input(config: AppConfig, image_path_or_url: str) -> str:
    if image_path_or_url.startswith(("http://", "https://", "data:")):
        return image_path_or_url

    candidate = Path(image_path_or_url)
    if not candidate.is_absolute():
        candidate = (config.root_dir / candidate).resolve()
    if not candidate.exists():
        raise RuntimeError(f"Image not found: {candidate}")
    return _to_data_url(candidate)


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(part for part in parts if part).strip()
    return str(content)


def build_multimodal_tools(config: AppConfig) -> list[object]:
    vision_model = build_vision_model(config)

    @tool
    def analyze_image(image_path_or_url: str, question: str) -> str:
        """Use the dedicated vision model to inspect an image and answer a question about it."""
        image_url = _resolve_image_input(config, image_path_or_url)
        response = vision_model.invoke(
            [
                HumanMessage(
                    content=[
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ]
                )
            ]
        )
        return _message_text(response.content)

    return [analyze_image]
