"""Shared helpers for constructing chat LLM clients.

Supports the hosted OpenAI API as well as any OpenAI-compatible local server
(Ollama, LM Studio, vLLM, llama.cpp) via a custom base URL.
"""
import os

from langchain_openai import ChatOpenAI


def build_chat_openai(
    model: str,
    base_url: str | None = None,
    api_key: str | None = None,
    temperature: float = 0,
) -> ChatOpenAI:
    """Build a ChatOpenAI client.

    When ``base_url`` (or the ``OPENAI_BASE_URL`` env var) points at a local /
    OpenAI-compatible server, a real key is usually not required, so a
    placeholder key is used unless one is supplied.
    """
    base_url = base_url or os.getenv("OPENAI_BASE_URL", "").strip() or None
    api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip() or None

    kwargs: dict = {"model": model, "temperature": temperature}
    if base_url:
        kwargs["base_url"] = base_url
        # Local servers accept any key; ChatOpenAI still requires one to be set.
        kwargs["api_key"] = api_key or "local"
    elif api_key:
        kwargs["api_key"] = api_key

    return ChatOpenAI(**kwargs)
