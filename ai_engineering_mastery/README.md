# AI Engineering Mastery — every buzzword, done properly

You have seen the joke: *"How to become an AI Engineer in 2026: say 'we should use
agents' twice per meeting, call every search feature RAG, add a vector database before
you have any vectors…"* This course is the serious answer. Every term the meme
lampoons — **RAG, vector databases, AI agents, multi-agent systems, MCP, LLM gateways,
semantic caching, observability, fine-tuning vs. prompting, prompt-cost optimization,
hallucinations, benchmarking and evals** — is a real engineering discipline, and here
you will implement each one from first principles in plain Python.

Eight progressive modules and one capstone take you from tokens and vector similarity
to a production-shaped, observable, cost-accounted agentic RAG pipeline. Every module
pairs a deep-dive README with runnable code, a hands-on exercise, and a reference
solution. No API keys, no third-party packages — a deterministic mock LLM and
hash-based embeddings make every file runnable offline, so you learn the *architecture*
instead of fighting SDKs.

## Who This Is For
- Engineers who can call an LLM API but want to understand what RAG, agents, and evals
  actually are under the hood — well enough to build (or reject!) each one.
- Developers tired of buzzword-driven design who want the judgment to say *when* a
  vector database, an agent, or a multi-agent system is genuinely warranted.
- Anyone preparing for AI-engineering interviews where chunking trade-offs, ReAct,
  reranking, context budgets, and eval design come up.

## How Each Module Is Structured
| File | Purpose |
|------|---------|
| `README.md` | Learning objectives + deep-dive concepts with tables and diagrams |
| `concepts.py` | Annotated, runnable examples — `python3 concepts.py` prints proof of every idea |
| `exercise.py` | Lab with numbered TODOs and self-verification checks |
| `solution.py` | Complete reference solution |

## The Curriculum
| # | Module | You Will Master |
|---|--------|-----------------|
| 01 | **[LLM Foundations](module_01_llm_foundations/README.md)** | Tokens, embeddings, cosine similarity, attention as weighted lookup, prompting patterns, fine-tune vs. prompt |
| 02 | **[RAG Fundamentals](module_02_rag_fundamentals/README.md)** | Chunking strategies, embedding pipelines, building a vector database (indexing, top-k similarity search) |
| 03 | **[Advanced RAG](module_03_advanced_rag/README.md)** | Why naive RAG plateaus, hybrid search (BM25 + vectors + RRF), query rewriting (multi-query, HyDE), cross-encoder reranking, retrieval evals |
| 04 | **[RAG Architectures](module_04_rag_architectures/README.md)** | GraphRAG, Agentic RAG, multimodal RAG, common pitfalls, and a decision framework for choosing |
| 05 | **[Single-Agent Systems](module_05_single_agent/README.md)** | Tool/function calling, the ReAct loop, argument validation, agent failure modes and the guards that catch them |
| 06 | **[Multi-Agent Systems & MCP](module_06_multi_agent/README.md)** | Orchestrator–worker pattern, an MCP-style tool protocol, information isolation, planning — and when one agent is enough |
| 07 | **[Context, Memory & Evals](module_07_context_memory_evals/README.md)** | Context-window budgeting, short/long-term memory, summarization, and a real eval harness (exact match, grounding, LLM-as-judge) |
| 08 | **[Production AI Engineering](module_08_production/README.md)** | LLM gateway (routing, fallback), semantic caching, OpenTelemetry-style tracing, cost accounting, hallucination detection, honest benchmarking |
| 🏆 | **[Capstone](capstone/README.md)** | *DeskMate* — a support-desk agentic RAG pipeline that applies every module, with evals and traces to prove it works |

## Prerequisites & Tooling
Python 3.11+ and a terminal — no third-party packages, no API keys.

```bash
python3 --version                                   # 3.11 or newer
cd ai_engineering_mastery
python3 module_01_llm_foundations/concepts.py       # every concepts.py runs standalone
```

## Suggested Learning Path
```mermaid
flowchart LR
    A[01 foundations] --> B[02 rag] --> C[03 advanced rag] --> D[04 architectures]
    D --> E[05 single agent] --> F[06 multi-agent + MCP]
    F --> G[07 context, memory, evals] --> H[08 production] --> Z[🏆 Capstone]
```

Modules 1–4 teach *retrieval* (data in, relevant context out), 5–6 teach *agency*
(models that act), 7–8 teach *engineering* (making it measurable, affordable, and
debuggable). Do them in order — later modules import ideas, vocabulary, and sometimes
code shapes from earlier ones.

## Ground Rules
1. **Run everything.** Each `concepts.py` prints and asserts observable results — read
   the output next to the source.
2. **Attempt every exercise before opening the solution.** The struggle is the course.
3. **Retrieval before generation.** Most "the model is dumb" bugs are "the context was
   wrong" bugs. You'll measure this yourself in Module 3.
4. **No component before its problem.** You earn the vector database in Module 2 by
   first feeling keyword search fail — the meme's rule 6, inverted.
5. **If you didn't eval it, it doesn't work.** Every module from 3 onward ends by
   measuring the thing it built.

Start with [module_01_llm_foundations](module_01_llm_foundations/README.md).
