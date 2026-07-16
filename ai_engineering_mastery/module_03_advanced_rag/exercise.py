"""
Module 3 Exercise: Fusion, Reranking, and Retrieval Evals
=========================================================
Goal
----
Implement RRF fusion, retrieve-then-rerank, and the three retrieval metrics —
then use your own metrics to prove your own pipeline beats the naive baseline.

Complete the TODOs below, then run:  python3 exercise.py
All assertions at the bottom must pass. Try it before opening solution.py!
"""

import hashlib
import math


# ---------------------------------------------------------------------------
# Provided: primitives and rankers from concepts.py
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


SYNONYMS = {"money": "refund", "refunds": "refund"}


def embed(text: str, dims: int = 64) -> list[float]:
    vec = [0.0] * dims
    normalized = " ".join(SYNONYMS.get(w.strip(".,!?;:()\"'").lower(), w)
                          for w in text.split())
    for token in tokenize(normalized):
        h = hashlib.sha256(token.encode()).digest()
        vec[h[0] % dims] += 1.0 if h[1] % 2 == 0 else -1.0
    return vec


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


CORPUS = [
    "Error E-1234 means the reset link has expired; request a new one.",       # 0
    "Refunds are processed within 5 business days of the request.",            # 1
    "To request a refund, open a support ticket from your dashboard.",         # 2
    "The pro plan includes priority support and a 99.9% uptime SLA.",          # 3
    "Reboot the gateway appliance by holding the power button 10 seconds.",    # 4
    "Invoices are emailed on the first day of each month.",                    # 5
]


def keyword_rank(query: str, corpus: list[str]) -> list[int]:
    n = len(corpus)
    doc_words = [set(d.lower().split()) for d in corpus]

    def idf(word):
        containing = sum(1 for ws in doc_words if word in ws)
        return math.log((n + 1) / (containing + 0.5))

    scores = [(sum(idf(w) for w in query.lower().split() if w in ws), i)
              for i, ws in enumerate(doc_words)]
    return [i for _, i in sorted(scores, key=lambda p: -p[0])]


def vector_rank(query: str, corpus: list[str]) -> list[int]:
    q = embed(query)
    scores = [(cosine_similarity(q, embed(d)), i) for i, d in enumerate(corpus)]
    return [i for _, i in sorted(scores, key=lambda p: -p[0])]


def cross_encoder_score(query: str, doc: str) -> float:
    def norm(text):
        return {SYNONYMS.get(w, w) for w in
                (x.strip(".,!?;:()\"'").lower() for x in text.split()) if w}
    q, d = norm(query), norm(doc)
    return len(q & d) / len(q) if q else 0.0


# ---------------------------------------------------------------------------
# TODO 1 — rrf_fuse(rankings, k=60)
# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion over multiple rankings (lists of doc ids, best
# first). Each ranking contributes 1 / (k + rank) per doc, where the best
# doc has rank 1. Return all doc ids sorted by fused score, best first.
# Fuse RANKS, not scores — BM25 and cosine scales are incomparable.


# ---------------------------------------------------------------------------
# TODO 2 — retrieve_then_rerank(query, corpus, candidates=4, top=2)
# ---------------------------------------------------------------------------
# Stage 1: hybrid shortlist — rrf_fuse keyword_rank + vector_rank, take the
#          first `candidates` doc ids.
# Stage 2: reorder the shortlist by cross_encoder_score(query, corpus[i]),
#          highest first. Return the first `top` ids.


# ---------------------------------------------------------------------------
# TODO 3 — recall_at_k, precision_at_k, mrr
# ---------------------------------------------------------------------------
# recall_at_k(retrieved, relevant, k): fraction of `relevant` present in the
#   first k of `retrieved`.
# precision_at_k(retrieved, relevant, k): fraction of the first k that are
#   relevant.
# mrr(retrieved, relevant): 1/rank of the FIRST relevant doc (rank starts
#   at 1); 0.0 if none appears.


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    fused = rrf_fuse([[0, 1, 2], [0, 2, 1]])
    assert set(fused) == {0, 1, 2}
    assert fused[0] == 0, "ranked 1st by both -> best fused score"

    # Appearing in BOTH rankings beats a single first place:
    fused2 = rrf_fuse([[7, 3], [3]])
    assert fused2[0] == 3, "doc 3 (rank 2 + rank 1) must beat doc 7 (rank 1 once)"

    top = retrieve_then_rerank("how do I request a refund", CORPUS)
    assert top[0] == 2, "the doc answering 'how do I request' must win rerank"
    assert len(top) == 2

    assert recall_at_k([1, 2, 3], {1, 9}, k=3) == 0.5
    assert recall_at_k([1, 9, 3], {1, 9}, k=3) == 1.0
    assert precision_at_k([1, 2, 3], {1, 9}, k=3) == 1 / 3
    assert mrr([7, 8, 1], {1}) == 1 / 3
    assert mrr([7, 8], {1}) == 0.0

    # Your metrics judging your pipeline vs the naive baseline:
    eval_set = [
        ("what does error E-1234 mean", {0}),
        ("how do I get my money back", {1, 2}),
    ]
    def avg_mrr(ranker):
        return sum(mrr(ranker(q, CORPUS), rel) for q, rel in eval_set) / len(eval_set)

    hybrid = lambda q, c: rrf_fuse([keyword_rank(q, c), vector_rank(q, c)])
    assert avg_mrr(hybrid) >= avg_mrr(vector_rank), \
        "hybrid must not lose to the naive baseline"

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Implement multi-query fusion: rrf_fuse over vector_rank of 3 paraphrases.
# 2. Add ndcg@k — graded relevance instead of binary.
# 3. Break the corpus: add 20 distractor docs about refunds for a DIFFERENT
#    product and watch precision@k fall while recall@k holds. Fix with
#    metadata filtering from Module 2.
