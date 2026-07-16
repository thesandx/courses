"""
Module 8 Exercise: Gateway, Semantic Cache, Tracer
==================================================
Goal
----
Build the three production pillars: a routing/fallback/metering gateway, a
semantic cache with TTL and source invalidation, and a span tracer.

Complete the TODOs below, then run:  python3 exercise.py
All assertions at the bottom must pass. Try it before opening solution.py!
"""

import hashlib
import math
import time


# ---------------------------------------------------------------------------
# Provided: primitives and mock model providers
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


MODELS = {
    "small":    {"price_per_1k": 0.10, "tiers": {"classify"},
                 "reply": lambda p: "label: refund"},
    "medium":   {"price_per_1k": 1.00, "tiers": {"classify", "answer"},
                 "reply": lambda p: "Refunds take 5 business days."},
    "frontier": {"price_per_1k": 8.00, "tiers": {"classify", "answer", "reason"},
                 "reply": lambda p: "Detailed reasoning..."},
}


class ProviderDown(Exception):
    pass


# ---------------------------------------------------------------------------
# TODO 1 — class Gateway(outage=None)
# ---------------------------------------------------------------------------
# complete(prompt, tier, caller) -> dict:
#   * candidates = models whose "tiers" contain `tier`, sorted cheapest first
#   * raise ValueError if none
#   * try candidates in order; a model in self.outage raises/counts as down —
#     record its name and move on
#   * on success: tokens = count_tokens(prompt) + count_tokens(answer);
#     cost = tokens/1000 * price; accumulate per-caller usage in self.usage
#     as {"tokens", "cost", "calls"}; return {"answer", "model", "tokens",
#     "cost", "failed_over_from": [names tried before success]}
#   * if all candidates are down, raise ProviderDown


# ---------------------------------------------------------------------------
# TODO 2 — class SemanticCache(threshold=0.80, ttl_seconds=3600)
# ---------------------------------------------------------------------------
# * put(prompt, answer, source, now): store an entry usable by BOTH layers
# * get(prompt, now) -> None or:
#     {"answer", "layer": "exact"} on an identical, unexpired prompt
#     {"answer", "layer": "semantic"} when the best unexpired entry's
#       cosine similarity >= threshold
#     None otherwise (including: everything expired)
# * invalidate_source(source) -> count of entries purged from both layers


# ---------------------------------------------------------------------------
# TODO 3 — class Tracer
# ---------------------------------------------------------------------------
# * start(name, **attributes): push a span dict {"name", "attributes",
#   "parent" (name of enclosing span or None), "start", "duration_ms": None}
#   onto a stack AND append it to self.spans
# * end(**attributes): pop the innermost span, merge the attributes,
#   set duration_ms


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    gw = Gateway()
    r = gw.complete("classify: 'where is my refund'", "classify", "bot")
    assert r["model"] == "small" and r["failed_over_from"] == []
    r2 = gw.complete("how long do refunds take?", "answer", "chat")
    assert r2["model"] == "medium"
    assert gw.usage["chat"]["calls"] == 1 and gw.usage["chat"]["cost"] > 0

    gw_out = Gateway(outage={"medium"})
    r3 = gw_out.complete("how long do refunds take?", "answer", "chat")
    assert r3["model"] == "frontier" and r3["failed_over_from"] == ["medium"]
    try:
        Gateway(outage={"small", "medium", "frontier"}).complete(
            "x", "answer", "chat")
        raise SystemExit("FAIL: total outage must raise ProviderDown")
    except ProviderDown:
        pass
    try:
        gw.complete("x", "translate", "chat")
        raise SystemExit("FAIL: unknown tier must raise ValueError")
    except ValueError:
        pass

    cache = SemanticCache(threshold=0.80, ttl_seconds=100)
    cache.put("how do I reset my password", "Settings > Security.",
              source="handbook", now=1000.0)
    assert cache.get("how do I reset my password", now=1001)["layer"] == "exact"
    sem = cache.get("how do I reset my password please", now=1001)
    assert sem and sem["layer"] == "semantic"
    assert cache.get("what is the refund policy", now=1001) is None
    assert cache.get("how do I reset my password", now=1500) is None, "TTL"
    assert cache.invalidate_source("handbook") == 1
    assert cache.get("how do I reset my password", now=1001) is None

    tracer = Tracer()
    tracer.start("pipeline", question="q")
    tracer.start("retrieve")
    time.sleep(0.001)
    tracer.end(k=3)
    tracer.start("llm_call")
    tracer.end(model="medium", cost=0.01)
    tracer.end(total=True)
    assert [s["name"] for s in tracer.spans] == ["pipeline", "retrieve",
                                                 "llm_call"]
    assert tracer.spans[1]["parent"] == "pipeline"
    assert tracer.spans[0]["parent"] is None
    assert all(s["duration_ms"] is not None for s in tracer.spans)
    assert tracer.spans[1]["duration_ms"] <= tracer.spans[0]["duration_ms"]
    assert tracer.spans[2]["attributes"]["cost"] == 0.01
    assert tracer.spans[0]["attributes"]["total"] is True

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Add a per-caller budget to the Gateway: raise once a caller's cost
#    crosses a limit (rule 12 of the meme: don't burn the budget in a demo).
# 2. Log a warning when a semantic hit's similarity is within 0.02 of the
#    threshold — those are your future cache-poisoning bug reports.
# 3. Export the tracer's spans as JSON and compute p50/p95 llm_call latency
#    over 100 runs.
