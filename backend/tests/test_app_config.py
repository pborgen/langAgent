import pytest

from backend.app_config import load_config, validate_config
from backend.llm import build_chat_openai


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "AGENT_BACKEND",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "ANTHROPIC_API_KEY",
        "USE_PINECONE",
        "PINECONE_INDEX_NAME",
    ):
        monkeypatch.delenv(var, raising=False)


def test_openai_base_url_defaults_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    assert load_config().openai_base_url == ""


def test_openai_base_url_loaded_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    assert load_config().openai_base_url == "http://localhost:11434/v1"


def test_base_url_makes_openai_key_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("AGENT_BACKEND", "langgraph")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")

    result = validate_config(load_config())

    assert result["errors"] == []
    assert any("custom OpenAI-compatible endpoint" in w for w in result["warnings"])


def test_missing_key_and_base_url_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("AGENT_BACKEND", "langgraph")

    result = validate_config(load_config())

    assert any("OPENAI_API_KEY is required" in e for e in result["errors"])


def test_api_key_only_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("AGENT_BACKEND", "langgraph")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    result = validate_config(load_config())

    assert result["errors"] == []
    assert not any("custom OpenAI-compatible endpoint" in w for w in result["warnings"])


def test_build_chat_openai_threads_base_url_and_defaults_local_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_env(monkeypatch)
    client = build_chat_openai(model="llama3.1", base_url="http://localhost:11434/v1")

    assert client.model_name == "llama3.1"
    assert "http://localhost:11434/v1" in str(client.openai_api_base)
    # Local servers accept any key; a placeholder is supplied when none is set.
    assert client.openai_api_key.get_secret_value() == "local"
