# Real-World API Track — From Mock LLM to Production Calls (OpenRouter)

Modules 1–8 teach the architecture with deterministic mock LLMs so everything runs
offline and free. This track is the bridge to real-world projects: the **same
patterns, now against a live LLM API**. It uses **OpenRouter** through the
**OpenAI-compatible API** — one key, one client, and you can swap between hundreds
of models (GPT, Claude, Gemini, Llama, …) by changing a single string, which is
exactly the Module 8 gateway idea in the real world.

Each exercise pairs with the module that taught the concept — do the module first,
then its real-API twin here.

## Setup (one time)

```bash
pip install openai                                   # exercises 1-4, 7 (works with any OpenAI-compatible API)
pip install langchain langchain-openai               # exercise 5
pip install mcp                                      # exercise 6
export OPENROUTER_API_KEY="sk-or-..."                # from https://openrouter.ai/keys
export OPENROUTER_MODEL="openai/gpt-4o-mini"         # optional; any OpenRouter model id
python3 01_first_llm_call.py                         # verify the setup works
```

The only OpenRouter-specific line in every script is the client construction:

```python
from openai import OpenAI
client = OpenAI(base_url="https://openrouter.ai/api/v1",
                api_key=os.environ["OPENROUTER_API_KEY"])
```

Everything after that is the standard OpenAI-compatible surface
(`client.chat.completions.create(...)`) — the same code works against OpenAI
directly, a local vLLM/Ollama server, or any other compatible endpoint by
changing `base_url`. Every script checks for credentials and tells you what's
missing instead of crashing.

## The Exercises

| Script | Pairs with | You will do for real |
|--------|-----------|----------------------|
| `01_first_llm_call.py` | Module 1 | Your first API call, structured prompt sections, reading token usage from the response |
| `02_rag_with_real_llm.py` | Modules 2–3 | Retrieval from your own vector store + **grounded generation** with JSON-mode citations |
| `03_tool_calling_agent.py` | Modules 5–6 | A real agent: OpenAI-style function tools + the ReAct loop you built in Module 5, now driven by a real model |
| `04_eval_llm_judge.py` | Modules 7–8 | A real **LLM-as-judge** eval suite: rubric grading, grounding checks, the honest results table |
| `05_langchain_workflow.py` | Modules 2–4 | **LangChain & AI workflows**: LCEL chains, a classify-and-route workflow, and a RAG chain over your own retriever |
| `06_mcp_real.py` | Module 6 | **Real MCP**: a FastMCP server over stdio, runtime tool discovery, and an LLM agent calling the discovered tools |
| `07_multi_agent_swarm.py` | Module 6 | **Multi-agent swarm**: an orchestrator model planning subtasks, parallel specialist workers, conflict-aware synthesis, and the honest cost line |

Do them in order — each reuses ideas (and sometimes code) from the previous one.

## Ground Rules for the Real World

1. **Never hardcode API keys.** Environment variables or a secrets manager, always.
2. **Read `response.usage` on every call** — prompt tokens, completion tokens. If
   you didn't measure it, you can't optimize it (Module 8). OpenRouter's dashboard
   shows the per-model cost of every request.
3. **Handle errors with typed exceptions** (`openai.RateLimitError`,
   `openai.APIStatusError`), never by string-matching messages.
4. **Check `finish_reason` before trusting content** — `length` means truncation,
   `tool_calls` means the model wants a tool, not an answer.
5. **The evals from Module 7 apply unchanged.** A real model makes them *more*
   necessary, not less: real models drift, get updated, and different models
   behind the same OpenRouter key behave differently — the suite is how you
   compare them honestly.

## Cost Expectations

All four scripts together make ~10 short calls. With the default
`openai/gpt-4o-mini` a full run costs a fraction of a cent; pick a bigger model
via `OPENROUTER_MODEL` when you want to compare quality (then re-run exercise 4
and look at the table — that's the whole point).

## Where to Go Next

- Swap the hash embeddings in exercise 2 for a real embedding model and re-run
  the Module 3 retrieval evals against it — measure the recall jump.
- Add the semantic cache from Module 8 in front of exercise 2's `ask()` and watch
  repeated questions cost zero.
- Run exercise 4 against two different `OPENROUTER_MODEL`s and compare the full
  tables — a real model benchmark, done honestly (Module 8, rule 14 of the meme).
- Rebuild the DeskMate capstone with exercises 2 + 3 + 4 as the LLM layer — that
  is a genuinely production-shaped RAG agent.
