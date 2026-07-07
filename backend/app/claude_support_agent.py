"""Customer support agent powered by Claude (Anthropic SDK with tool runner).

Drop-in alternative to the LangGraph-based SupportAgent. Claude autonomously
decides which tools to call and the SDK handles the agentic loop.

Select this backend by setting AGENT_BACKEND=claude in your environment.
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Literal

import anthropic
from anthropic import beta_tool
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
KB_DIR = ROOT / "knowledge_base"
LOGGER = logging.getLogger("claude_support_agent")

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _log_event(event: str, **fields: object) -> None:
    LOGGER.info(json.dumps({"event": event, **fields}, default=str))


# ---------------------------------------------------------------------------
# Knowledge base (reuses the same local/Pinecone logic)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


def _local_kb_search(query: str, top_k: int = 3) -> str:
    """Simple local keyword search over knowledge_base/*.txt files."""
    docs: list[tuple[str, str]] = []
    if KB_DIR.exists():
        for path in sorted(KB_DIR.glob("*.txt")):
            docs.append((path.name, path.read_text(encoding="utf-8")))

    if not docs:
        return "No knowledge base documents were found."

    q_tokens = set(_tokenize(query))
    scored = []
    for name, content in docs:
        score = len(q_tokens & set(_tokenize(content)))
        scored.append((score, name, content))

    ranked = sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]
    snippets = [f"[{name}]\n{content[:700]}" for _, name, content in ranked]
    return "\n\n".join(snippets)


def _pinecone_kb_search(query: str, top_k: int = 3) -> str:
    """Pinecone vector search for production RAG."""
    from langchain_openai import OpenAIEmbeddings
    from langchain_pinecone import PineconeVectorStore

    embeddings = OpenAIEmbeddings(
        model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    store = PineconeVectorStore(
        index_name=os.getenv("PINECONE_INDEX_NAME", ""),
        embedding=embeddings,
        namespace=os.getenv("PINECONE_NAMESPACE") or None,
    )
    docs = store.similarity_search(query, k=top_k)
    if not docs:
        return "No relevant documents found in vector database."
    snippets = []
    for doc in docs:
        source = str(doc.metadata.get("source", "unknown"))
        snippets.append(f"[{source}]\n{doc.page_content[:700]}")
    return "\n\n".join(snippets)


def _kb_search(query: str, top_k: int = 3) -> str:
    use_pinecone = os.getenv("USE_PINECONE", "false").lower() == "true"
    if use_pinecone:
        try:
            return _pinecone_kb_search(query, top_k)
        except Exception as exc:
            _log_event("kb_search_error", error=str(exc), fallback="local")
            return _local_kb_search(query, top_k)
    return _local_kb_search(query, top_k)


# ---------------------------------------------------------------------------
# Tools — defined with @beta_tool so the SDK auto-generates schemas
# ---------------------------------------------------------------------------

@beta_tool
def lookup_order_status(order_id: str) -> str:
    """Look up the current status of a customer order by its order ID.

    Args:
        order_id: The order ID to look up (e.g. "1001").
    """
    mocked = {
        "1001": "Order 1001 is in transit. Estimated delivery: 2026-03-06.",
        "1002": "Order 1002 was delivered on 2026-03-02.",
        "1003": "Order 1003 is awaiting carrier pickup.",
    }
    return mocked.get(order_id, f"Order {order_id} was not found in the demo system.")


@beta_tool
def book_appointment(customer_name: str, date: str, time: str, reason: str) -> str:
    """Book a support or demo appointment for a customer.

    Args:
        customer_name: Full name of the customer.
        date: Preferred date (e.g. "2026-03-15").
        time: Preferred time (e.g. "2:00 PM").
        reason: Reason for the appointment.
    """
    return (
        "Appointment requested successfully: "
        f"{customer_name}, {date} at {time}, reason: {reason}. "
        "(Demo mode: connect Google Calendar API in production.)"
    )


@beta_tool
def escalate_to_human(summary: str, priority: Literal["low", "medium", "high"]) -> str:
    """Escalate the conversation to a human support specialist.

    Use this when the customer is angry, mentions legal action, or the issue
    is too complex to resolve automatically.

    Args:
        summary: Brief summary of the customer issue and conversation context.
        priority: Escalation priority level.
    """
    return f"Escalation created with priority={priority}. Summary: {summary}"


@beta_tool
def search_knowledge_base(query: str) -> str:
    """Search the business knowledge base for information relevant to the customer's question.

    Use this to find answers about products, policies, FAQs, and support documentation.

    Args:
        query: The search query describing what information is needed.
    """
    return _kb_search(query)


TOOLS = [lookup_order_status, book_appointment, escalate_to_human, search_knowledge_base]

SYSTEM_PROMPT = """\
You are an autonomous customer support agent for a small business.

Your capabilities:
- Search the knowledge base for product info, FAQs, and policies
- Look up order status by order ID
- Book appointments for customers
- Escalate to a human specialist when needed

Guidelines:
1. Always search the knowledge base first when a customer asks a question about products or policies.
2. If the customer asks about an order, use the order lookup tool.
3. If the customer wants to book an appointment, use the booking tool.
4. Escalate to a human when:
   - The customer is angry, mentions legal action, or requests a chargeback
   - The issue is too complex to resolve with available tools
   - The customer explicitly asks to speak with a human
5. Be concise, professional, and empathetic.
6. If you cannot find an answer in the knowledge base, say so honestly and offer to escalate.
"""


# ---------------------------------------------------------------------------
# Agent class — same .chat() interface as the LangGraph SupportAgent
# ---------------------------------------------------------------------------

class ClaudeSupportAgent:
    """Customer support agent powered by Claude with autonomous tool use."""

    def __init__(self, model: str = "claude-haiku-4-5") -> None:
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for the Claude agent backend.")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self._sessions: dict[str, list[dict]] = {}

    def chat(
        self,
        session_id: str,
        customer_id: str,
        user_message: str,
        human_approved: bool = False,
    ) -> dict[str, object]:
        started_at = time.perf_counter()

        # Build message history for this session
        history = self._sessions.setdefault(session_id, [])

        # If human approved an escalation, inject that context
        if human_approved:
            user_message = (
                f"[SYSTEM: Human supervisor has approved escalation for this customer.] "
                f"{user_message}"
            )

        history.append({"role": "user", "content": user_message})

        # Run the autonomous tool loop via the SDK tool runner
        tools_used: list[str] = []
        final_text = ""
        status = "answered"
        route = "autonomous"
        handoff_summary = ""

        try:
            runner = self.client.beta.messages.tool_runner(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=history,
            )

            last_message = None
            for message in runner:
                last_message = message
                # Track which tools were called
                for block in message.content:
                    if block.type == "tool_use":
                        tools_used.append(block.name)

            # Extract final text response
            if last_message:
                for block in last_message.content:
                    if block.type == "text":
                        final_text = block.text
                        break

                # Append assistant response to session history
                history.append({"role": "assistant", "content": last_message.content})

            # Determine status based on tools used
            if "escalate_to_human" in tools_used:
                status = "escalated" if human_approved else "awaiting_human_approval"
                route = "escalate"
                handoff_summary = f"Escalation for customer {customer_id}: {user_message[:200]}"
            elif tools_used:
                status = "answered_with_tools"
                if any(t in tools_used for t in ("lookup_order_status", "book_appointment")):
                    route = "tools"
                else:
                    route = "docs"
            else:
                status = "answered"
                route = "docs"

        except anthropic.APIError as exc:
            _log_event("claude_api_error", error=str(exc))
            final_text = "I'm sorry, I encountered an error processing your request. Please try again."
            status = "error"

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        _log_event(
            "agent_turn",
            backend="claude",
            session_id=session_id,
            customer_id=customer_id,
            model=self.model,
            route=route,
            status=status,
            tools_used=tools_used,
            latency_ms=elapsed_ms,
        )

        return {
            "status": status,
            "response": final_text,
            "handoff_summary": handoff_summary,
            "route": route,
            "tools_used": tools_used,
        }
