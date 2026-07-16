"""
Module 3 Solution: Fusion, Reranking, and Retrieval Evals
=========================================================
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


# TODO 1 — fuse ranks, never scores.
def rrf_fuse(rankings: list[list[int]], k: int = 60) -> list[int]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda d: -scores[d])


# TODO 2 — cheap shortlist, expensive reorder.
def retrieve_then_rerank(query: str, corpus: list[str],
                         candidates: int = 4, top: int = 2) -> list[int]:
    shortlist = rrf_fuse([keyword_rank(query, corpus),
                          vector_rank(query, corpus)])[:candidates]
    reranked = sorted(shortlist,
                      key=lambda i: -cross_encoder_score(query, corpus[i]))
    return reranked[:top]


# TODO 3 — the three questions: can it see the answer / how much junk /
#          how high is the first hit.
def recall_at_k(retrieved: list[int], relevant: set[int], k: int) -> float:
    return len(set(retrieved[:k]) & relevant) / len(relevant)


def precision_at_k(retrieved: list[int], relevant: set[int], k: int) -> float:
    return len(set(retrieved[:k]) & relevant) / k


def mrr(retrieved: list[int], relevant: set[int]) -> float:
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


if __name__ == "__main__":
    fused = rrf_fuse([[0, 1, 2], [0, 2, 1]])
    assert set(fused) == {0, 1, 2}
    assert fused[0] == 0

    fused2 = rrf_fuse([[7, 3], [3]])
    assert fused2[0] == 3

    top = retrieve_then_rerank("how do I request a refund", CORPUS)
    assert top[0] == 2
    assert len(top) == 2

    assert recall_at_k([1, 2, 3], {1, 9}, k=3) == 0.5
    assert recall_at_k([1, 9, 3], {1, 9}, k=3) == 1.0
    assert precision_at_k([1, 2, 3], {1, 9}, k=3) == 1 / 3
    assert mrr([7, 8, 1], {1}) == 1 / 3
    assert mrr([7, 8], {1}) == 0.0

    eval_set = [
        ("what does error E-1234 mean", {0}),
        ("how do I get my money back", {1, 2}),
    ]

    def avg_mrr(ranker):
        return sum(mrr(ranker(q, CORPUS), rel) for q, rel in eval_set) / len(eval_set)

    hybrid = lambda q, c: rrf_fuse([keyword_rank(q, c), vector_rank(q, c)])
    assert avg_mrr(hybrid) >= avg_mrr(vector_rank)

    print("All solution checks passed ✔")
