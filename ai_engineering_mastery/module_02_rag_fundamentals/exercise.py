"""
Module 2 Exercise: Build a Vector Database
==========================================
Goal
----
Implement an overlapping chunker and a `VectorStore` with top-k search,
metadata filtering, and re-indexing — the working core of RAG's supply chain.

Complete the TODOs below, then run:  python3 exercise.py
All assertions at the bottom must pass. Try it before opening solution.py!
"""

import hashlib
import math


# ---------------------------------------------------------------------------
# Provided: primitives from Module 1 (with the synonym-simulated embeddings)
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


# ---------------------------------------------------------------------------
# TODO 1 — chunk_overlapping(text, size, overlap)
# ---------------------------------------------------------------------------
# Split `text` into word-chunks of `size` words, where consecutive chunks
# share `overlap` words (step = size - overlap). Return a list of strings.
# Skip empty trailing windows. Ideas that straddle a border must appear
# whole in at least one chunk — that is the point of overlap.


# ---------------------------------------------------------------------------
# TODO 2 — class VectorStore
# ---------------------------------------------------------------------------
# Implement:
#   * add(text, meta=None) -> int
#       store {"id", "vector" (embed(text)), "text", "meta"} and return the id
#       (ids start at 0 and increment)
#   * search(query, k=3, where=None) -> list[(score, record)]
#       exact top-k cosine search, highest score first; if `where` is given,
#       only consider records whose meta matches EVERY key/value in `where`
#   * delete_by_source(source) -> int
#       remove records with meta["source"] == source, return how many
#   * __len__


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    text = " ".join(f"w{i}" for i in range(50))
    chunks = chunk_overlapping(text, size=20, overlap=5)
    assert chunks[0].split()[0] == "w0" and chunks[1].split()[0] == "w15", \
        "step must be size - overlap"
    assert set(chunks[0].split()) & set(chunks[1].split()), \
        "consecutive chunks must share words"
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
    assert hits[0][0] >= hits[1][0], "results must be sorted by score, desc"
    assert "refund" in hits[0][1]["text"].lower(), \
        "semantic search must surface the refund chunk"

    only_pricing = store.search("money", k=3, where={"source": "pricing.md"})
    assert len(only_pricing) == 1
    assert only_pricing[0][1]["meta"]["source"] == "pricing.md"

    assert store.delete_by_source("pricing.md") == 1
    assert len(store) == 2
    assert store.delete_by_source("nope.md") == 0

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Add upsert(source, chunks): delete_by_source + re-add — document refresh.
# 2. Return the top-k WITH a normalized score in [0, 1] and a citation string
#    like "handbook.md#3".
# 3. Time search() on 100k fake records to see when brute force stops scaling
#    (that measurement is what earns an ANN index).
