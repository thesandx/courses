# Module 7: Context Engineering, Memory & Evals

## Learning Objectives
- Distinguish **context engineering from prompt engineering**: managing *everything*
  in the window — instructions, history, retrievals, tool results — as a budget.
- Implement a **token budgeter** that packs the window by priority and degrades
  gracefully instead of truncating blindly.
- Build **short-term memory** (a rolling conversation buffer with summarization) and
  **long-term memory** (vector-store recall of durable facts).
- Understand memory in **multi-agent** settings: what is shared, what is private,
  and why "everyone remembers everything" recreates the isolation bugs of Module 6.
- Build an **eval harness** for generated answers: exact checks, grounding checks,
  and a rubric-scoring judge — then run it end-to-end over a pipeline.

---

## 1. Context Engineering vs Prompt Engineering

Prompt engineering wordsmiths one message. Context engineering manages the whole
window over time:

| | Prompt engineering | Context engineering |
|---|---|---|
| Object | One string | The full window: system + history + retrievals + tool results + memory |
| Question | "How do I phrase this?" | "What earns its tokens *this* call?" |
| Failure | Awkward answer | Truncated instructions, forgotten decisions, context rot |

Two facts drive everything: the window is **finite**, and (Module 1) everything in
it **competes for attention** — irrelevant content actively degrades answers, it
doesn't just cost money. So context is a *budget allocation problem*:

```
priority 1: system contract        (never dropped)
priority 2: the current question   (never dropped)
priority 3: retrieved evidence     (drop lowest-relevance first)
priority 4: conversation history   (summarize, then drop oldest)
```

## 2. Short-Term Memory: The Rolling Buffer

Conversations outgrow windows. The standard shape: keep the last N turns verbatim,
**summarize** the overflow into a compact digest, never silently drop.

```mermaid
flowchart LR
    T[new turn] --> B[buffer]
    B -- over budget --> S[summarize oldest turns] --> D[digest]
    D --> C[context: digest + recent turns verbatim]
    B -- within budget --> C
```

> **Pitfall:** summarization is lossy in a *biased* way — decisions and numbers
> survive, hedges and reasoning die. Pin critical facts (order IDs, constraints the
> user stated) into structured memory instead of trusting the summary to keep them.

## 3. Long-Term Memory: Retrieval Again

Durable facts ("Ada prefers email", "staging DB is read-only") must survive across
sessions. Long-term memory is RAG applied to your own past: store facts in a vector
store at write time, retrieve the top-k *relevant to the current question* at read
time. Everything from Modules 2–3 applies — including the evals.

In **multi-agent** systems memory needs an owner: shared memory (the plan, user
preferences) is written by the orchestrator; a worker's scratch memory stays private.
Letting every agent write shared memory reintroduces contradiction (Module 6) as a
*persistent* bug.

## 4. Evals for Generation

Module 3 evaluated retrieval. Generation needs three layers, cheapest first:

| Layer | Checks | Catches |
|-------|--------|---------|
| Deterministic | Exact/regex match, JSON parses, required fields | Format drift, flat wrong answers |
| **Grounding** | Is every claimed fact supported by the retrieved context? | Hallucination (the meme's "edge case") |
| LLM-as-judge | Rubric scoring: correct? complete? concise? | Quality no regex can see |

Rules that keep evals honest:
1. **Judge with a rubric, not vibes** — "score correctness 0–2 against this reference"
   beats "is this good?".
2. **Calibrate the judge** on a handful of hand-labeled cases before trusting it.
3. **Evals are regression tests.** Run the suite on every prompt/retriever change;
   a one-point drop caught pre-deploy is worth the whole harness.

`concepts.py` ends by running a full suite over the Module 2 pipeline — the
"run a full eval suite on your pipeline" moment this module exists for.

---

## Key Takeaways
- Context is a prioritized token budget; irrelevant content degrades, not just costs.
- Short-term memory = recent turns verbatim + summarized overflow; pin critical facts.
- Long-term memory is RAG over your own past; in multi-agent systems, memory needs
  an owner.
- Eval generation in layers: deterministic → grounding → rubric judge, calibrated.
- Evals are regression tests for AI behavior — no change ships without the suite.

Next: [Module 8 — Production AI Engineering](../module_08_production/README.md).

---

## Files in This Module
- `concepts.py` — budget packer, rolling buffer + summarizer, vector-store memory, three-layer eval harness
- `exercise.py` — build the budgeter, memory, and grounding check yourself
- `solution.py` — reference solution
