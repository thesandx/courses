"""Module 2: sentence-aware chunking + the vector store."""

from .primitives import embed, cosine_similarity

HANDBOOK = (
    "Refunds are processed within 5 business days. "
    "Refund requests require the original order id. "
    "Password reset links are sent by email and expire after one hour. "
    "The pro plan includes priority support with a 4 hour response target. "
    "Invoices are emailed on the first day of each month."
)


def chunk_sentences(text: str, max_words: int = 14) -> list[str]:
    sentences = [s.strip() + "." for s in text.split(".") if s.strip()]
    chunks, current = [], ""
    for s in sentences:
        candidate = (current + " " + s).strip()
        if current and len(candidate.split()) > max_words:
            chunks.append(current)
            current = s
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


class VectorStore:
    def __init__(self):
        self._records: list[dict] = []

    def add(self, text: str, meta: dict | None = None) -> int:
        rid = len(self._records)
        self._records.append({"id": rid, "vector": embed(text),
                              "text": text, "meta": meta or {}})
        return rid

    def search(self, query: str, k: int = 2) -> list[tuple[float, dict]]:
        q = embed(query)
        scored = [(cosine_similarity(q, r["vector"]), r) for r in self._records]
        return sorted(scored, key=lambda p: -p[0])[:k]

    def __len__(self):
        return len(self._records)


def build_store() -> VectorStore:
    store = VectorStore()
    for chunk in chunk_sentences(HANDBOOK):
        store.add(chunk, meta={"source": "handbook.md"})
    return store
