from __future__ import annotations

from langchain_openai import ChatOpenAI

from openproject_automation.config import AppConfig


def _profile(max_input_tokens: int) -> dict[str, int]:
    return {"max_input_tokens": max_input_tokens}


def build_text_model(config: AppConfig) -> ChatOpenAI:
    return ChatOpenAI(
        model=config.openai_model,
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
        timeout=config.llm_timeout_seconds,
        temperature=0,
        max_retries=2,
        streaming=False,
        profile=_profile(config.context_window_tokens),
    )


def build_vision_model(config: AppConfig) -> ChatOpenAI:
    return ChatOpenAI(
        model=config.openai_model_vision,
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
        timeout=config.llm_timeout_seconds,
        temperature=0,
        max_retries=2,
        streaming=False,
        profile=_profile(config.context_window_tokens),
    )
