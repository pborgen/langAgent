"""knowledge_mcp — a Model Context Protocol (MCP) server exposing this
project's knowledge base over HTTP.

Why this exists
---------------
The customer support agent already knows how to (a) retrieve documents from a
knowledge base (local ``.txt`` files or Pinecone) and (b) talk to an LLM
(hosted OpenAI or a local Ollama/LM Studio/vLLM server). MCP is a standard way
to expose those same capabilities so that *any* MCP client — Claude Desktop,
Claude Code, or your own agent — can use them without importing this code.

This server reuses the exact same building blocks as the agent:
  * ``build_knowledge_base()`` — the local/Pinecone retriever
  * ``build_chat_openai()``    — the LLM client factory (works with Ollama)

MCP has three primitives, and this file demonstrates all three:
  * Tools     — actions a client can call (search / add / RAG answer)
  * Resources — read-only data a client can load as context (kb:// URIs)
  * Prompts   — reusable prompt templates a client can invoke

Run it
------
    python -m backend.knowledge_mcp.server

Then it serves streamable-HTTP at http://127.0.0.1:8848/mcp
(override with MCP_HOST / MCP_PORT / MCP_TRANSPORT env vars).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from backend.customer_support_agent import KB_DIR, build_knowledge_base
from backend.llm import build_chat_openai

load_dotenv()

# Host/port are read up front because FastMCP binds them at construction time.
_HOST = os.getenv("MCP_HOST", "127.0.0.1")
_PORT = int(os.getenv("MCP_PORT", "8848"))

mcp = FastMCP(
    "knowledge_mcp",
    instructions=(
        "Search and answer questions from the support knowledge base. "
        "Use `search_knowledge` for raw snippets, `get_answer` for a synthesized "
        "answer, and `add_document` to teach the KB something new."
    ),
    host=_HOST,
    port=_PORT,
)

# Build the retriever once at startup. Local (keyword) or Pinecone (vector)
# depending on USE_PINECONE — identical to what the support agent uses.
_kb = build_knowledge_base()


# ---------------------------------------------------------------------------
# Tools — actions the client can invoke
# ---------------------------------------------------------------------------

@mcp.tool()
def search_knowledge(query: str, top_k: int = 3) -> str:
    """Search the support knowledge base and return the most relevant snippets.

    Args:
        query: A natural-language question or keywords.
        top_k: How many document snippets to return (default 3).
    """
    return _kb.search(query, top_k=top_k)


@mcp.tool()
def add_document(title: str, text: str) -> str:
    """Add a new document to the local knowledge base.

    Writes ``<title>.txt`` into the knowledge_base directory and refreshes the
    in-memory retriever so the document is searchable immediately. This affects
    the *local* retriever only; for Pinecone, run the ingestion worker.

    Args:
        title: Short name for the document (used as the filename).
        text: The full document text to store.
    """
    global _kb

    safe = "".join(c if (c.isalnum() or c in "-_ ") else "_" for c in title).strip()
    safe = safe.replace(" ", "_")
    if not safe:
        return "Refused: title produced an empty filename."

    path = Path(KB_DIR) / f"{safe}.txt"
    if path.exists():
        return f"Refused: {path.name} already exists. Choose a different title."

    path.write_text(text, encoding="utf-8")
    _kb = build_knowledge_base()  # reload so the new doc is retrievable now
    return f"Added {path.name} ({len(text)} chars) to the knowledge base."


@mcp.tool()
def get_answer(question: str, top_k: int = 3) -> str:
    """Answer a question with retrieval-augmented generation (RAG).

    Retrieves context from the knowledge base, then asks the configured LLM
    (e.g. local Ollama via OPENAI_BASE_URL) to synthesize a grounded answer.

    Args:
        question: The user's question.
        top_k: How many snippets of context to retrieve (default 3).
    """
    context = _kb.search(question, top_k=top_k)
    llm = build_chat_openai(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    prompt = (
        "You are a support assistant. Answer the question using ONLY the context "
        "below. If the answer is not in the context, say you don't know.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\nAnswer:"
    )
    response = llm.invoke(prompt)
    return getattr(response, "content", str(response))


# ---------------------------------------------------------------------------
# Resources — read-only data the client can load as context (kb:// URIs)
# ---------------------------------------------------------------------------

def _read_kb_file(name: str) -> str:
    path = Path(KB_DIR) / name
    if not path.exists():
        return f"(no such document: {name})"
    return path.read_text(encoding="utf-8")


@mcp.resource("kb://faq")
def faq_resource() -> str:
    """The raw FAQ document."""
    return _read_kb_file("faq.txt")


@mcp.resource("kb://policies")
def policies_resource() -> str:
    """The raw policies document."""
    return _read_kb_file("policies.txt")


@mcp.resource("kb://documents")
def documents_resource() -> str:
    """A listing of every document currently in the local knowledge base."""
    names = sorted(p.name for p in Path(KB_DIR).glob("*.txt"))
    return "\n".join(names) if names else "(knowledge base is empty)"


# ---------------------------------------------------------------------------
# Prompt — a reusable template the client can invoke
# ---------------------------------------------------------------------------

@mcp.prompt()
def support_reply(question: str) -> str:
    """Draft a friendly support reply grounded in knowledge-base context."""
    context = _kb.search(question, top_k=3)
    return (
        "Use the following knowledge base context to write a friendly, concise "
        f"support reply.\n\nContext:\n{context}\n\nCustomer question: {question}"
    )


def main() -> None:
    # streamable-http is the current HTTP transport (endpoint: /mcp).
    # Set MCP_TRANSPORT=sse for the older SSE transport, or =stdio for local
    # subprocess use (Claude Desktop).
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    print(f"knowledge_mcp serving via {transport} on {_HOST}:{_PORT}")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
