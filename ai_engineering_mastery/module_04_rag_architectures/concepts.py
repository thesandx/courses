"""
Module 4: RAG Architectures — Concepts in Action
================================================
Run: python3 concepts.py

Flat vector RAG failing a multi-hop question, GraphRAG answering it by
traversal, and an agentic retrieval loop that decides when to retrieve,
when to rewrite, and when to answer.
"""

import hashlib
import math
import re

# ---------------------------------------------------------------------------
# Primitives from earlier modules
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


def embed(text: str, dims: int = 256) -> list[float]:  # more dims, fewer hash collisions
    vec = [0.0] * dims
    for token in tokenize(text):
        h = hashlib.sha256(token.encode()).digest()
        vec[h[0] % dims] += 1.0 if h[1] % 2 == 0 else -1.0
    return vec


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def vector_top_k(query: str, corpus: list[str], k: int = 2) -> list[int]:
    q = embed(query)
    scores = [(cosine_similarity(q, embed(d)), i) for i, d in enumerate(corpus)]
    return [i for _, i in sorted(scores, key=lambda p: -p[0])[:k]]


# The corpus: org facts plus realistic distractors. The multi-hop answer
# spans docs 1 and 2; docs 3-4 merely LOOK like the question.
CORPUS = [
    "The billing outage on May 3rd was traced to ticket E-1234.",              # 0
    "Priya fixed ticket E-1234 after the billing outage.",                     # 1
    "Priya reports to Marcus, who leads the payments team.",                   # 2
    "The engineering manager handbook describes who handles escalations.",     # 3
    "Managers of engineers review incident tickets weekly.",                   # 4
    "The payments team owns the gateway and the invoicing service.",           # 5
]

# ============================================================================
# 1. Flat RAG fails the multi-hop question
# ============================================================================
print("=" * 70)
print("1. The multi-hop failure")
print("=" * 70)

QUESTION = "Who is the manager of the engineer who fixed E-1234?"
hits = vector_top_k(QUESTION, CORPUS, k=2)
print(f"question: {QUESTION}")
print(f"flat RAG top-2 docs: {hits}")
for i in hits:
    print(f"  [{i}] {CORPUS[i]}")

# The answer requires doc 1 (Priya fixed it) AND doc 2 (Priya -> Marcus).
# Doc 2 barely resembles the question, while the handbook distractors are
# FULL of 'manager'/'engineer' — similarity retrieves lookalikes, not links.
assert 2 not in hits, \
    "doc 2 doesn't resemble the question — flat similarity search misses it"
print("=> the hop 'Priya -> Marcus' is invisible to similarity search")

# ============================================================================
# 2. GraphRAG: extract triples, answer by traversal
# ============================================================================
print()
print("=" * 70)
print("2. GraphRAG")
print("=" * 70)

# Scripted extraction — in production an LLM emits these triples per chunk.
EXTRACTION_PATTERNS = [
    (re.compile(r"(\w[\w ]*?) fixed ticket (E-\d+)"), "fixed"),
    (re.compile(r"(\w[\w ]*?) reports to (\w+)"), "reports_to"),
    (re.compile(r"(\w+), who leads the ([\w ]+? team)"), "leads"),
    (re.compile(r"traced to ticket (E-\d+)"), None),  # entity only
]


class KnowledgeGraph:
    """Adjacency-list triple store: (subject, relation, object)."""

    def __init__(self):
        self.triples: list[tuple[str, str, str]] = []

    def add(self, subj: str, rel: str, obj: str):
        triple = (subj.strip(), rel, obj.strip())
        if triple not in self.triples:
            self.triples.append(triple)

    def objects(self, subj: str, rel: str) -> list[str]:
        return [o for s, r, o in self.triples if s == subj and r == rel]

    def subjects(self, rel: str, obj: str) -> list[str]:
        return [s for s, r, o in self.triples if r == rel and o == obj]


def extract_triples(corpus: list[str]) -> KnowledgeGraph:
    kg = KnowledgeGraph()
    for doc in corpus:
        for pattern, rel in EXTRACTION_PATTERNS:
            for m in pattern.finditer(doc):
                if rel:
                    kg.add(m.group(1), rel, m.group(2))
    return kg


kg = extract_triples(CORPUS)
print("extracted triples:")
for t in kg.triples:
    print(f"  {t}")

# Multi-hop = two-edge walk: E-1234 <-fixed- ? -reports_to-> ?
fixer = kg.subjects("fixed", "E-1234")[0]
manager = kg.objects(fixer, "reports_to")[0]
print(f"graph walk: E-1234 <-fixed- {fixer} -reports_to-> {manager}")
assert (fixer, manager) == ("Priya", "Marcus")

# The traversal result is then SERIALIZED as context for the generator:
subgraph_context = (f"{fixer} fixed E-1234. {fixer} reports to {manager}.")
print(f"context handed to the LLM: {subgraph_context!r}")

# Aggregation, impossible for top-k, is trivial on the graph:
team_leads = kg.subjects("leads", "payments team")
assert team_leads == ["Marcus"]

# ============================================================================
# 3. Agentic RAG: retrieval as a decision inside a bounded loop
# ============================================================================
print()
print("=" * 70)
print("3. Agentic RAG")
print("=" * 70)


def agent_policy(question: str, evidence: list[str]) -> tuple[str, str]:
    """The 'model' deciding the next action. Scripted here; in production
    this is one LLM call returning {action, argument}. The SHAPE of the loop
    — inspect evidence, choose retrieve/answer/refuse — is the architecture."""
    text = " ".join(evidence).lower()
    if "fixed ticket" not in text:
        return ("retrieve", "who fixed ticket E-1234")
    if "fixed ticket" in text and "reports to" not in text:
        # Iterative refinement: the SECOND query uses what the first found.
        person = re.search(r"(\w+) fixed ticket", " ".join(evidence)).group(1)
        return ("retrieve", f"who does {person} report to")
    if "reports to" in text:
        person = re.search(r"(\w+) reports to (\w+)", " ".join(evidence))
        return ("answer", f"{person.group(2)} manages {person.group(1)}, "
                          f"who fixed E-1234.")
    return ("refuse", "insufficient evidence")


def agentic_rag(question: str, corpus: list[str], max_steps: int = 5) -> dict:
    evidence: list[str] = []
    trace: list[str] = []
    for step in range(max_steps):                    # bounded — always
        action, arg = agent_policy(question, evidence)
        trace.append(f"step {step}: {action}({arg!r})")
        if action == "retrieve":
            for i in vector_top_k(arg, corpus, k=1):
                if corpus[i] not in evidence:
                    evidence.append(corpus[i])
        else:
            return {"action": action, "text": arg,
                    "evidence": evidence, "trace": trace}
    return {"action": "refuse", "text": "step budget exhausted",
            "evidence": evidence, "trace": trace}


result = agentic_rag(QUESTION, CORPUS)
for line in result["trace"]:
    print(f"  {line}")
print(f"  answer: {result['text']}")

assert result["action"] == "answer"
assert "Marcus" in result["text"] and "Priya" in result["text"]
assert len(result["evidence"]) == 2, "two hops -> two targeted retrievals"
assert len(result["trace"]) <= 5, "the loop is bounded"
print("=> the loop found the hop that one-shot similarity search could not")

# The flip side: agentic RAG spent 3 'LLM calls' where flat RAG spends 1.
calls_flat, calls_agentic = 1, len(result["trace"])
print(f"cost: flat RAG = {calls_flat} model call, agentic = {calls_agentic} calls")
assert calls_agentic > calls_flat, "agency is never free"

print("\nAll Module 4 concept checks passed ✔")
