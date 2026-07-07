import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore


ROOT = Path(__file__).resolve().parent
KB_DIR = ROOT / "knowledge_base"


def load_documents(kb_dir: Path) -> list[Document]:
    docs: list[Document] = []
    for path in sorted(kb_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        chunks = [c.strip() for c in text.split("\n") if c.strip()]
        for i, chunk in enumerate(chunks, start=1):
            docs.append(
                Document(
                    page_content=chunk,
                    metadata={"source": path.name, "chunk": i},
                )
            )
    return docs


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Index local knowledge_base/*.txt into Pinecone")
    parser.add_argument("--index", default=os.getenv("PINECONE_INDEX_NAME", ""))
    parser.add_argument("--namespace", default=os.getenv("PINECONE_NAMESPACE", ""))
    parser.add_argument("--embedding-model", default=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY.")
    if not os.getenv("PINECONE_API_KEY"):
        raise RuntimeError("Missing PINECONE_API_KEY.")
    if not args.index:
        raise RuntimeError("Missing Pinecone index name. Set --index or PINECONE_INDEX_NAME.")

    documents = load_documents(KB_DIR)
    if not documents:
        raise RuntimeError("No .txt docs found in knowledge_base/.")

    embeddings = OpenAIEmbeddings(model=args.embedding_model)
    store = PineconeVectorStore(index_name=args.index, embedding=embeddings, namespace=args.namespace or None)
    store.add_documents(documents)

    print(
        f"Indexed {len(documents)} chunks into Pinecone index='{args.index}' "
        f"namespace='{args.namespace or '(default)'}'."
    )


if __name__ == "__main__":
    main()
