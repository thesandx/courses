"""
Module 1: LLM Foundations — Concepts in Action
==============================================
Run: python3 concepts.py

Each section maps 1:1 to a section in README.md and prints observable proof.
No third-party packages: embeddings are deterministic hash-based vectors, so the
geometry is real even though the "meaning" is simulated.
"""

import hashlib
import math

# ============================================================================
# 1. Tokens: the unit of everything
# ============================================================================
print("=" * 70)
print("1. Tokens")
print("=" * 70)


def tokenize(text: str) -> list[str]:
    """A toy subword tokenizer: lowercase words, split long words into 4-char
    pieces. Real BPE is smarter, but the *consequences* (subword splits, budget
    counted in tokens) are identical."""
    tokens: list[str] = []
    for word in text.lower().split():
        word = word.strip(".,!?;:()\"'")
        if not word:
            continue
        while len(word) > 4:
            tokens.append(word[:4])
            word = word[4:]
        tokens.append(word)
    return tokens


def estimate_tokens(text: str) -> int:
    """The ~4 chars/token heuristic — good enough for budgeting, never exact."""
    return max(1, len(text) // 4)


plain = "The cat sat on the mat"
jargon = "Hyperparameterization heteroscedasticity"
for text in (plain, jargon):
    toks = tokenize(text)
    print(f"{text!r}\n  -> {len(toks)} tokens: {toks}")

# Rare/long words explode into more tokens — same char count, bigger bill:
assert len(tokenize(jargon)) > len(tokenize("cat sat mat on a hat here")), \
    "jargon should cost more tokens than simple words of similar length"
print(f"estimate_tokens(plain) = {estimate_tokens(plain)} (heuristic, not exact)")

# ============================================================================
# 2. Embeddings + cosine similarity
# ============================================================================
print()
print("=" * 70)
print("2. Embeddings & cosine similarity")
print("=" * 70)

DIMS = 64


def embed(text: str) -> list[float]:
    """Deterministic bag-of-tokens hash embedding.
    Each token hashes to a direction in DIMS-dimensional space; a text's vector
    is the sum of its tokens' directions. Texts sharing tokens end up nearby —
    the same *geometry* a real embedding model gives you for shared meaning."""
    vec = [0.0] * DIMS
    for token in tokenize(text):
        h = hashlib.sha256(token.encode()).digest()
        idx = h[0] % DIMS
        sign = 1.0 if h[1] % 2 == 0 else -1.0
        vec[idx] += sign
    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


query = "how do I reset my password"
close = "steps to reset a forgotten password"
far = "quarterly revenue grew nine percent"

sim_close = cosine_similarity(embed(query), embed(close))
sim_far = cosine_similarity(embed(query), embed(far))
print(f"sim(query, password-doc) = {sim_close:.3f}")
print(f"sim(query, revenue-doc)  = {sim_far:.3f}")
assert sim_close > sim_far, "related text must score higher"
assert abs(cosine_similarity(embed(query), embed(query)) - 1.0) < 1e-9, \
    "a vector is perfectly similar to itself"

# ============================================================================
# 3. Attention: a softmax-weighted lookup
# ============================================================================
print()
print("=" * 70)
print("3. Attention as weighted lookup")
print("=" * 70)


def softmax(scores: list[float]) -> list[float]:
    m = max(scores)
    exps = [math.exp(s - m) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def attention(query_vec: list[float], keys: list[list[float]],
              values: list[str]) -> list[tuple[str, float]]:
    """Score each key against the query, softmax into weights, and show how
    much each value would contribute to the blended output."""
    scores = [cosine_similarity(query_vec, k) * 5 for k in keys]  # *5 = sharpness
    weights = softmax(scores)
    return sorted(zip(values, weights), key=lambda p: -p[1])


context_chunks = [
    "Password resets are done from Settings > Security.",
    "Our refund policy allows returns within 30 days.",
    "The password reset link expires after one hour.",
]
weighted = attention(embed(query), [embed(c) for c in context_chunks], context_chunks)
print(f"query: {query!r}")
for chunk, w in weighted:
    print(f"  weight {w:.2f}  <- {chunk}")

top_two = {chunk for chunk, _ in weighted[:2]}
assert "refund" not in " ".join(top_two), \
    "the two password chunks should out-attend the refund chunk"

# Everything in context competes: adding junk chunks dilutes the good ones.
junk = ["unrelated filler text " + str(i) for i in range(5)]
diluted = attention(embed(query),
                    [embed(c) for c in context_chunks + junk],
                    context_chunks + junk)
best_clean = max(w for c, w in weighted if "Settings" in c)
best_diluted = max(w for c, w in diluted if "Settings" in c)
print(f"best chunk's weight: {best_clean:.2f} clean vs {best_diluted:.2f} with junk")
assert best_diluted < best_clean, "junk context steals attention weight"

# ============================================================================
# 4. Prompting as engineering
# ============================================================================
print()
print("=" * 70)
print("4. Structured prompt assembly")
print("=" * 70)


def build_prompt(role: str, instructions: str, context: list[str],
                 examples: list[tuple[str, str]], question: str,
                 output_format: str) -> str:
    """Assemble the five sections in a deliberate order: contract at the top,
    context in the middle, the ask + format reminder at the end."""
    parts = [f"ROLE: {role}", f"INSTRUCTIONS: {instructions}"]
    if context:
        docs = "\n".join(f"[doc {i + 1}] {c}" for i, c in enumerate(context))
        parts.append(f"CONTEXT:\n{docs}")
    if examples:
        shots = "\n".join(f"Q: {q}\nA: {a}" for q, a in examples)
        parts.append(f"EXAMPLES:\n{shots}")
    parts.append(f"QUESTION: {question}")
    parts.append(f"OUTPUT FORMAT: {output_format}")
    return "\n\n".join(parts)


prompt = build_prompt(
    role="You are a support engineer for AcmeDB.",
    instructions="Answer ONLY from the provided context. If the answer is not "
                 "in the context, say 'I don't know'.",
    context=[c for c, _ in weighted[:2]],           # attention-ranked context!
    examples=[("How long do sessions last?", "I don't know")],
    question=query,
    output_format='JSON: {"answer": str, "sources": [int]}',
)
print(prompt)
print(f"\nprompt budget: ~{estimate_tokens(prompt)} tokens")
for section in ("ROLE:", "INSTRUCTIONS:", "CONTEXT:", "EXAMPLES:",
                "QUESTION:", "OUTPUT FORMAT:"):
    assert section in prompt, f"missing section {section}"

# ============================================================================
# 5. Prompt or fine-tune? A rubric, not a vibe
# ============================================================================
print()
print("=" * 70)
print("5. Prompt vs fine-tune decision rubric")
print("=" * 70)


def prompt_or_finetune(*, needs_new_knowledge: bool, needs_style_consistency: bool,
                       task_changes_often: bool, huge_volume_fixed_task: bool) -> str:
    if needs_new_knowledge:
        return "RAG"            # fine-tuning is a terrible database
    if task_changes_often:
        return "prompting"      # fine-tunes are frozen the day they finish
    if huge_volume_fixed_task:
        return "fine-tune"      # amortize the cost, shrink the model
    if needs_style_consistency:
        return "prompting, then fine-tune if examples don't stick"
    return "prompting"


cases = [
    dict(needs_new_knowledge=True, needs_style_consistency=False,
         task_changes_often=False, huge_volume_fixed_task=False),
    dict(needs_new_knowledge=False, needs_style_consistency=False,
         task_changes_often=True, huge_volume_fixed_task=False),
    dict(needs_new_knowledge=False, needs_style_consistency=False,
         task_changes_often=False, huge_volume_fixed_task=True),
]
for case in cases:
    print(f"{case} -> {prompt_or_finetune(**case)}")
assert prompt_or_finetune(needs_new_knowledge=True, needs_style_consistency=True,
                          task_changes_often=False,
                          huge_volume_fixed_task=True) == "RAG", \
    "missing knowledge always routes to RAG first"

print("\nAll Module 1 concept checks passed ✔")
