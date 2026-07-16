"""
Module 7: Context, Memory & Evals — Concepts in Action
======================================================
Run: python3 concepts.py

A priority-based context budgeter, short-term memory with summarization,
long-term memory over a vector store, and a three-layer eval harness run
end-to-end against a toy RAG pipeline.
"""

import hashlib
import math

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


def count_tokens(text: str) -> int:
    return len(tokenize(text))


def embed(text: str, dims: int = 256) -> list[float]:
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


# ============================================================================
# 1. Context as a prioritized token budget
# ============================================================================
print("=" * 70)
print("1. The context budgeter")
print("=" * 70)


def pack_context(system: str, question: str, evidence: list[tuple[float, str]],
                 history_digest: str, budget: int) -> dict:
    """Fill the window by priority. The contract and the question are never
    dropped; evidence is added best-first while it fits; the history digest
    takes whatever is left. Returns what made it in and what was cut."""
    required = count_tokens(system) + count_tokens(question)
    assert required <= budget, "budget can't even fit the contract + question"
    remaining = budget - required

    kept_evidence, dropped = [], []
    for score, chunk in sorted(evidence, key=lambda p: -p[0]):
        cost = count_tokens(chunk)
        if cost <= remaining:
            kept_evidence.append(chunk)
            remaining -= cost
        else:
            dropped.append(chunk)

    digest = history_digest if count_tokens(history_digest) <= remaining else ""
    if digest:
        remaining -= count_tokens(digest)
    return {"system": system, "question": question, "evidence": kept_evidence,
            "digest": digest, "dropped": dropped, "unused_tokens": remaining}


evidence = [
    (0.91, "Refunds are processed within 5 business days."),
    (0.55, "Refund requests need the original order id."),
    (0.20, "Our office dog is named Waffles and attends standups."),
]
packed = pack_context(
    system="Answer only from context.",
    question="how long do refunds take?",
    evidence=evidence,
    history_digest="User already gave order id B-42.",
    budget=45,
)
print(f"kept evidence : {packed['evidence']}")
print(f"dropped       : {packed['dropped']}")
print(f"digest kept   : {packed['digest']!r}")

assert evidence[0][1] in packed["evidence"], "top evidence always packed first"
assert "Waffles" in " ".join(packed["dropped"]), \
    "the lowest-relevance chunk is the one that gets cut"
assert packed["digest"], "the digest fit in the leftover budget"

# Same call, tighter budget: graceful degradation, never a crash.
tight = pack_context("Answer only from context.", "how long do refunds take?",
                     evidence, "User already gave order id B-42.", budget=25)
assert len(tight["evidence"]) < len(packed["evidence"])
print(f"tight budget  : kept {len(tight['evidence'])} chunk(s), "
      f"digest kept: {bool(tight['digest'])}")

# ============================================================================
# 2. Short-term memory: rolling buffer + summarization
# ============================================================================
print()
print("=" * 70)
print("2. Short-term memory")
print("=" * 70)


def summarize(turns: list[str]) -> str:
    """Stands in for an LLM summarization call: keeps entities/numbers-ish
    words, drops the chatter. Real summaries have the same LOSSY property."""
    keep = [w for t in turns for w in t.split()
            if w[:1].isupper() or any(ch.isdigit() for ch in w)]
    return "digest: " + " ".join(keep[:12])


class ConversationMemory:
    def __init__(self, max_verbatim: int = 4):
        self.digest = ""
        self.recent: list[str] = []
        self.max_verbatim = max_verbatim
        self.pinned: list[str] = []          # facts too important to summarize

    def add_turn(self, turn: str):
        self.recent.append(turn)
        if len(self.recent) > self.max_verbatim:
            overflow = self.recent[:-self.max_verbatim]
            self.recent = self.recent[-self.max_verbatim:]
            merged = ([self.digest] if self.digest else []) + overflow
            self.digest = summarize(merged)

    def pin(self, fact: str):
        self.pinned.append(fact)

    def context(self) -> str:
        parts = []
        if self.pinned:
            parts.append("PINNED: " + "; ".join(self.pinned))
        if self.digest:
            parts.append(self.digest)
        parts.extend(self.recent)
        return "\n".join(parts)


memory = ConversationMemory(max_verbatim=3)
memory.pin("order id is B-42")
turns = [
    "User: hi, I need help with a refund",
    "Assistant: sure, what's the order id?",
    "User: it's B-42, purchased May 3rd for $120",
    "Assistant: thanks, checking",
    "User: also can you make it fast, I fly on Friday",
    "Assistant: refund for B-42 initiated",
]
for turn in turns:
    memory.add_turn(turn)

ctx = memory.context()
print(ctx)
assert len(memory.recent) == 3, "only the last 3 turns stay verbatim"
assert memory.digest.startswith("digest:"), "overflow was summarized, not dropped"
assert "B-42" in ctx, "the pinned fact survives no matter what the summary kept"
assert turns[-1] in ctx, "the newest turn is always verbatim"

# ============================================================================
# 3. Long-term memory: RAG over your own past
# ============================================================================
print()
print("=" * 70)
print("3. Long-term memory")
print("=" * 70)


class LongTermMemory:
    """A vector store of durable facts; recall = top-k relevant to the
    current question. This is Module 2 pointed at yourself."""

    def __init__(self):
        self._facts: list[tuple[list[float], str]] = []

    def remember(self, fact: str):
        self._facts.append((embed(fact), fact))

    def recall(self, question: str, k: int = 2) -> list[str]:
        q = embed(question)
        scored = sorted(self._facts,
                        key=lambda p: -cosine_similarity(q, p[0]))
        return [fact for _, fact in scored[:k]]


ltm = LongTermMemory()
for fact in ["Ada prefers contact by email, never phone.",
             "Ada's plan renews on the 3rd of each month.",
             "The staging database is read-only after 6pm.",
             "Ada's timezone is IST."]:
    ltm.remember(fact)

recalled = ltm.recall("how should I contact Ada about her refund?")
print(f"recalled for contact question: {recalled}")
assert any("email" in f for f in recalled), \
    "the contact-preference fact must surface for a contact question"
assert not any("staging database" in f for f in recalled), \
    "irrelevant ops facts stay out of the window"

# ============================================================================
# 4. The three-layer eval harness, run over a real (toy) pipeline
# ============================================================================
print()
print("=" * 70)
print("4. Eval harness: deterministic -> grounding -> judge")
print("=" * 70)

KB = [
    "Refunds are processed within 5 business days.",
    "Refund requests require the original order id.",
    "Reset links expire after one hour.",
]


def toy_pipeline(question: str) -> dict:
    """Retrieve top-2 from KB, 'generate' by extractive templating. One case
    is deliberately buggy: the ETA question hallucinates a number not in KB."""
    q = embed(question)
    ranked = sorted(KB, key=lambda d: -cosine_similarity(q, embed(d)))
    context = ranked[:2]
    if "how long" in question:
        answer = "Refunds are processed within 3 days."          # bug on purpose
    elif "need" in question:
        answer = "You need the original order id."
    else:
        answer = "Reset links expire after one hour."
    return {"answer": answer, "context": context}


# Layer 1: deterministic checks -----------------------------------------
def check_format(answer: str) -> bool:
    return answer.endswith(".") and 3 <= len(answer.split()) <= 30


# Layer 2: grounding — every number/entity in the answer must appear in
# the retrieved context, or the answer is (by definition here) ungrounded.
def check_grounding(answer: str, context: list[str]) -> bool:
    ctx = " ".join(context).lower()
    for word in answer.lower().split():
        word = word.strip(".,")
        if word.isdigit() and word not in ctx:
            return False
    return True


# Layer 3: rubric judge (scripted LLM-as-judge; rubric, not vibes) -------
def judge(answer: str, reference: str) -> int:
    """Score 0-2: 2 = matches reference facts, 1 = partial, 0 = wrong.
    A real judge is an LLM call carrying THIS rubric in its prompt."""
    ref_words = set(reference.lower().split())
    ans_words = set(answer.lower().split())
    overlap = len(ref_words & ans_words) / len(ref_words)
    return 2 if overlap > 0.8 else 1 if overlap > 0.4 else 0


EVAL_CASES = [
    {"question": "how long do refunds take?",
     "reference": "Refunds are processed within 5 business days."},
    {"question": "what do I need to request a refund?",
     "reference": "You need the original order id."},
    {"question": "when do reset links expire?",
     "reference": "Reset links expire after one hour."},
]

print(f"{'case':<42} {'format':<7} {'grounded':<9} judge")
results = []
for case in EVAL_CASES:
    out = toy_pipeline(case["question"])
    row = {"format": check_format(out["answer"]),
           "grounded": check_grounding(out["answer"], out["context"]),
           "judge": judge(out["answer"], case["reference"])}
    results.append(row)
    print(f"{case['question']:<42} {str(row['format']):<7} "
          f"{str(row['grounded']):<9} {row['judge']}/2")

# The harness CAUGHT the planted hallucination:
refund_eta = results[0]
assert refund_eta["format"], "format was fine — deterministic checks pass"
assert not refund_eta["grounded"], \
    "grounding catches the fabricated '3 days' that format checks missed"
assert all(r["grounded"] for r in results[1:]), "honest answers ground cleanly"
suite_score = sum(r["judge"] for r in results) / (2 * len(results))
print(f"suite: judge score {suite_score:.2f}, "
      f"grounded {sum(r['grounded'] for r in results)}/{len(results)}")
assert suite_score < 1.0, \
    "the suite must NOT report perfection while a hallucination ships"

print("\nAll Module 7 concept checks passed ✔")
