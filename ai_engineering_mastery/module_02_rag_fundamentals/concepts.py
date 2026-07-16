"""
Module 2: RAG Fundamentals — Concepts in Action
===============================================
Run: python3 concepts.py

Chunking strategies, the indexing pipeline, and a working in-memory vector
database with top-k cosine search. Ends by showing keyword search fail where
semantic search succeeds — the reason vector stores exist.
"""

import hashlib
import math

# ---------------------------------------------------------------------------
# Shared primitives (built in Module 1)
# ---------------------------------------------------------------------------


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


# Real embedding models LEARN from data that "money back" and "refund" mean
# the same thing. Our hash embedding can't learn, so we hard-code a small
# synonym table to simulate that learned association — the geometry downstream
# is identical.
SYNONYMS = {
    "money": "refund", "refunds": "refund", "reimbursement": "refund",
    "password": "credential", "passwords": "credential",
    "holiday": "closure", "holidays": "closure",
}


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


# ============================================================================
# 1. Chunking strategies
# ============================================================================
print("=" * 70)
print("1. Chunking strategies")
print("=" * 70)

HANDBOOK = (
    "Refunds are processed within 5 business days. Customers on the pro plan "
    "get priority processing. To request a refund open a support ticket. "
    "Password resets are done from the security settings page. Reset links "
    "expire after one hour for safety. Contact support if your link expired. "
    "Our offices are closed on public holidays. Support replies within one "
    "business day. Emergency incidents are handled around the clock."
)


def chunk_fixed(text: str, size: int) -> list[str]:
    """Every `size` words, mid-sentence be damned."""
    words = text.split()
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)]


def chunk_sentences(text: str, max_words: int) -> list[str]:
    """Pack whole sentences until the next one would overflow max_words."""
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


def chunk_overlapping(text: str, size: int, overlap: int) -> list[str]:
    """Fixed-size with a sliding window: ideas near borders appear in two
    chunks, so a query matching the border still retrieves a complete idea."""
    words = text.split()
    step = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step)
            if words[i:i + size]]


fixed = chunk_fixed(HANDBOOK, 20)
sent = chunk_sentences(HANDBOOK, 20)
over = chunk_overlapping(HANDBOOK, 20, 5)
print(f"fixed(20): {len(fixed)} chunks; first ends mid-idea: ...{fixed[0][-30:]!r}")
print(f"sentence(≤20 words): {len(sent)} chunks; first: {sent[0]!r}")
print(f"overlapping(20, 5): {len(over)} chunks")

assert all(c.rstrip().endswith(".") for c in sent), \
    "sentence-aware chunks end on sentence boundaries"
# Overlap means consecutive chunks share words:
shared = set(over[0].split()) & set(over[1].split())
assert shared, "overlapping chunks must share border words"
print(f"words shared by overlapping chunks 0 and 1: {sorted(shared)[:4]} ...")

# ============================================================================
# 2 & 3. The indexing pipeline + a vector database
# ============================================================================
print()
print("=" * 70)
print("2. Indexing pipeline -> in-memory vector database")
print("=" * 70)


class VectorStore:
    """The honest core of every vector database: records that pair a vector
    with its text and metadata, plus exact top-k cosine search. Production
    stores add ANN indexes, persistence, and filters — not different math."""

    def __init__(self):
        self._records: list[dict] = []

    def add(self, text: str, meta: dict | None = None) -> int:
        record_id = len(self._records)
        self._records.append({
            "id": record_id,
            "vector": embed(text),
            "text": text,                    # a vector alone is write-only memory
            "meta": meta or {},
        })
        return record_id

    def search(self, query: str, k: int = 3,
               where: dict | None = None) -> list[tuple[float, dict]]:
        qvec = embed(query)
        candidates = self._records
        if where:                            # metadata filtering
            candidates = [r for r in candidates
                          if all(r["meta"].get(key) == val
                                 for key, val in where.items())]
        scored = [(cosine_similarity(qvec, r["vector"]), r) for r in candidates]
        return sorted(scored, key=lambda p: -p[0])[:k]

    def delete_by_source(self, source: str) -> int:
        """Re-indexing = delete by source, re-add. No retraining anything."""
        before = len(self._records)
        self._records = [r for r in self._records
                         if r["meta"].get("source") != source]
        return before - len(self._records)

    def __len__(self):
        return len(self._records)


store = VectorStore()
for chunk in chunk_sentences(HANDBOOK, 20):
    store.add(chunk, meta={"source": "handbook.md"})
store.add("The pro plan costs $49 per month.", meta={"source": "pricing.md"})
print(f"indexed {len(store)} chunks")

hits = store.search("how do I get my money back", k=2)
for score, rec in hits:
    print(f"  {score:.3f}  [{rec['meta']['source']}] {rec['text'][:60]}...")
assert "refund" in hits[0][1]["text"].lower(), \
    "semantic search must find the refund chunk without keyword overlap"

# Metadata filter: same query, restricted to pricing.md only.
filtered = store.search("how do I get my money back", k=2,
                        where={"source": "pricing.md"})
assert all(r["meta"]["source"] == "pricing.md" for _, r in filtered)
print(f"filtered search returned only pricing.md ({len(filtered)} hit)")

removed = store.delete_by_source("pricing.md")
assert removed == 1 and len(store) == len(chunk_sentences(HANDBOOK, 20))
print(f"re-indexing: removed {removed} pricing chunk, store back to handbook only")

# ============================================================================
# 4. Why not just keyword search?
# ============================================================================
print()
print("=" * 70)
print("3. Keyword search fails where semantic search succeeds")
print("=" * 70)


def keyword_score(query: str, text: str) -> float:
    """Naive keyword overlap: |query words ∩ text words| / |query words|."""
    q = set(query.lower().split())
    t = set(text.lower().split())
    return len(q & t) / len(q) if q else 0.0


query = "how do I get my money back"
refund_chunk = next(r["text"] for r in store._records
                    if "refund" in r["text"].lower())

kw = keyword_score(query, refund_chunk)
sem = cosine_similarity(embed(query), embed(refund_chunk))
print(f"query: {query!r}")
print(f"  keyword score vs refund chunk:  {kw:.3f}   <- string match: nothing shared")
print(f"  semantic score vs refund chunk: {sem:.3f}   <- subword/meaning overlap")
assert kw < 0.2, "keyword search scores the right answer near zero"
assert sem > kw, "the embedding sees similarity the keywords cannot"

# ...but keywords win on exact identifiers (why Module 3 builds hybrid search):
id_query = "error E-1234"
store.add("Error E-1234 means the reset link expired.", meta={"source": "kb.md"})
kw_id = keyword_score(id_query, "Error E-1234 means the reset link expired.")
print(f"  keyword score for exact ID {id_query!r}: {kw_id:.3f}  <- keywords still matter")
assert kw_id >= 0.5

print("\nAll Module 2 concept checks passed ✔")
