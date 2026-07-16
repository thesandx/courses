"""
Module 1 Exercise: Build the LLM Primitives Toolkit
===================================================
Goal
----
Implement the four primitives every later module leans on: token budgeting,
cosine similarity, softmax attention weights, and structured prompt assembly.

Complete the TODOs below, then run:  python3 exercise.py
All assertions at the bottom must pass. Try it before opening solution.py!
"""

import hashlib
import math


# ---------------------------------------------------------------------------
# Provided: the toy tokenizer and hash embedding from concepts.py
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


def embed(text: str, dims: int = 64) -> list[float]:
    vec = [0.0] * dims
    for token in tokenize(text):
        h = hashlib.sha256(token.encode()).digest()
        vec[h[0] % dims] += 1.0 if h[1] % 2 == 0 else -1.0
    return vec


# ---------------------------------------------------------------------------
# TODO 1 — fits_budget(text, max_tokens)
# ---------------------------------------------------------------------------
# Return True if `text` fits in `max_tokens` using the REAL tokenizer above
# (len(tokenize(text))), not the chars/4 heuristic. A model call that
# overflows its window fails hard — this check runs before every call.


# ---------------------------------------------------------------------------
# TODO 2 — cosine_similarity(a, b)
# ---------------------------------------------------------------------------
# Implement cosine similarity between two equal-length vectors:
#   dot(a, b) / (|a| * |b|)
# Return 0.0 if either vector has zero magnitude (never divide by zero).


# ---------------------------------------------------------------------------
# TODO 3 — attention_weights(query, chunks)
# ---------------------------------------------------------------------------
# Given a query string and a list of chunk strings:
#   1. score each chunk: cosine_similarity(embed(query), embed(chunk)) * 5
#   2. softmax the scores (subtract max before exp for numerical stability)
#   3. return the list of weights, in the SAME order as `chunks`
# Weights must sum to ~1.0.


# ---------------------------------------------------------------------------
# TODO 4 — build_prompt(role, instructions, context, question)
# ---------------------------------------------------------------------------
# Return a single string with sections in this exact order, separated by
# blank lines:
#   "ROLE: {role}"
#   "INSTRUCTIONS: {instructions}"
#   "CONTEXT:" then one line per chunk formatted as "[doc N] {chunk}" (N from 1)
#   "QUESTION: {question}"
# The instruction contract goes at the top, the ask at the end — position
# is attention engineering.


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    assert fits_budget("one two six", 3)
    assert not fits_budget("one two six ten", 3)

    assert abs(cosine_similarity([1, 0], [1, 0]) - 1.0) < 1e-9
    assert abs(cosine_similarity([1, 0], [0, 1])) < 1e-9
    assert cosine_similarity([0, 0], [1, 1]) == 0.0, "zero vector must not crash"
    q, doc = embed("reset password"), embed("password reset steps")
    assert cosine_similarity(q, doc) > 0.3

    chunks = [
        "Password resets are done from Settings.",
        "Refunds are allowed within 30 days.",
        "Reset links expire after one hour.",
    ]
    weights = attention_weights("how do I reset my password", chunks)
    assert len(weights) == 3
    assert abs(sum(weights) - 1.0) < 1e-6, "softmax weights must sum to 1"
    assert weights[1] < weights[0] and weights[1] < weights[2], \
        "the refund chunk must get the least attention"

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
        prompt.index("QUESTION:"), "sections out of order"

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Add few-shot `examples` to build_prompt and verify the model-facing format.
# 2. Make attention_weights take a `sharpness` parameter and observe how higher
#    sharpness concentrates weight on the top chunk (temperature, inverted).
# 3. Write truncate_to_budget(chunks, max_tokens) that drops the LOWEST-weight
#    chunks first — you will want it in Module 7.
