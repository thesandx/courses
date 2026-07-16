"""
Module 8 Solution: Gateway, Semantic Cache, Tracer
==================================================
Run: python3 solution.py — passes the same checks as exercise.py.
"""

import hashlib
import math
import time


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


# TODO 1 — cheapest capable model first; walk up on outage; meter everything.
class Gateway:
    def __init__(self, outage: set[str] | None = None):
        self.outage = outage or set()
        self.usage: dict[str, dict] = {}

    def complete(self, prompt: str, tier: str, caller: str) -> dict:
        candidates = sorted((n for n, m in MODELS.items() if tier in m["tiers"]),
                            key=lambda n: MODELS[n]["price_per_1k"])
        if not candidates:
            raise ValueError(f"no model serves tier {tier!r}")
        attempts: list[str] = []
        for model in candidates:
            if model in self.outage:
                attempts.append(model)
                continue
            answer = MODELS[model]["reply"](prompt)
            tokens = count_tokens(prompt) + count_tokens(answer)
            cost = tokens / 1000 * MODELS[model]["price_per_1k"]
            stats = self.usage.setdefault(caller, {"tokens": 0, "cost": 0.0,
                                                   "calls": 0})
            stats["tokens"] += tokens
            stats["cost"] += cost
            stats["calls"] += 1
            return {"answer": answer, "model": model, "tokens": tokens,
                    "cost": cost, "failed_over_from": attempts}
        raise ProviderDown(f"all candidates down: {candidates}")


# TODO 2 — exact layer for identical prompts, semantic layer for paraphrases;
#          TTL and source purges keep stale answers from outliving their docs.
class SemanticCache:
    def __init__(self, threshold: float = 0.80, ttl_seconds: float = 3600):
        self.threshold = threshold
        self.ttl = ttl_seconds
        self._exact: dict[str, dict] = {}
        self._entries: list[dict] = []

    @staticmethod
    def _key(prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()

    def put(self, prompt: str, answer: str, source: str, now: float):
        entry = {"answer": answer, "vector": embed(prompt),
                 "source": source, "at": now}
        self._exact[self._key(prompt)] = entry
        self._entries.append(entry)

    def get(self, prompt: str, now: float) -> dict | None:
        entry = self._exact.get(self._key(prompt))
        if entry and now - entry["at"] < self.ttl:
            return {"answer": entry["answer"], "layer": "exact"}
        qvec = embed(prompt)
        best, best_sim = None, 0.0
        for entry in self._entries:
            if now - entry["at"] >= self.ttl:
                continue
            sim = cosine_similarity(qvec, entry["vector"])
            if sim > best_sim:
                best, best_sim = entry, sim
        if best and best_sim >= self.threshold:
            return {"answer": best["answer"], "layer": "semantic"}
        return None

    def invalidate_source(self, source: str) -> int:
        stale = [e for e in self._entries if e["source"] == source]
        self._entries = [e for e in self._entries if e["source"] != source]
        self._exact = {k: v for k, v in self._exact.items()
                       if v["source"] != source}
        return len(stale)


# TODO 3 — spans: a stack for nesting, a list for the report.
class Tracer:
    def __init__(self):
        self.spans: list[dict] = []
        self._stack: list[dict] = []

    def start(self, name: str, **attributes):
        span = {"name": name, "attributes": attributes,
                "parent": self._stack[-1]["name"] if self._stack else None,
                "start": time.perf_counter(), "duration_ms": None}
        self._stack.append(span)
        self.spans.append(span)

    def end(self, **attributes):
        span = self._stack.pop()
        span["attributes"].update(attributes)
        span["duration_ms"] = (time.perf_counter() - span["start"]) * 1000


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
    assert cache.get("how do I reset my password", now=1500) is None
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

    print("All solution checks passed ✔")
