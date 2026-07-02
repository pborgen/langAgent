import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Annotated, Literal, Protocol, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from .llm import build_chat_openai


ROOT = Path(__file__).resolve().parent
KB_DIR = ROOT / "knowledge_base"
LOGGER = logging.getLogger("support_agent")

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _log_event(event: str, **fields: object) -> None:
    payload = {"event": event, **fields}
    LOGGER.info(json.dumps(payload, default=str))


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


def choose_route(text: str) -> str:
    normalized = text.lower()
    escalate_terms = ["angry", "legal", "lawsuit", "chargeback", "speak to human", "agent"]
    tool_terms = ["order", "status", "track", "appointment", "book", "schedule"]

    if any(term in normalized for term in escalate_terms):
        return "escalate"
    if any(term in normalized for term in tool_terms):
        return "tools"
    return "docs"


class KnowledgeBase(Protocol):
    def search(self, query: str, top_k: int = 3) -> str:
        ...


class LocalKnowledgeBase:
    """Simple local retriever fallback."""

    def __init__(self, kb_dir: Path) -> None:
        self.docs: list[tuple[str, str]] = []
        if kb_dir.exists():
            for path in sorted(kb_dir.glob("*.txt")):
                self.docs.append((path.name, path.read_text(encoding="utf-8")))

    def search(self, query: str, top_k: int = 3) -> str:
        if not self.docs:
            return "No knowledge base documents were found."

        q_tokens = set(_tokenize(query))
        scored: list[tuple[int, str, str]] = []

        for name, content in self.docs:
            doc_tokens = set(_tokenize(content))
            score = len(q_tokens & doc_tokens)
            scored.append((score, name, content))

        ranked = sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]
        snippets = [f"[{name}]\n{content[:700]}" for _, name, content in ranked]
        return "\n\n".join(snippets)


class PineconeKnowledgeBase:
    """Pinecone-backed retriever for production-like RAG behavior."""

    def __init__(self, index_name: str, namespace: str = "") -> None:
        from langchain_openai import OpenAIEmbeddings
        from langchain_pinecone import PineconeVectorStore

        embeddings = OpenAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
        self.store = PineconeVectorStore(
            index_name=index_name,
            embedding=embeddings,
            namespace=namespace or None,
        )

    def search(self, query: str, top_k: int = 3) -> str:
        docs = self.store.similarity_search(query, k=top_k)
        if not docs:
            return "No relevant documents found in vector database."

        snippets = []
        for doc in docs:
            source = str(doc.metadata.get("source", "unknown"))
            snippets.append(f"[{source}]\n{doc.page_content[:700]}")
        return "\n\n".join(snippets)


def build_knowledge_base() -> KnowledgeBase:
    use_pinecone = os.getenv("USE_PINECONE", "false").lower() == "true"
    if not use_pinecone:
        return LocalKnowledgeBase(KB_DIR)

    index_name = os.getenv("PINECONE_INDEX_NAME", "").strip()
    namespace = os.getenv("PINECONE_NAMESPACE", "").strip()
    if not index_name:
        print("USE_PINECONE=true but PINECONE_INDEX_NAME is missing. Falling back to local retriever.", file=sys.stderr)
        _log_event("kb_init_warning", reason="missing_pinecone_index", fallback="local")
        return LocalKnowledgeBase(KB_DIR)

    try:
        _log_event("kb_init", provider="pinecone", index=index_name, namespace=namespace or "(default)")
        return PineconeKnowledgeBase(index_name=index_name, namespace=namespace)
    except Exception as exc:
        print(f"Failed to initialize Pinecone retriever ({exc}). Falling back to local retriever.", file=sys.stderr)
        _log_event("kb_init_error", error=str(exc), fallback="local")
        return LocalKnowledgeBase(KB_DIR)


@tool
def lookup_order_status(order_id: str) -> str:
    """Look up order status by order ID."""
    mocked = {
        "1001": "Order 1001 is in transit. Estimated delivery: 2026-03-06.",
        "1002": "Order 1002 was delivered on 2026-03-02.",
        "1003": "Order 1003 is awaiting carrier pickup.",
    }
    return mocked.get(order_id, f"Order {order_id} was not found in the demo system.")


@tool
def book_appointment(customer_name: str, date: str, time: str, reason: str) -> str:
    """Book a support or demo appointment."""
    return (
        "Appointment requested successfully: "
        f"{customer_name}, {date} at {time}, reason: {reason}. "
        "(Demo mode: connect Google Calendar API in production.)"
    )


@tool
def escalate_to_human(summary: str, priority: Literal["low", "medium", "high"]) -> str:
    """Escalate a conversation to a human support specialist."""
    return f"Escalation created with priority={priority}. Summary: {summary}"


TOOLS = [lookup_order_status, book_appointment, escalate_to_human]


class SupportState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    customer_id: str
    route: str
    retrieved_context: str
    final_response: str
    status: str
    handoff_summary: str
    human_approved: bool
    tools_used: list[str]


class SupportAgent:
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        load_dotenv()
        self.kb = build_knowledge_base()
        self.llm = build_chat_openai(model=model, base_url=base_url, api_key=api_key)
        self.tool_llm = self.llm.bind_tools(TOOLS)
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(SupportState)
        graph.add_node("retrieve", self._retrieve_context)
        graph.add_node("route", self._route)
        graph.add_node("answer_from_docs", self._answer_from_docs)
        graph.add_node("handle_with_tools", self._handle_with_tools)
        graph.add_node("escalate", self._escalate)

        graph.add_edge(START, "retrieve")
        graph.add_edge("retrieve", "route")
        graph.add_conditional_edges(
            "route",
            self._route_selector,
            {
                "docs": "answer_from_docs",
                "tools": "handle_with_tools",
                "escalate": "escalate",
            },
        )
        graph.add_edge("answer_from_docs", END)
        graph.add_edge("handle_with_tools", END)
        graph.add_edge("escalate", END)

        return graph.compile(checkpointer=MemorySaver())

    def _retrieve_context(self, state: SupportState) -> SupportState:
        latest = self._latest_user_text(state)
        return {"retrieved_context": self.kb.search(latest)}

    def _route(self, state: SupportState) -> SupportState:
        text = self._latest_user_text(state).lower()
        route = choose_route(text)
        _log_event("route_decision", route=route, preview=text[:120])
        return {"route": route}

    def _route_selector(self, state: SupportState) -> str:
        return state.get("route", "docs")

    def _answer_from_docs(self, state: SupportState) -> SupportState:
        latest = self._latest_user_text(state)
        prompt = [
            SystemMessage(
                content=(
                    "You are a customer support assistant for a small business. "
                    "Answer only from provided context. If missing, say you need a human agent."
                )
            ),
            HumanMessage(
                content=(
                    f"Customer question: {latest}\n\n"
                    f"Context:\n{state.get('retrieved_context', '')}\n\n"
                    "Return a concise answer."
                )
            ),
        ]
        reply = self.llm.invoke(prompt)
        return {
            "messages": [AIMessage(content=reply.content)],
            "final_response": str(reply.content),
            "status": "answered",
        }

    def _handle_with_tools(self, state: SupportState) -> SupportState:
        latest = self._latest_user_text(state)
        tools_used: list[str] = []
        messages: list[AnyMessage] = [
            SystemMessage(
                content=(
                    "You are a support agent. Use tools for order lookup, booking, or escalation. "
                    "If you call a tool, summarize the result for the customer."
                )
            ),
            HumanMessage(content=latest),
        ]

        first = self.tool_llm.invoke(messages)
        messages.append(first)

        if first.tool_calls:
            for call in first.tool_calls:
                name = call["name"]
                tools_used.append(name)
                args = call.get("args", {})
                tool_obj = next((t for t in TOOLS if t.name == name), None)
                tool_output = "Requested tool is unavailable."
                if tool_obj is not None:
                    tool_output = str(tool_obj.invoke(args))

                messages.append(ToolMessage(content=tool_output, tool_call_id=call["id"]))

            final = self.tool_llm.invoke(messages)
            _log_event("tool_calls", tools=tools_used, count=len(tools_used))
            return {
                "messages": [AIMessage(content=str(final.content))],
                "final_response": str(final.content),
                "status": "answered_with_tools",
                "tools_used": tools_used,
            }

        _log_event("tool_calls", tools=[], count=0)
        return {
            "messages": [AIMessage(content=str(first.content))],
            "final_response": str(first.content),
            "status": "answered_without_tools",
            "tools_used": [],
        }

    def _escalate(self, state: SupportState) -> SupportState:
        if not state.get("human_approved", False):
            summary = (
                "Escalation recommended. Reason: complex/high-risk customer issue. "
                f"Customer said: {self._latest_user_text(state)}"
            )
            return {
                "handoff_summary": summary,
                "final_response": (
                    "This request is marked for human review. "
                    "A specialist can approve and take over with full context."
                ),
                "status": "awaiting_human_approval",
                "tools_used": [],
            }

        escalation_result = escalate_to_human.invoke(
            {
                "summary": f"Approved escalation. Customer issue: {self._latest_user_text(state)}",
                "priority": "high",
            }
        )
        return {
            "final_response": str(escalation_result),
            "status": "escalated",
            "messages": [AIMessage(content=str(escalation_result))],
            "tools_used": ["escalate_to_human"],
        }

    @staticmethod
    def _latest_user_text(state: SupportState) -> str:
        for message in reversed(state.get("messages", [])):
            if isinstance(message, HumanMessage):
                return str(message.content)
        return ""

    def chat(
        self,
        session_id: str,
        customer_id: str,
        user_message: str,
        human_approved: bool = False,
    ) -> dict[str, object]:
        started_at = time.perf_counter()
        result = self.graph.invoke(
            {
                "messages": [HumanMessage(content=user_message)],
                "customer_id": customer_id,
                "human_approved": human_approved,
            },
            config={"configurable": {"thread_id": session_id}},
        )
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        _log_event(
            "agent_turn",
            session_id=session_id,
            customer_id=customer_id,
            route=result.get("route", "unknown"),
            status=result.get("status", "unknown"),
            tools_used=result.get("tools_used", []),
            latency_ms=elapsed_ms,
        )

        return {
            "status": result.get("status", "unknown"),
            "response": result.get("final_response", ""),
            "handoff_summary": result.get("handoff_summary", ""),
            "route": result.get("route", "unknown"),
            "tools_used": result.get("tools_used", []),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="LangGraph customer support agent demo")
    parser.add_argument("message", help="Customer message")
    parser.add_argument("--session-id", default="demo-session")
    parser.add_argument("--customer-id", default="cust-001")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument(
        "--base-url",
        default=None,
        help="OpenAI-compatible endpoint for a local LLM (e.g. http://localhost:11434/v1). "
        "Falls back to OPENAI_BASE_URL.",
    )
    parser.add_argument("--approve", action="store_true", help="Approve escalation if needed")
    args = parser.parse_args()

    load_dotenv()
    base_url = args.base_url or os.getenv("OPENAI_BASE_URL", "").strip() or None
    if not base_url and not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Set OPENAI_API_KEY in your environment or .env file, "
            "or pass --base-url / OPENAI_BASE_URL to use a local LLM."
        )

    agent = SupportAgent(model=args.model, base_url=base_url)
    output = agent.chat(
        session_id=args.session_id,
        customer_id=args.customer_id,
        user_message=args.message,
        human_approved=args.approve,
    )

    print("\n=== Support Agent Result ===")
    print(f"status: {output['status']}")
    print(f"response: {output['response']}")
    if output["handoff_summary"]:
        print(f"handoff_summary: {output['handoff_summary']}")


if __name__ == "__main__":
    main()
