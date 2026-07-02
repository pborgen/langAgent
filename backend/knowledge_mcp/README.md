# knowledge_mcp

A minimal **Model Context Protocol (MCP)** server that exposes this project's
knowledge base to any MCP client (Claude Desktop, Claude Code, or your own
agent). It's a learning project: small, but it touches all three MCP primitives
and reuses the *same* retriever and LLM factory as the customer support agent.

## What it exposes

**Tools** (actions a client can call)
| Tool | Description |
|------|-------------|
| `search_knowledge(query, top_k=3)` | Raw retrieval — returns the top matching KB snippets. |
| `add_document(title, text)` | Writes a new `.txt` doc into the KB and reloads the retriever. |
| `get_answer(question, top_k=3)` | Full RAG — retrieves context, then asks the LLM for a grounded answer. |

**Resources** (read-only context a client can load)
- `kb://faq` — the FAQ document
- `kb://policies` — the policies document
- `kb://documents` — a listing of everything in the KB

**Prompts** (reusable templates)
- `support_reply(question)` — drafts a KB-grounded support reply

## Run it

```bash
source .venv/bin/activate            # or use .venv/bin/python directly
python -m backend.knowledge_mcp.server
# → streamable-HTTP at http://127.0.0.1:8848/mcp
```

Point `get_answer` at your **local Ollama** instead of hosted OpenAI:

```bash
OPENAI_BASE_URL="http://localhost:11434/v1" OPENAI_MODEL="qwen2.5" \
  python -m backend.knowledge_mcp.server
```

## Configuration (env vars)

| Var | Default | Purpose |
|-----|---------|---------|
| `MCP_HOST` | `127.0.0.1` | Bind address |
| `MCP_PORT` | `8848` | Bind port |
| `MCP_TRANSPORT` | `streamable-http` | `streamable-http`, `sse`, or `stdio` |
| `OPENAI_BASE_URL` | — | Point at a local LLM (e.g. Ollama `…/v1`) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used by `get_answer` |
| `USE_PINECONE` | `false` | Use Pinecone vector retriever instead of local `.txt` |

## Try it from Python

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://127.0.0.1:8848/mcp") as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            print([t.name for t in (await s.list_tools()).tools])
            out = await s.call_tool("get_answer", {"question": "How long do refunds take?"})
            print(out.content[0].text)

asyncio.run(main())
```

## Connect it to Claude Desktop / Claude Code

For a local subprocess (stdio) integration, run with `MCP_TRANSPORT=stdio` and
register it in the client's MCP config, e.g.:

```json
{
  "mcpServers": {
    "knowledge": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "backend.knowledge_mcp.server"],
      "env": { "MCP_TRANSPORT": "stdio" },
      "cwd": "/absolute/path/to/langAgent"
    }
  }
}
```

## Ideas to extend (next learning steps)

- `get_session(id)` resource that reads past conversations from `storage.py`.
- `lookup_order_status` tool wrapping the agent's existing tool.
- Wire the Pinecone retriever (`USE_PINECONE=true`) for real vector search.
- Add auth via FastMCP's `token_verifier` for a network deployment.
