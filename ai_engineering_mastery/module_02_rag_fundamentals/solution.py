"""
Module 2 Solution: A Vector Database
====================================
Run: python3 solution.py — passes the same checks as exercise.py.
"""

import hashlib
import math


def tokenize(text: str) -> list[str]:
    tokens = []
    for word in text.lower().split():
        word = word.strip(".,!?;:()\"'")
        if not word:
            continue
        while len(word) > 4:
            tokens.append(word[:4])
            word = word[4:]
        tokens.append(word)
    return tokens


SYNONYMS = {"money": "refund", "refunds": "refund", "password": "credential",
            "passwords": "credential"}


def embed(text: str, dims: int = 64) -> list[float]:
    vec = [0.0] * dims
    normalized = " ".join(SYNONYMS.get(w.strip(".,!?;:()\"'").lower(), w)
                          for w in text.split())
    for token in tokenize(normalized):
        h = hashlib.sha256(token.encode()).digest()
        vec[h[0] % dims] += 1.0 if h[1] % 2 == 0 else -1.0
    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


# TODO 1 — the sliding window: border ideas survive in at least one chunk.
def chunk_overlapping(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    step = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step)
            if words[i:i + size]]


# TODO 2 — vector + text + meta per record; exact top-k search; filters.
class VectorStore:
    def __init__(self):
        self._records: list[dict] = []
        self._next_id = 0

    def add(self, text: str, meta: dict | None = None) -> int:
        record_id = self._next_id
        self._next_id += 1
        self._records.append({
            "id": record_id,
            "vector": embed(text),
            "text": text,
            "meta": meta or {},
        })
        return record_id

    def search(self, query: str, k: int = 3,
               where: dict | None = None) -> list[tuple[float, dict]]:
        qvec = embed(query)
        candidates = self._records
        if where:
            candidates = [r for r in candidates
                          if all(r["meta"].get(key) == val
                                 for key, val in where.items())]
        scored = [(cosine_similarity(qvec, r["vector"]), r) for r in candidates]
        return sorted(scored, key=lambda p: -p[0])[:k]

    def delete_by_source(self, source: str) -> int:
        before = len(self._records)
        self._records = [r for r in self._records
                         if r["meta"].get("source") != source]
        return before - len(self._records)

    def __len__(self):
        return len(self._records)


if __name__ == "__main__":
    text = " ".join(f"w{i}" for i in range(50))
    chunks = chunk_overlapping(text, size=20, overlap=5)
    assert chunks[0].split()[0] == "w0" and chunks[1].split()[0] == "w15"
    assert set(chunks[0].split()) & set(chunks[1].split())
    assert all(len(c.split()) <= 20 for c in chunks)

    store = VectorStore()
    i0 = store.add("Refunds are processed within 5 business days.",
                   meta={"source": "handbook.md"})
    i1 = store.add("Reset your password from the security settings page.",
                   meta={"source": "handbook.md"})
    i2 = store.add("The pro plan costs $49 per month.",
                   meta={"source": "pricing.md"})
    assert (i0, i1, i2) == (0, 1, 2)
    assert len(store) == 3

    hits = store.search("how do I get my money back", k=2)
    assert len(hits) == 2
    assert hits[0][0] >= hits[1][0]
    assert "refund" in hits[0][1]["text"].lower()

    only_pricing = store.search("money", k=3, where={"source": "pricing.md"})
    assert len(only_pricing) == 1
    assert only_pricing[0][1]["meta"]["source"] == "pricing.md"

    assert store.delete_by_source("pricing.md") == 1
    assert len(store) == 2
    assert store.delete_by_source("nope.md") == 0

    print("All solution checks passed ✔")
