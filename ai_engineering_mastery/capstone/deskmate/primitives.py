"""Module 1 primitives: tokens, embeddings, similarity."""

import hashlib
import math

# Simulates the associations a real embedding model learns from data.
SYNONYMS = {"money": "refund", "refunds": "refund", "cash": "refund",
            "password": "credential", "passwords": "credential"}


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
    normalized = " ".join(SYNONYMS.get(w.strip(".,!?;:()\"'").lower(), w)
                          for w in text.split())
    vec = [0.0] * dims
    for token in tokenize(normalized):
        h = hashlib.sha256(token.encode()).digest()
        vec[h[0] % dims] += 1.0 if h[1] % 2 == 0 else -1.0
    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0
