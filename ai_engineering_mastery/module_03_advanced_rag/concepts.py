"""
Module 3: Advanced RAG — Concepts in Action
===========================================
Run: python3 concepts.py

Hybrid search (keyword + vector + RRF), query rewriting (multi-query, HyDE),
cross-encoder-style reranking, and retrieval evals. Every technique is
measured against the naive baseline it claims to beat.
"""

import hashlib
import math

# ---------------------------------------------------------------------------
# Primitives from Modules 1–2
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


SYNONYMS = {"money": "refund", "refunds": "refund", "card": "payment",
            "restart": "reboot", "restarting": "reboot"}


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


# The corpus: a tiny knowledge base with labeled ground truth further down.
CORPUS = [
    "Error E-1234 means the reset link has expired; request a new one.",       # 0
    "Refunds are processed within 5 business days of the request.",            # 1
    "To request a refund, open a support ticket from your dashboard.",         # 2
    "The pro plan includes priority support and a 99.9% uptime SLA.",          # 3
    "Reboot the gateway appliance by holding the power button 10 seconds.",    # 4
    "Invoices are emailed on the first day of each month.",                    # 5
]

# ============================================================================
# 1. Hybrid search: BM25-lite + vectors + RRF
# ============================================================================
print("=" * 70)
print("1. Hybrid search")
print("=" * 70)


def keyword_rank(query: str, corpus: list[str]) -> list[int]:
    """BM25-lite: score = sum over query words of IDF-weighted matches.
    Rare words (like 'E-1234') dominate — exactly BM25's virtue."""
    n = len(corpus)
    doc_words = [set(d.lower().split()) for d in corpus]

    def idf(word: str) -> float:
        containing = sum(1 for ws in doc_words if word in ws)
        return math.log((n + 1) / (containing + 0.5))

    scores = []
    for i, words in enumerate(doc_words):
        s = sum(idf(w) for w in query.lower().split() if w in words)
        scores.append((s, i))
    return [i for _, i in sorted(scores, key=lambda p: -p[0])]


def vector_rank(query: str, corpus: list[str]) -> list[int]:
    q = embed(query)
    scores = [(cosine_similarity(q, embed(d)), i) for i, d in enumerate(corpus)]
    return [i for _, i in sorted(scores, key=lambda p: -p[0])]


def rrf_fuse(rankings: list[list[int]], k: int = 60) -> list[int]:
    """Reciprocal Rank Fusion: fuse RANKS, never raw scores — cosine and BM25
    live on incomparable scales."""
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda d: -scores[d])


id_query = "what does error E-1234 mean"
para_query = "how do I get my money back"

for query, needs in ((id_query, 0), (para_query, 1)):
    kw = keyword_rank(query, CORPUS)
    vs = vector_rank(query, CORPUS)
    fused = rrf_fuse([kw, vs])
    print(f"query: {query!r}  (relevant doc: {needs})")
    print(f"  keyword top-3: {kw[:3]}   vector top-3: {vs[:3]}   fused top-3: {fused[:3]}")

# The identifier query: keywords nail it, and fusion preserves that.
assert keyword_rank(id_query, CORPUS)[0] == 0
assert rrf_fuse([keyword_rank(id_query, CORPUS), vector_rank(id_query, CORPUS)])[0] == 0
# The paraphrase query: vectors find it, and fusion preserves that too.
assert vector_rank(para_query, CORPUS)[0] in (1, 2)
assert rrf_fuse([keyword_rank(para_query, CORPUS),
                 vector_rank(para_query, CORPUS)])[0] in (1, 2)
print("hybrid search keeps the best of both rankers ✔")

# ============================================================================
# 2. Query rewriting: multi-query and HyDE
# ============================================================================
print()
print("=" * 70)
print("2. Query rewriting")
print("=" * 70)

# A scripted "LLM" for rewrites — in production these come from a model call.
REWRITES = {
    "my payment came back weird": [
        "refund request process",
        "how are refunds processed",
        "billing issue with payment",
    ],
}
HYDE_DRAFTS = {
    "my payment came back weird":
        "Refunds are processed within a few business days after you open a "
        "support ticket describing the payment issue.",
}


def multi_query_rank(query: str, corpus: list[str]) -> list[int]:
    """Retrieve with the original + each paraphrase, fuse with RRF."""
    queries = [query] + REWRITES.get(query, [])
    return rrf_fuse([vector_rank(q, corpus) for q in queries])


def hyde_rank(query: str, corpus: list[str]) -> list[int]:
    """HyDE: embed a HYPOTHETICAL ANSWER instead of the question — answers
    live nearer other answers in embedding space than questions do."""
    hypothetical = HYDE_DRAFTS.get(query, query)
    return vector_rank(hypothetical, corpus)


vague = "my payment came back weird"
naive = vector_rank(vague, CORPUS)
multi = multi_query_rank(vague, CORPUS)
hyde = hyde_rank(vague, CORPUS)
print(f"vague query: {vague!r}  (relevant docs: 1, 2)")
print(f"  naive top-3:       {naive[:3]}")
print(f"  multi-query top-3: {multi[:3]}")
print(f"  HyDE top-3:        {hyde[:3]}")


def rank_of(doc_id: int, ranking: list[int]) -> int:
    return ranking.index(doc_id) + 1


assert rank_of(1, multi) <= rank_of(1, naive), "multi-query must not hurt doc 1"
assert rank_of(1, hyde) <= rank_of(1, naive), "HyDE must not hurt doc 1"
assert {1, 2} <= set(hyde[:3]), \
    "the hypothetical answer lands near BOTH real answers (naive missed doc 1)"
assert not {1, 2} <= set(naive[:3]), "the naive ranking should miss one of them"

# ============================================================================
# 3. Reranking: retrieve cheap, rank expensive
# ============================================================================
print()
print("=" * 70)
print("3. Cross-encoder-style reranking")
print("=" * 70)


def cross_encoder_score(query: str, doc: str) -> float:
    """Simulates a cross-encoder: scores the INTERACTION of query and doc
    (word-pair overlap incl. synonyms), not two independent embeddings.
    Real ones are transformer models — same contract, same position in the
    pipeline: too slow for the corpus, precise on a shortlist."""
    def norm(text):
        return {SYNONYMS.get(w, w) for w in
                (x.strip(".,!?;:()\"'").lower() for x in text.split()) if w}
    q, d = norm(query), norm(doc)
    overlap = len(q & d) / len(q) if q else 0.0
    return overlap + (0.3 if any(w in d for w in q if len(w) > 6) else 0.0)


def retrieve_then_rerank(query: str, corpus: list[str],
                         candidates: int = 4, k: int = 2) -> list[int]:
    shortlist = rrf_fuse([keyword_rank(query, corpus),
                          vector_rank(query, corpus)])[:candidates]
    reranked = sorted(shortlist,
                      key=lambda i: -cross_encoder_score(query, corpus[i]))
    return reranked[:k]


final = retrieve_then_rerank("how do I request a refund", CORPUS)
print(f"retrieve(4) -> rerank -> top-2: {final}")
assert final[0] == 2, "the doc that ANSWERS 'how do I request' must rank first"

# ============================================================================
# 4. Retrieval evals: recall@k, precision@k, MRR
# ============================================================================
print()
print("=" * 70)
print("4. Retrieval evals")
print("=" * 70)

# Labeled ground truth: query -> set of relevant doc ids.
EVAL_SET = [
    ("what does error E-1234 mean", {0}),
    ("how do I get my money back", {1, 2}),
    ("when do invoices arrive", {5}),
    ("gateway appliance restart procedure", {4}),
]


def recall_at_k(retrieved: list[int], relevant: set[int], k: int) -> float:
    return len(set(retrieved[:k]) & relevant) / len(relevant)


def precision_at_k(retrieved: list[int], relevant: set[int], k: int) -> float:
    return len(set(retrieved[:k]) & relevant) / k


def mrr(retrieved: list[int], relevant: set[int]) -> float:
    for rank, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def evaluate(ranker, name: str, k: int = 3) -> dict[str, float]:
    r_sum = p_sum = m_sum = 0.0
    for query, relevant in EVAL_SET:
        ranking = ranker(query, CORPUS)
        r_sum += recall_at_k(ranking, relevant, k)
        p_sum += precision_at_k(ranking, relevant, k)
        m_sum += mrr(ranking, relevant)
    n = len(EVAL_SET)
    result = {"recall@3": r_sum / n, "precision@3": p_sum / n, "mrr": m_sum / n}
    print(f"  {name:<22} " + "  ".join(f"{k_}={v:.2f}" for k_, v in result.items()))
    return result


print(f"eval set: {len(EVAL_SET)} labeled queries, k=3  (report the WHOLE table)")
base = evaluate(vector_rank, "vector only")
kw_only = evaluate(keyword_rank, "keyword only")
hybrid = evaluate(lambda q, c: rrf_fuse([keyword_rank(q, c), vector_rank(q, c)]),
                  "hybrid (RRF)")

assert hybrid["recall@3"] >= max(base["recall@3"], kw_only["recall@3"]), \
    "hybrid must be at least as good as the best single ranker on recall"
assert hybrid["mrr"] >= base["mrr"]

print("\nAll Module 3 concept checks passed ✔")
