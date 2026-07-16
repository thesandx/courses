"""
Module 1 Solution: LLM Primitives Toolkit
=========================================
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


def embed(text: str, dims: int = 64) -> list[float]:
    vec = [0.0] * dims
    for token in tokenize(text):
        h = hashlib.sha256(token.encode()).digest()
        vec[h[0] % dims] += 1.0 if h[1] % 2 == 0 else -1.0
    return vec


# TODO 1 — budget in tokens, because the model bills and truncates in tokens.
def fits_budget(text: str, max_tokens: int) -> bool:
    return len(tokenize(text)) <= max_tokens


# TODO 2 — the primitive under every vector database, cache, and memory store.
def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# TODO 3 — score, normalize, blend: attention in nine lines.
def attention_weights(query: str, chunks: list[str]) -> list[float]:
    q = embed(query)
    scores = [cosine_similarity(q, embed(c)) * 5 for c in chunks]
    m = max(scores)
    exps = [math.exp(s - m) for s in scores]      # subtract max: no overflow
    total = sum(exps)
    return [e / total for e in exps]


# TODO 4 — contract first, context middle, ask last.
def build_prompt(role: str, instructions: str, context: list[str],
                 question: str) -> str:
    docs = "\n".join(f"[doc {i + 1}] {c}" for i, c in enumerate(context))
    return "\n\n".join([
        f"ROLE: {role}",
        f"INSTRUCTIONS: {instructions}",
        f"CONTEXT:\n{docs}",
        f"QUESTION: {question}",
    ])


if __name__ == "__main__":
    assert fits_budget("one two six", 3)
    assert not fits_budget("one two six ten", 3)

    assert abs(cosine_similarity([1, 0], [1, 0]) - 1.0) < 1e-9
    assert abs(cosine_similarity([1, 0], [0, 1])) < 1e-9
    assert cosine_similarity([0, 0], [1, 1]) == 0.0
    q, doc = embed("reset password"), embed("password reset steps")
    assert cosine_similarity(q, doc) > 0.3

    chunks = [
        "Password resets are done from Settings.",
        "Refunds are allowed within 30 days.",
        "Reset links expire after one hour.",
    ]
    weights = attention_weights("how do I reset my password", chunks)
    assert len(weights) == 3
    assert abs(sum(weights) - 1.0) < 1e-6
    assert weights[1] < weights[0] and weights[1] < weights[2]

    prompt = build_prompt(
        role="support engineer",
        instructions="answer only from context",
        context=chunks[:2],
        question="how do I reset my password",
    )
    lines = prompt.split("\n")
    assert lines[0] == "ROLE: support engineer"
    assert "[doc 1] Password resets are done from Settings." in prompt
    assert "[doc 2] Refunds are allowed within 30 days." in prompt
    assert prompt.rstrip().endswith("QUESTION: how do I reset my password")
    assert prompt.index("INSTRUCTIONS:") < prompt.index("CONTEXT:") < \
        prompt.index("QUESTION:")

    print("All solution checks passed ✔")
