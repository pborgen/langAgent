import os
import json
from typing import Any

import httpx
import redis
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


REDIS_URL = _env("REDIS_URL", "redis://127.0.0.1:6379/0")
VLLM_API_BASE = _env("VLLM_API_BASE", "http://127.0.0.1:8001")
VLLM_MODEL = _env("VLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "")
PROXY_API_KEY = os.getenv("PROXY_API_KEY", "")
MEMORY_MAX_MESSAGES = int(_env("MEMORY_MAX_MESSAGES", "20"))
REQUEST_TIMEOUT_SECONDS = float(_env("REQUEST_TIMEOUT_SECONDS", "120"))


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 512


class ChatResponse(BaseModel):
    session_id: str
    model: str
    response: str
    prompt_messages: int


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: list[dict[str, Any]]


app = FastAPI(title="vLLM Redis Memory Proxy", version="0.1.0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def _auth_or_401(authorization: str | None) -> None:
    if not PROXY_API_KEY:
        return
    expected = f"Bearer {PROXY_API_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _session_key(session_id: str) -> str:
    return f"vllm:session:{session_id}:messages"


def _load_messages(session_id: str) -> list[dict[str, str]]:
    rows = redis_client.lrange(_session_key(session_id), 0, -1)
    return [json.loads(row) for row in rows]


def _save_message(session_id: str, role: str, content: str) -> None:
    key = _session_key(session_id)
    payload = {"role": role, "content": content}
    redis_client.rpush(key, json.dumps(payload))
    redis_client.ltrim(key, -MEMORY_MAX_MESSAGES, -1)


def _call_vllm(messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int) -> str:
    headers = {"Content-Type": "application/json"}
    if VLLM_API_KEY:
        headers["Authorization"] = f"Bearer {VLLM_API_KEY}"

    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        response = client.post(f"{VLLM_API_BASE}/v1/chat/completions", headers=headers, json=body)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"vLLM upstream error: {response.text}")
    data = response.json()
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"Unexpected vLLM response shape: {data}") from exc


@app.get("/health")
def health() -> dict[str, str]:
    try:
        redis_client.ping()
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, authorization: str | None = Header(default=None)) -> ChatResponse:
    _auth_or_401(authorization)

    model = payload.model or VLLM_MODEL
    history = _load_messages(payload.session_id)
    history.append({"role": "user", "content": payload.message})

    assistant_text = _call_vllm(
        messages=history,
        model=model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )

    _save_message(payload.session_id, "user", payload.message)
    _save_message(payload.session_id, "assistant", assistant_text)
    prompt_messages = min(len(history), MEMORY_MAX_MESSAGES)

    return ChatResponse(
        session_id=payload.session_id,
        model=model,
        response=assistant_text,
        prompt_messages=prompt_messages,
    )


@app.get("/sessions/{session_id}/messages", response_model=SessionMessagesResponse)
def session_messages(session_id: str, authorization: str | None = Header(default=None)) -> SessionMessagesResponse:
    _auth_or_401(authorization)
    return SessionMessagesResponse(session_id=session_id, messages=_load_messages(session_id))


@app.delete("/sessions/{session_id}/messages")
def clear_session(session_id: str, authorization: str | None = Header(default=None)) -> dict[str, str]:
    _auth_or_401(authorization)
    redis_client.delete(_session_key(session_id))
    return {"status": "cleared"}
