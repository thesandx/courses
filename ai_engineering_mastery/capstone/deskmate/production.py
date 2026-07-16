"""Module 8: gateway, semantic cache, tracer."""

import hashlib
import time

from .primitives import count_tokens, embed, cosine_similarity

MODELS = {
    "medium":   {"price_per_1k": 1.00, "tiers": {"answer"}},
    "frontier": {"price_per_1k": 8.00, "tiers": {"answer", "reason"}},
}


class Gateway:
    """Routing (cheapest capable model) + metering. The 'model call' is the
    extractive answer the agent already produced — the gateway's job here is
    the production discipline around it, which is exactly its real job."""

    def __init__(self):
        self.usage = {"tokens": 0, "cost": 0.0, "calls": 0}

    def complete(self, prompt: str, answer: str, tier: str = "answer") -> dict:
        model = min((n for n, m in MODELS.items() if tier in m["tiers"]),
                    key=lambda n: MODELS[n]["price_per_1k"])
        tokens = count_tokens(prompt) + count_tokens(answer)
        cost = tokens / 1000 * MODELS[model]["price_per_1k"]
        self.usage["tokens"] += tokens
        self.usage["cost"] += cost
        self.usage["calls"] += 1
        return {"answer": answer, "model": model, "tokens": tokens,
                "cost": cost}


class SemanticCache:
    def __init__(self, threshold: float = 0.80, ttl_seconds: float = 3600):
        self.threshold = threshold
        self.ttl = ttl_seconds
        self._entries: list[dict] = []
        self.hits = 0

    def get(self, prompt: str, now: float) -> str | None:
        q = embed(prompt)
        best, best_sim = None, 0.0
        for e in self._entries:
            if now - e["at"] >= self.ttl:
                continue
            sim = cosine_similarity(q, e["vector"])
            if sim > best_sim:
                best, best_sim = e, sim
        if best and best_sim >= self.threshold:
            self.hits += 1
            return best["answer"]
        return None

    def put(self, prompt: str, answer: str, source: str, now: float):
        self._entries.append({"vector": embed(prompt), "answer": answer,
                              "source": source, "at": now})

    def invalidate_source(self, source: str) -> int:
        before = len(self._entries)
        self._entries = [e for e in self._entries if e["source"] != source]
        return before - len(self._entries)


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

    def report(self) -> str:
        lines = []
        for s in self.spans:
            indent = "  " if s["parent"] else ""
            attrs = " ".join(f"{k}={v}" for k, v in s["attributes"].items())
            lines.append(f"{indent}{s['name']:<16} {s['duration_ms']:8.2f}ms  {attrs}")
        return "\n".join(lines)
