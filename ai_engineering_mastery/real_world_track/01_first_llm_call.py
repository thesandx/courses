"""
Real-World Exercise 1: Your First LLM Call (pairs with Module 1)
================================================================
Run: python3 01_first_llm_call.py

Requires:  pip install openai
           export OPENROUTER_API_KEY="sk-or-..."
Optional:  export OPENROUTER_MODEL="openai/gpt-4o-mini"   (any OpenRouter model id)

What Module 1 taught with a mock, you now do for real:
  1. make an API call through an OpenAI-compatible endpoint (OpenRouter)
  2. send a STRUCTURED prompt (role / instructions / context / question)
  3. read token usage off the response — the habit that Module 8 turns into
     cost accounting
"""

import os
import sys

# ---------------------------------------------------------------------------
# Client setup — the only OpenRouter-specific code in this whole track.
# ---------------------------------------------------------------------------
try:
    from openai import OpenAI
except ImportError:
    sys.exit("The 'openai' package is missing. Run:  pip install openai")

API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY:
    sys.exit("OPENROUTER_API_KEY is not set. Get a key at https://openrouter.ai/keys\n"
             "then:  export OPENROUTER_API_KEY='sk-or-...'")

MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

# ---------------------------------------------------------------------------
# 1. The simplest possible call
# ---------------------------------------------------------------------------
print("=" * 70)
print(f"1. Basic call  (model: {MODEL})")
print("=" * 70)

response = client.chat.completions.create(
    model=MODEL,
    max_tokens=200,
    messages=[
        {"role": "user", "content": "In one sentence: what is a token in an LLM?"},
    ],
)

choice = response.choices[0]
print(f"answer        : {choice.message.content}")
print(f"finish_reason : {choice.finish_reason}")   # 'stop' = clean; 'length' = truncated!

# ---------------------------------------------------------------------------
# 2. The structured prompt from Module 1, for real
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("2. Structured prompt: contract first, context middle, ask last")
print("=" * 70)

CONTEXT = [
    "Refunds are processed within 5 business days.",
    "Refund requests require the original order id.",
]

system_prompt = (
    "You are a support engineer for AcmeDB.\n"
    "Answer ONLY from the provided context. If the answer is not in the "
    "context, reply exactly: I don't know."
)
user_prompt = (
    "CONTEXT:\n"
    + "\n".join(f"[doc {i + 1}] {c}" for i, c in enumerate(CONTEXT))
    + "\n\nQUESTION: how long do refunds take?"
)

response = client.chat.completions.create(
    model=MODEL,
    max_tokens=200,
    messages=[
        {"role": "system", "content": system_prompt},   # the contract
        {"role": "user", "content": user_prompt},        # context + ask
    ],
)
print(f"grounded answer: {response.choices[0].message.content}")

# The refusal rule must actually work — ask something the context can't answer:
response2 = client.chat.completions.create(
    model=MODEL,
    max_tokens=200,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.replace(
            "how long do refunds take?", "what is the CEO's name?")},
    ],
)
print(f"out-of-context : {response2.choices[0].message.content}")

# ---------------------------------------------------------------------------
# 3. Token usage — read it on EVERY call
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("3. Usage accounting (Module 8 starts here)")
print("=" * 70)

usage = response.usage
print(f"prompt_tokens     : {usage.prompt_tokens}")
print(f"completion_tokens : {usage.completion_tokens}")
print(f"total_tokens      : {usage.total_tokens}")
print("(OpenRouter's dashboard shows the exact $ cost per request per model —")
print(" the gateway you built in Module 8 is what OpenRouter is at scale.)")

print("\nExercise 1 complete ✔")

# ---------------------------------------------------------------------------
# YOUR TURN
# ---------------------------------------------------------------------------
# 1. Compare Module 1's estimate_tokens() heuristic against usage.prompt_tokens
#    for the same text. How far off is chars/4 for prose vs code?
# 2. Set max_tokens=10 and observe finish_reason == "length" — this is the
#    truncation failure your production code must detect.
# 3. Change OPENROUTER_MODEL to a different provider's model and re-run:
#    same code, different model — that's the point of a gateway.
