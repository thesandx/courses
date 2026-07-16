# Module 8: Production AI Engineering — Gateways, Caching, Observability, Cost

## Learning Objectives
- Build an **LLM gateway** that earns its box in the diagram: model routing,
  fallback on failure, and centralized accounting — not "one mysterious box".
- Implement a **semantic cache** (the Redis rule, done right): exact-match + embedding
  similarity, TTLs, and the invalidation trap.
- Add **OpenTelemetry-style tracing** to an AI pipeline — spans with timing, token
  counts, and parent/child structure — and know why *this* system especially needs it.
- Account for **cost per request** and reason about the cost/accuracy/latency
  triangle with numbers instead of adjectives.
- **Benchmark honestly**: report the full metric table against a baseline, not the
  one metric you win.

---

## 1. The LLM Gateway

Every team draws it; few can say what it does. A gateway is justified by exactly
three jobs, all of which need one choke point in front of N models:

| Job | Mechanism |
|-----|-----------|
| **Routing** | Send each request to the cheapest model that meets its quality tier (classify-tier traffic must not pay frontier-model prices) |
| **Fallback** | Provider outage or rate limit → retry on the next model in the tier, transparently |
| **Accounting** | Every token in/out metered per caller in ONE place — the bill is per token (Module 1) |

If your gateway does none of these, it is a proxy with a cool name. `concepts.py`
builds all three in ~60 lines, with a flaky provider to prove fallback.

## 2. Semantic Caching

"We should add Redis" is a punchline until you notice LLM calls are *expensive,
slow, and frequently repeated*. Two cache layers:

1. **Exact cache** — key = hash(model + prompt). Trivial, safe, hits only identical
   prompts.
2. **Semantic cache** — embed the prompt; if a stored prompt's similarity exceeds a
   threshold, serve its answer. Catches paraphrases ("reset my password" / "how do I
   reset my password?").

The trap is **invalidation**: a cached answer outlives the document it came from.
Cache entries need TTLs *and* source-based invalidation (the refund policy changed →
purge every answer that cited it). The threshold is a precision dial: too low and
users get *answers to someone else's question* — a cache-shaped hallucination.

## 3. Observability: Traces for a Nondeterministic System

Logs tell you a request happened; **traces** tell you what it spent and where. A
trace is a tree of **spans** — each with a name, start/end time, and attributes
(model, tokens, cache hit, retrieved doc ids):

```
trace: answer_question                     total=812ms  tokens=1450
├── span: cache_lookup                     3ms   hit=false
├── span: retrieve                         40ms  k=3
├── span: llm_call (gateway)               760ms model=medium tokens_in=1200 tokens_out=250
└── span: grounding_check                  9ms   grounded=true
```

AI pipelines need this *more* than normal services: the same code path varies 10× in
latency and cost depending on model behavior. Instrument first, then debug — but note
the meme's rule 7 cuts the other way too: spans that no one queries are just
expensive logs. Emit attributes you will actually alert on (cost, tokens, grounded?).

## 4. The Cost / Accuracy / Latency Triangle

Every architecture choice in this course moves you on this triangle:

| Lever | Cost | Accuracy | Latency |
|-------|------|----------|---------|
| Bigger model | ↑↑ | ↑ | ↑ |
| More retrieval (larger k) | ↑ | ↑ then ↓ (context rot) | ↑ |
| Reranking stage | ↑ | ↑ | ↑ |
| Semantic cache | ↓↓ on hits | = (if threshold honest) | ↓↓ on hits |
| Agentic loop | ↑ per step | ↑ on hard tasks | ↑↑ |

The discipline: attach *numbers* from your traces and evals to each lever, then
argue. "We should use agents" costs 3–10× per request — worth it exactly when evals
show the accuracy jump (and per the meme's rule 12: dashboards of per-request cost
are what keep the live demo from burning the budget).

## 5. Honest Benchmarking

Cherry-picking the one metric you win is the final boss of AI-engineering
self-deception. The antidote is mechanical:
- Fix the eval suite (Modules 3 + 7) *before* running the comparison.
- Report **every** metric — accuracy, grounded rate, p50 latency, cost per query —
  for baseline and candidate, in one table.
- Declare the trade-off in words: "candidate: +9pt grounded, +40% cost."

`concepts.py` benchmarks a cached-gateway pipeline against a naive one and prints
the full table, wins and losses both.

---

## Key Takeaways
- A gateway = routing + fallback + accounting at one choke point, or it's just a box.
- Cache exact first, semantic second; thresholds are precision dials and invalidation
  is the real problem (TTL + purge by source).
- Trace spans with token/cost attributes — nondeterministic systems are undebuggable
  without them; emit only what you'll query.
- Argue cost/accuracy/latency with measured numbers, never adjectives.
- Benchmarks report the whole table against a fixed suite — including the losses.

Next: the [Capstone](../capstone/README.md).

---

## Files in This Module
- `concepts.py` — gateway with routing/fallback/metering, two-layer cache, tracer, full benchmark
- `exercise.py` — build the gateway, semantic cache, and tracer yourself
- `solution.py` — reference solution
