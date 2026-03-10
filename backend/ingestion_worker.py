"""Background ingestion worker that processes queued upload jobs.

Reads files from storage_uri (local file paths), extracts text, chunks it,
and writes to the knowledge_base/ directory (and optionally Pinecone).

Can be run standalone:  python -m backend.ingestion_worker
Or started as a background thread via start_worker().
"""

import json
import logging
import os
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

from .storage import Storage

ROOT = Path(__file__).resolve().parent
KB_DIR = ROOT / "knowledge_base"
LOGGER = logging.getLogger("ingestion_worker")

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _log_event(event: str, **fields: object) -> None:
    LOGGER.info(json.dumps({"event": event, **fields}, default=str))


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _extract_text(file_path: Path, content_type: str) -> str:
    """Extract plain text from a supported file."""
    if content_type == "text/plain":
        return file_path.read_text(encoding="utf-8")

    if content_type == "text/html":
        raw = file_path.read_text(encoding="utf-8")
        # Strip HTML tags with a simple approach (no extra dependency)
        import re
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    if content_type == "application/pdf":
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except ImportError:
            raise RuntimeError(
                "PDF ingestion requires pdfplumber. Install with: pip install pdfplumber"
            )

    raise ValueError(f"Unsupported content type: {content_type}")


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by character count."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------------
# Write to knowledge base
# ---------------------------------------------------------------------------

def _write_to_local_kb(filename: str, chunks: list[str], tenant_id: str) -> Path:
    """Write chunks as a .txt file in knowledge_base/ for local retriever."""
    KB_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).stem.replace(" ", "_")
    kb_file = KB_DIR / f"{tenant_id}_{safe_name}.txt"
    kb_file.write_text("\n".join(chunks), encoding="utf-8")
    return kb_file


def _index_to_pinecone(filename: str, chunks: list[str], tenant_id: str) -> int:
    """Index chunks into Pinecone (if configured)."""
    from langchain_core.documents import Document
    from langchain_openai import OpenAIEmbeddings
    from langchain_pinecone import PineconeVectorStore

    index_name = os.getenv("PINECONE_INDEX_NAME", "").strip()
    if not index_name:
        return 0

    documents = [
        Document(
            page_content=chunk,
            metadata={
                "source": filename,
                "tenant_id": tenant_id,
                "chunk": i,
            },
        )
        for i, chunk in enumerate(chunks, start=1)
    ]

    embeddings = OpenAIEmbeddings(
        model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    store = PineconeVectorStore(
        index_name=index_name,
        embedding=embeddings,
        namespace=os.getenv("PINECONE_NAMESPACE") or None,
    )
    store.add_documents(documents)
    return len(documents)


# ---------------------------------------------------------------------------
# Process a single job
# ---------------------------------------------------------------------------

def process_job(storage: Storage, job: dict) -> None:
    """Process one ingestion job: extract → chunk → store."""
    job_id = job["job_id"]
    storage.update_job_status(job_id, "processing")
    _log_event("job_processing", job_id=job_id, filename=job["filename"])

    try:
        file_path = Path(job["storage_uri"])
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {job['storage_uri']}")

        # Extract text
        text = _extract_text(file_path, job["content_type"])
        if not text.strip():
            raise ValueError("Extracted text is empty")

        # Chunk
        chunks = _chunk_text(text)
        _log_event("job_chunked", job_id=job_id, chunk_count=len(chunks))

        # Write to local KB
        kb_path = _write_to_local_kb(job["filename"], chunks, job["tenant_id"])
        _log_event("job_kb_written", job_id=job_id, kb_path=str(kb_path))

        # Optionally index to Pinecone
        use_pinecone = os.getenv("USE_PINECONE", "false").lower() == "true"
        if use_pinecone:
            try:
                count = _index_to_pinecone(job["filename"], chunks, job["tenant_id"])
                _log_event("job_pinecone_indexed", job_id=job_id, indexed_count=count)
            except Exception as exc:
                _log_event("job_pinecone_error", job_id=job_id, error=str(exc))

        storage.update_job_status(job_id, "completed")
        _log_event("job_completed", job_id=job_id, chunk_count=len(chunks))

    except Exception as exc:
        storage.update_job_status(job_id, "failed", error=str(exc))
        _log_event("job_failed", job_id=job_id, error=str(exc))


# ---------------------------------------------------------------------------
# Worker loop
# ---------------------------------------------------------------------------

def _worker_loop(storage: Storage, poll_interval: float = 5.0) -> None:
    """Poll for queued jobs and process them."""
    _log_event("worker_started")
    while True:
        try:
            jobs = storage.get_queued_jobs(limit=5)
            for job in jobs:
                process_job(storage, job)
        except Exception as exc:
            _log_event("worker_error", error=str(exc))
        time.sleep(poll_interval)


def start_worker(storage: Storage, poll_interval: float = 5.0) -> threading.Thread:
    """Start the ingestion worker as a daemon thread."""
    thread = threading.Thread(
        target=_worker_loop,
        args=(storage, poll_interval),
        daemon=True,
        name="ingestion-worker",
    )
    thread.start()
    _log_event("worker_thread_started")
    return thread


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    load_dotenv()
    store = Storage()
    _worker_loop(store)
