"""
Real-World Exercise 3: A Tool-Calling Agent (pairs with Modules 5-6)
====================================================================
Run: python3 03_tool_calling_agent.py

Requires:  pip install openai
           export OPENROUTER_API_KEY="sk-or-..."

The ReAct loop you built in Module 5 with a scripted policy, now driven by a
real model through the OpenAI-compatible function-calling API:
  * tools declared with JSON schemas (the contract from Module 5)
  * the runtime executes; the model only ever REQUESTS
  * the loop is bounded, errors go back as tool results, and every step prints
"""

import json
import os
import sys

try:
    from openai import OpenAI
except ImportError:
    sys.exit("The 'openai' package is missing. Run:  pip install openai")

API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY:
    sys.exit("OPENROUTER_API_KEY is not set (see README.md).")

MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

# ---------------------------------------------------------------------------
# The business data and tool implementations (the runtime side)
# ---------------------------------------------------------------------------
ORDERS = {"A-17": {"item": "keyboard", "eta_days": 3, "status": "shipped"},
          "B-42": {"item": "monitor", "eta_days": 7, "status": "processing"}}

INVOICES = {"2026-06": {"total": 4200, "status": "paid"},
            "2026-07": {"total": 5100, "status": "due"}}


def track_order(order_id: str) -> dict:
    order = ORDERS.get(order_id)
    return order if order else {"error": f"no order with id {order_id!r}; "
                                         f"known ids look like 'A-17'"}


def lookup_invoice(month: str) -> dict:
    invoice = INVOICES.get(month)
    return invoice if invoice else {"error": f"no invoice for {month!r}; "
                                             f"format is YYYY-MM"}


IMPLEMENTATIONS = {"track_order": track_order, "lookup_invoice": lookup_invoice}

# The schemas the model sees — descriptions are prompt engineering (Module 5):
TOOLS = [
    {"type": "function",
     "function": {
         "name": "track_order",
         "description": "Track a customer's order. Call this whenever the "
                        "user asks where an order is or when it arrives.",
         "parameters": {
             "type": "object",
             "properties": {"order_id": {
                 "type": "string",
                 "description": "The order id, format letter-dash-digits, e.g. A-17"}},
             "required": ["order_id"],
         }}},
    {"type": "function",
     "function": {
         "name": "lookup_invoice",
         "description": "Get the invoice total and status for a month. Call "
                        "this for any billing or invoice question.",
         "parameters": {
             "type": "object",
             "properties": {"month": {
                 "type": "string",
                 "description": "The month in YYYY-MM format, e.g. 2026-06"}},
             "required": ["month"],
         }}},
]

# ---------------------------------------------------------------------------
# The ReAct loop — Module 5's shape, real model deciding the actions
# ---------------------------------------------------------------------------


def run_agent(question: str, max_steps: int = 6) -> str:
    messages = [
        {"role": "system",
         "content": "You are a support agent. Use the tools to answer; do not "
                    "guess order or invoice data. Answer in one sentence."},
        {"role": "user", "content": question},
    ]
    total_tokens = 0

    for step in range(1, max_steps + 1):                 # bounded — always
        response = client.chat.completions.create(
            model=MODEL, max_tokens=400, tools=TOOLS, messages=messages,
        )
        total_tokens += response.usage.total_tokens
        choice = response.choices[0]

        if choice.finish_reason != "tool_calls":         # the model answered
            print(f"    [{step}] final answer  ({total_tokens} tokens total)")
            return choice.message.content

        # The model requested tools. Echo its message back, then execute
        # EVERY requested call and return one result per call — the contract.
        messages.append(choice.message)
        for call in choice.message.tool_calls:
            fn_name = call.function.name
            args = json.loads(call.function.arguments)   # parse, never regex
            print(f"    [{step}] tool request  {fn_name}({args})")

            fn = IMPLEMENTATIONS.get(fn_name)
            # Errors become observations, not crashes (Module 5's guard):
            result = fn(**args) if fn else {"error": f"unknown tool {fn_name!r}"}
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

    return "step budget exhausted — the loop is bounded for a reason"


print("=" * 70)
print(f"Tool-calling agent  (model: {MODEL})")
print("=" * 70)

for question in [
    "Where is my order B-42 and when will it arrive?",
    "How much was the June 2026 invoice, and is it paid?",
    "Track order Z-99 for me.",                # doesn't exist — error feedback
]:
    print(f"\nQ: {question}")
    answer = run_agent(question)
    print(f"A: {answer}")

print("\nExercise 3 complete ✔")

# ---------------------------------------------------------------------------
# YOUR TURN
# ---------------------------------------------------------------------------
# 1. Ask a question needing BOTH tools ("is my June invoice paid and where is
#    order A-17?") — many models will issue parallel tool calls in one step.
# 2. Add the Module 5 loop detector: if the model requests the identical
#    (name, arguments) twice, stop with "loop detected".
# 3. Add a third tool `refund_order` and require a confirmation step before
#    executing it — write tools are a security boundary (Module 5).
