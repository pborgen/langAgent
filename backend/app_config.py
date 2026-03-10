import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    agent_backend: str  # "langgraph" or "claude"
    openai_api_key: str
    openai_model: str
    anthropic_api_key: str
    anthropic_model: str
    use_pinecone: bool
    pinecone_index_name: str
    strict_startup_validation: bool
    db_path: str


def _as_bool(raw: str, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> AppConfig:
    return AppConfig(
        agent_backend=os.getenv("AGENT_BACKEND", "langgraph").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5").strip(),
        use_pinecone=_as_bool(os.getenv("USE_PINECONE", "false")),
        pinecone_index_name=os.getenv("PINECONE_INDEX_NAME", "").strip(),
        strict_startup_validation=_as_bool(os.getenv("STRICT_STARTUP_VALIDATION", "false")),
        db_path=os.getenv("DB_PATH", "").strip(),
    )


def validate_config(config: AppConfig) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if config.agent_backend == "claude":
        if not config.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required when AGENT_BACKEND=claude.")
    else:
        if not config.openai_api_key:
            errors.append("OPENAI_API_KEY is required for chat/agent endpoints.")

    if config.agent_backend not in ("langgraph", "claude"):
        errors.append(f"AGENT_BACKEND must be 'langgraph' or 'claude', got '{config.agent_backend}'.")

    if config.use_pinecone and not config.pinecone_index_name:
        errors.append("USE_PINECONE=true requires PINECONE_INDEX_NAME.")

    if not config.use_pinecone:
        warnings.append("USE_PINECONE is false; using local fallback retriever.")

    return {"errors": errors, "warnings": warnings}
