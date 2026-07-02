import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .app_config import AppConfig, load_config, validate_config
from .claude_support_agent import ClaudeSupportAgent
from .customer_support_agent import SupportAgent
from .ingestion_worker import start_worker
from .storage import Storage


LOGGER = logging.getLogger("support_api")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _log_event(event: str, **fields: object) -> None:
    LOGGER.info(json.dumps({"event": event, **fields}, default=str))


class ChatRequest(BaseModel):
    session_id: str
    customer_id: str
    message: str


class ApproveRequest(BaseModel):
    session_id: str
    customer_id: str
    message: str


class AgentResponse(BaseModel):
    status: str
    response: str
    handoff_summary: str
    route: str
    tools_used: list[str]


class SessionEvent(BaseModel):
    session_id: str
    customer_id: str
    user_message: str
    agent_response: str
    status: str
    route: str
    tools_used: list[str]
    human_approved: bool
    created_at: str


class SessionHistoryResponse(BaseModel):
    session_id: str
    events: list[SessionEvent]


class AnalyticsSummaryResponse(BaseModel):
    scope: str
    total_events: int
    escalations: int
    awaiting_approval: int
    tool_calls: int


class UploadContractResponse(BaseModel):
    accepted_content_types: list[str]
    max_file_size_mb: int
    notes: str


class UploadJobCreateRequest(BaseModel):
    tenant_id: str = Field(min_length=2)
    filename: str = Field(min_length=1)
    content_type: Literal["text/plain", "application/pdf", "text/html"]
    source: Literal["dashboard", "api", "widget"] = "dashboard"
    storage_uri: str = Field(min_length=3)


class UploadJobResponse(BaseModel):
    job_id: str
    tenant_id: str
    filename: str
    content_type: str
    source: str
    storage_uri: str
    status: str
    created_at: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    config: AppConfig = load_config()
    validation = validate_config(config)

    app.state.config = config
    app.state.storage = Storage(db_path=config.db_path or None)

    for warning in validation["warnings"]:
        _log_event("startup_warning", message=warning)

    if validation["errors"]:
        for error in validation["errors"]:
            _log_event("startup_error", message=error)
        if config.strict_startup_validation:
            raise RuntimeError("Startup validation failed. Fix env vars or set STRICT_STARTUP_VALIDATION=false.")

    app.state.agent = None
    if config.agent_backend == "claude":
        if config.anthropic_api_key:
            app.state.agent = ClaudeSupportAgent(model=config.anthropic_model)
            _log_event("startup_ready", backend="claude", agent_model=config.anthropic_model)
        else:
            _log_event("startup_partial", backend="claude", reason="missing_anthropic_api_key", agent_ready=False)
    else:
        if config.openai_api_key or config.openai_base_url:
            app.state.agent = SupportAgent(
                model=config.openai_model,
                base_url=config.openai_base_url or None,
                api_key=config.openai_api_key or None,
            )
            _log_event(
                "startup_ready",
                backend="langgraph",
                agent_model=config.openai_model,
                base_url=config.openai_base_url or "default",
            )
        else:
            _log_event("startup_partial", backend="langgraph", reason="missing_openai_api_key", agent_ready=False)

    start_worker(app.state.storage)

    yield

    app.state.storage.close()


app = FastAPI(title="Customer Support Agent API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    _log_event(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=latency_ms,
    )
    return response


def _get_agent_or_503(request: Request) -> SupportAgent | ClaudeSupportAgent:
    agent = getattr(request.app.state, "agent", None)
    if agent is None:
        backend = getattr(request.app.state, "config", None)
        hint = "ANTHROPIC_API_KEY" if backend and backend.agent_backend == "claude" else "OPENAI_API_KEY"
        raise HTTPException(
            status_code=503,
            detail=f"Agent is not ready. Set {hint} and restart the API.",
        )
    return agent


def _normalize_agent_response(result: dict[str, object]) -> dict[str, object]:
    return {
        "status": str(result.get("status", "unknown")),
        "response": str(result.get("response", "")),
        "handoff_summary": str(result.get("handoff_summary", "")),
        "route": str(result.get("route", "unknown")),
        "tools_used": list(result.get("tools_used", [])),
    }


def _record_session_event(
    request: Request,
    payload: ChatRequest | ApproveRequest,
    response_payload: dict[str, object],
    *,
    human_approved: bool,
) -> None:
    event = {
        "session_id": payload.session_id,
        "customer_id": payload.customer_id,
        "user_message": payload.message,
        "agent_response": response_payload["response"],
        "status": response_payload["status"],
        "route": response_payload["route"],
        "tools_used": response_payload["tools_used"],
        "human_approved": human_approved,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    request.app.state.storage.insert_session_event(event)


def _run_agent_turn(
    request: Request,
    payload: ChatRequest | ApproveRequest,
    *,
    human_approved: bool,
    event_name: str,
) -> dict[str, object]:
    agent = _get_agent_or_503(request)
    started_at = time.perf_counter()
    result = agent.chat(
        session_id=payload.session_id,
        customer_id=payload.customer_id,
        user_message=payload.message,
        human_approved=human_approved,
    )
    response_payload = _normalize_agent_response(result)
    _record_session_event(request, payload, response_payload, human_approved=human_approved)

    _log_event(
        event_name,
        session_id=payload.session_id,
        customer_id=payload.customer_id,
        status=response_payload["status"],
        route=response_payload["route"],
        tools_used=response_payload["tools_used"],
        latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
    )
    return response_payload


@app.get("/")
def index() -> FileResponse:
    index_file = FRONTEND_DIST / "index.html"
    if not index_file.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Frontend build not found. Run `cd frontend && npm install && npm run build` "
                "or use `npm run dev` for local UI development."
            ),
        )
    return FileResponse(index_file)


@app.get("/health")
def health(request: Request) -> dict[str, object]:
    config = getattr(request.app.state, "config", None)
    return {
        "status": "ok",
        "agent_ready": getattr(request.app.state, "agent", None) is not None,
        "agent_backend": config.agent_backend if config else "unknown",
    }


@app.post("/chat", response_model=AgentResponse)
def chat(payload: ChatRequest, request: Request) -> AgentResponse:
    response_payload = _run_agent_turn(request, payload, human_approved=False, event_name="chat_completed")
    return AgentResponse(**response_payload)


@app.post("/approve", response_model=AgentResponse)
def approve(payload: ApproveRequest, request: Request) -> AgentResponse:
    response_payload = _run_agent_turn(request, payload, human_approved=True, event_name="approve_completed")
    return AgentResponse(**response_payload)


@app.post("/v1/chat/messages", response_model=AgentResponse)
def v1_chat_messages(payload: ChatRequest, request: Request) -> AgentResponse:
    response_payload = _run_agent_turn(request, payload, human_approved=False, event_name="v1_chat_completed")
    return AgentResponse(**response_payload)


@app.post("/v1/escalations/approve", response_model=AgentResponse)
def v1_escalations_approve(payload: ApproveRequest, request: Request) -> AgentResponse:
    response_payload = _run_agent_turn(request, payload, human_approved=True, event_name="v1_approve_completed")
    return AgentResponse(**response_payload)


@app.get("/v1/sessions/{session_id}/messages", response_model=SessionHistoryResponse)
def v1_session_messages(session_id: str, request: Request) -> SessionHistoryResponse:
    events = request.app.state.storage.get_session_events(session_id)
    typed_events = [SessionEvent(**event) for event in events]
    return SessionHistoryResponse(session_id=session_id, events=typed_events)


@app.get("/v1/analytics/summary", response_model=AnalyticsSummaryResponse)
def v1_analytics_summary(request: Request, session_id: str | None = Query(default=None)) -> AnalyticsSummaryResponse:
    storage: Storage = request.app.state.storage
    if session_id:
        events = storage.get_session_events(session_id)
        scope = f"session:{session_id}"
    else:
        events = storage.get_all_session_events()
        scope = "global"

    total_events = len(events)
    escalations = sum(1 for event in events if event.get("status") == "escalated")
    awaiting_approval = sum(1 for event in events if event.get("status") == "awaiting_human_approval")
    tool_calls = sum(len(list(event.get("tools_used", []))) for event in events)
    return AnalyticsSummaryResponse(
        scope=scope,
        total_events=total_events,
        escalations=escalations,
        awaiting_approval=awaiting_approval,
        tool_calls=tool_calls,
    )


@app.get("/v1/uploads/contract", response_model=UploadContractResponse)
def get_upload_contract() -> UploadContractResponse:
    return UploadContractResponse(
        accepted_content_types=["text/plain", "application/pdf", "text/html"],
        max_file_size_mb=20,
        notes=(
            "Upload endpoint contract for ingestion MVP. "
            "Use /v1/uploads/jobs to register a queued indexing job record."
        ),
    )


@app.post("/v1/uploads/jobs", response_model=UploadJobResponse)
def create_upload_job(payload: UploadJobCreateRequest, request: Request) -> UploadJobResponse:
    created_at = datetime.now(timezone.utc).isoformat()
    job_id = f"job_{uuid4().hex[:10]}"

    job = {
        "job_id": job_id,
        "tenant_id": payload.tenant_id,
        "filename": payload.filename,
        "content_type": payload.content_type,
        "source": payload.source,
        "storage_uri": payload.storage_uri,
        "status": "queued",
        "created_at": created_at,
    }

    request.app.state.storage.insert_ingestion_job(job)
    _log_event("ingestion_job_created", job_id=job_id, tenant_id=payload.tenant_id, filename=payload.filename)
    return UploadJobResponse(**job)


@app.get("/v1/uploads/jobs/{job_id}", response_model=UploadJobResponse)
def get_upload_job(job_id: str, request: Request) -> UploadJobResponse:
    job = request.app.state.storage.get_ingestion_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Upload job not found")
    return UploadJobResponse(**job)


@app.get("/{full_path:path}")
def spa_fallback(full_path: str) -> FileResponse:
    # Keep API routes returning API errors instead of HTML fallback.
    reserved_prefixes = ("chat", "approve", "health", "v1", "openapi.json", "docs", "redoc", "assets")
    if full_path.startswith(reserved_prefixes):
        raise HTTPException(status_code=404, detail="Not found")

    index_file = FRONTEND_DIST / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found.")
    return FileResponse(index_file)
