from typing import Any

from fastapi.testclient import TestClient

from backend.support_api import app


class DummyAgent:
    def chat(self, session_id: str, customer_id: str, user_message: str, human_approved: bool = False) -> dict[str, Any]:
        if human_approved:
            return {
                "status": "escalated",
                "response": "Escalation approved and sent.",
                "handoff_summary": "",
                "route": "escalate",
                "tools_used": ["escalate_to_human"],
            }
        return {
            "status": "answered",
            "response": f"Echo: {user_message}",
            "handoff_summary": "",
            "route": "docs",
            "tools_used": [],
        }


def _reset_app_state(client: TestClient) -> None:
    client.app.state.session_events = {}


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "agent_ready" in body


def test_chat_returns_503_when_agent_not_ready() -> None:
    with TestClient(app) as client:
        _reset_app_state(client)
        client.app.state.agent = None
        response = client.post(
            "/chat",
            json={"session_id": "s1", "customer_id": "c1", "message": "hello"},
        )
    assert response.status_code == 503


def test_chat_endpoint_with_dummy_agent() -> None:
    with TestClient(app) as client:
        _reset_app_state(client)
        client.app.state.agent = DummyAgent()
        response = client.post(
            "/chat",
            json={"session_id": "s1", "customer_id": "c1", "message": "Where is my order?"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["route"] == "docs"


def test_approve_endpoint_with_dummy_agent() -> None:
    with TestClient(app) as client:
        _reset_app_state(client)
        client.app.state.agent = DummyAgent()
        response = client.post(
            "/approve",
            json={"session_id": "s1", "customer_id": "c1", "message": "approve"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "escalated"
    assert body["tools_used"] == ["escalate_to_human"]


def test_upload_contract_and_job_lifecycle() -> None:
    with TestClient(app) as client:
        _reset_app_state(client)
        contract_response = client.get("/v1/uploads/contract")
        assert contract_response.status_code == 200
        contract_body = contract_response.json()
        assert "application/pdf" in contract_body["accepted_content_types"]

        create_response = client.post(
            "/v1/uploads/jobs",
            json={
                "tenant_id": "tenant-1",
                "filename": "faq.pdf",
                "content_type": "application/pdf",
                "source": "dashboard",
                "storage_uri": "s3://bucket/tenant-1/faq.pdf",
            },
        )
        assert create_response.status_code == 200
        created = create_response.json()
        assert created["status"] == "queued"

        get_response = client.get(f"/v1/uploads/jobs/{created['job_id']}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["tenant_id"] == "tenant-1"


def test_upload_job_rejects_invalid_content_type() -> None:
    with TestClient(app) as client:
        _reset_app_state(client)
        response = client.post(
            "/v1/uploads/jobs",
            json={
                "tenant_id": "tenant-1",
                "filename": "faq.docx",
                "content_type": "application/msword",
                "source": "dashboard",
                "storage_uri": "s3://bucket/tenant-1/faq.docx",
            },
        )
    assert response.status_code == 422


def test_v1_chat_and_approve_endpoints() -> None:
    with TestClient(app) as client:
        _reset_app_state(client)
        client.app.state.agent = DummyAgent()

        chat_response = client.post(
            "/v1/chat/messages",
            json={"session_id": "s-v1", "customer_id": "c1", "message": "Hello"},
        )
        assert chat_response.status_code == 200
        chat_body = chat_response.json()
        assert chat_body["status"] == "answered"

        approve_response = client.post(
            "/v1/escalations/approve",
            json={"session_id": "s-v1", "customer_id": "c1", "message": "Approve this escalation"},
        )
        assert approve_response.status_code == 200
        approve_body = approve_response.json()
        assert approve_body["status"] == "escalated"


def test_v1_session_history_and_analytics() -> None:
    with TestClient(app) as client:
        _reset_app_state(client)
        client.app.state.agent = DummyAgent()

        client.post(
            "/v1/chat/messages",
            json={"session_id": "s-analytics", "customer_id": "c1", "message": "First message"},
        )
        client.post(
            "/v1/escalations/approve",
            json={"session_id": "s-analytics", "customer_id": "c1", "message": "Approve escalation"},
        )

        history_response = client.get("/v1/sessions/s-analytics/messages")
        assert history_response.status_code == 200
        history_body = history_response.json()
        assert history_body["session_id"] == "s-analytics"
        assert len(history_body["events"]) == 2

        summary_response = client.get("/v1/analytics/summary", params={"session_id": "s-analytics"})
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["scope"] == "session:s-analytics"
        assert summary["total_events"] == 2
