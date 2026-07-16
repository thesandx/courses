"""
Module 8: Production AI Engineering — Concepts in Action
========================================================
Run: python3 concepts.py

An LLM gateway (routing, fallback, metering), a two-layer semantic cache
with TTL + invalidation, OpenTelemetry-style spans, and an honest benchmark
that reports the losses along with the wins.
"""

import hashlib
import math
import time

# ---------------------------------------------------------------------------
# Primitives
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
# 1. The LLM gateway: routing, fallback, accounting
# ============================================================================
print("=" * 70)
print("1. LLM gateway")
print("=" * 70)

# Mock providers: (price per 1k tokens, simulated quality tier, a flaky flag)
MODELS = {
    "small":    {"price_per_1k": 0.10, "tiers": {"classify"},
                 "reply": lambda p: "label: refund"},
    "medium":   {"price_per_1k": 1.00, "tiers": {"classify", "answer"},
                 "reply": lambda p: "Refunds take 5 business days."},
    "frontier": {"price_per_1k": 8.00, "tiers": {"classify", "answer", "reason"},
                 "reply": lambda p: "Detailed reasoning about refunds..."},
}


class ProviderDown(Exception):
    pass


class Gateway:
    """One choke point in front of N models. Routing picks the cheapest
    model that can serve the tier; fallback walks up the list on failure;
    every token is metered per caller."""

    def __init__(self, outage: set[str] | None = None):
        self.outage = outage or set()
        self.usage: dict[str, dict] = {}       # caller -> tokens, cost, calls

    def _call_model(self, model: str, prompt: str) -> str:
        if model in self.outage:
            raise ProviderDown(model)
        return MODELS[model]["reply"](prompt)

    def complete(self, prompt: str, tier: str, caller: str) -> dict:
        candidates = sorted((name for name, m in MODELS.items()
                             if tier in m["tiers"]),
                            key=lambda n: MODELS[n]["price_per_1k"])
        if not candidates:
            raise ValueError(f"no model serves tier {tier!r}")
        attempts = []
        for model in candidates:                 # cheapest first, walk up on failure
            try:
                answer = self._call_model(model, prompt)
            except ProviderDown:
                attempts.append(model)
                continue
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


gw = Gateway()
cheap = gw.complete("classify this ticket: 'where is my refund'",
                    tier="classify", caller="ticket-bot")
deep = gw.complete("how long do refunds take?", tier="answer", caller="chat")
print(f"classify -> routed to {cheap['model']} (${cheap['cost']:.4f})")
print(f"answer   -> routed to {deep['model']} (${deep['cost']:.4f})")
assert cheap["model"] == "small", "classify traffic must ride the cheap model"
assert deep["model"] == "medium", "answer tier skips straight past 'small'"

# Fallback: kill the medium provider; answer traffic lands on frontier.
gw_outage = Gateway(outage={"medium"})
failed_over = gw_outage.complete("how long do refunds take?",
                                 tier="answer", caller="chat")
print(f"outage   -> {failed_over['model']} "
      f"(failed over from {failed_over['failed_over_from']})")
assert failed_over["model"] == "frontier"
assert failed_over["failed_over_from"] == ["medium"]

# Accounting: the bill is per caller, in one place.
assert gw.usage["ticket-bot"]["calls"] == 1 and gw.usage["chat"]["calls"] == 1
assert gw.usage["chat"]["cost"] > gw.usage["ticket-bot"]["cost"]
print(f"metering -> {({c: round(u['cost'], 4) for c, u in gw.usage.items()})}")

# ============================================================================
# 2. Two-layer cache: exact + semantic, TTL + invalidation
# ============================================================================
print()
print("=" * 70)
print("2. Semantic cache")
print("=" * 70)


class SemanticCache:
    def __init__(self, threshold: float = 0.80, ttl_seconds: float = 3600):
        self.threshold = threshold
        self.ttl = ttl_seconds
        self._exact: dict[str, dict] = {}
        self._entries: list[dict] = []

    @staticmethod
    def _key(prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()

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
            return {"answer": best["answer"], "layer": "semantic",
                    "similarity": best_sim}
        return None

    def put(self, prompt: str, answer: str, source: str, now: float):
        entry = {"answer": answer, "vector": embed(prompt),
                 "source": source, "at": now}
        self._exact[self._key(prompt)] = entry
        self._entries.append(entry)

    def invalidate_source(self, source: str) -> int:
        """The refund policy changed -> purge every answer that cited it."""
        stale = [e for e in self._entries if e["source"] == source]
        self._entries = [e for e in self._entries if e["source"] != source]
        self._exact = {k: v for k, v in self._exact.items()
                       if v["source"] != source}
        return len(stale)


cache = SemanticCache(threshold=0.80, ttl_seconds=100)
t0 = 1000.0
cache.put("how do I reset my password", "Use Settings > Security.",
          source="handbook.md", now=t0)

hit = cache.get("how do I reset my password", now=t0 + 1)
assert hit and hit["layer"] == "exact"
print(f"identical prompt  -> {hit['layer']} hit")

para = cache.get("how do I reset my password please", now=t0 + 1)
assert para and para["layer"] == "semantic"
print(f"paraphrase        -> {para['layer']} hit (sim={para['similarity']:.2f})")

miss = cache.get("what is the refund policy", now=t0 + 1)
assert miss is None, "an unrelated question must NEVER get a cached answer"
print("unrelated prompt  -> miss (below threshold: no one else's answers)")

expired = cache.get("how do I reset my password", now=t0 + 500)
assert expired is None, "TTL expiry"
purged = cache.invalidate_source("handbook.md")
assert purged == 1
assert cache.get("how do I reset my password", now=t0 + 1) is None, \
    "source invalidation purges both layers"
print(f"TTL + invalidation verified (purged {purged} entry)")

# ============================================================================
# 3. OpenTelemetry-style tracing
# ============================================================================
print()
print("=" * 70)
print("3. Tracing spans")
print("=" * 70)


class Tracer:
    def __init__(self):
        self.spans: list[dict] = []
        self._stack: list[dict] = []

    def start(self, name: str, **attributes) -> dict:
        span = {"name": name, "attributes": attributes,
                "parent": self._stack[-1]["name"] if self._stack else None,
                "start": time.perf_counter(), "duration_ms": None}
        self._stack.append(span)
        self.spans.append(span)
        return span

    def end(self, **attributes):
        span = self._stack.pop()
        span["attributes"].update(attributes)
        span["duration_ms"] = (time.perf_counter() - span["start"]) * 1000

    def report(self) -> str:
        lines = []
        for s in self.spans:
            indent = "  " if s["parent"] else ""
            attrs = " ".join(f"{k}={v}" for k, v in s["attributes"].items())
            lines.append(f"{indent}{s['name']:<18} "
                         f"{s['duration_ms']:.2f}ms  {attrs}")
        return "\n".join(lines)


KB = ["Refunds are processed within 5 business days.",
      "Reset links expire after one hour."]


def traced_pipeline(question: str, tracer: Tracer, cache: SemanticCache,
                    gateway: Gateway, now: float) -> str:
    tracer.start("answer_question", question=question)

    tracer.start("cache_lookup")
    cached = cache.get(question, now)
    tracer.end(hit=bool(cached))
    if cached:
        tracer.end(cached=True, cost=0.0)
        return cached["answer"]

    tracer.start("retrieve")
    q = embed(question)
    context = max(KB, key=lambda d: cosine_similarity(q, embed(d)))
    tracer.end(k=1)

    tracer.start("llm_call")
    result = gateway.complete(f"context: {context}\nq: {question}",
                              tier="answer", caller="pipeline")
    tracer.end(model=result["model"], tokens=result["tokens"],
               cost=round(result["cost"], 5))

    cache.put(question, result["answer"], source="kb", now=now)
    tracer.end(cached=False, cost=round(result["cost"], 5))
    return result["answer"]


tracer = Tracer()
pipeline_cache = SemanticCache()
pipeline_gw = Gateway()
traced_pipeline("how long do refunds take?", tracer, pipeline_cache,
                pipeline_gw, now=t0)
print(tracer.report())

root = tracer.spans[0]
children = [s for s in tracer.spans if s["parent"] == "answer_question"]
assert root["duration_ms"] is not None
assert {c["name"] for c in children} == {"cache_lookup", "retrieve", "llm_call"}
assert all(c["duration_ms"] <= root["duration_ms"] for c in children)
llm_span = next(s for s in tracer.spans if s["name"] == "llm_call")
assert "cost" in llm_span["attributes"], "emit attributes you will alert on"

# ============================================================================
# 4. The honest benchmark: whole table, wins AND losses
# ============================================================================
print()
print("=" * 70)
print("4. Benchmark: naive vs cached gateway (full table)")
print("=" * 70)

WORKLOAD = ["how long do refunds take?"] * 3 + ["when do reset links expire?"] * 2


def run_benchmark(use_cache: bool) -> dict:
    gwx = Gateway()
    cachex = SemanticCache()
    calls_saved = 0
    t = t0
    for q in WORKLOAD:
        t += 1
        if use_cache and cachex.get(q, t):
            calls_saved += 1
            continue
        result = gwx.complete(f"q: {q}", tier="answer", caller="bench")
        if use_cache:
            cachex.put(q, result["answer"], source="kb", now=t)
    usage = gwx.usage.get("bench", {"cost": 0.0, "calls": 0})
    return {"llm_calls": usage["calls"], "cost": usage["cost"],
            "cache_hits": calls_saved,
            # honesty: the cache adds a staleness risk the naive run lacks
            "staleness_risk": "yes" if use_cache else "no"}


naive = run_benchmark(use_cache=False)
cached = run_benchmark(use_cache=True)
print(f"{'metric':<16} {'naive':>10} {'cached':>10}")
for metric in ("llm_calls", "cost", "cache_hits", "staleness_risk"):
    n, c = naive[metric], cached[metric]
    fmt = (lambda v: f"{v:.4f}" if isinstance(v, float) else str(v))
    print(f"{metric:<16} {fmt(n):>10} {fmt(c):>10}")

assert cached["llm_calls"] < naive["llm_calls"]
assert cached["cost"] < naive["cost"]
assert cached["staleness_risk"] == "yes", \
    "the honest table includes the metric the winner LOSES on"

print("\nAll Module 8 concept checks passed ✔")
