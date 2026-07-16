"""
Module 5: Single-Agent Systems — Concepts in Action
===================================================
Run: python3 concepts.py

A tool registry with schema validation, a ReAct loop with a scripted model,
and every classic single-agent failure mode caught by its guard.
"""

import json
import re

# ============================================================================
# 1. Tool calling: declare, validate, dispatch
# ============================================================================
print("=" * 70)
print("1. Tool registry with schema validation")
print("=" * 70)


class ToolRegistry:
    """The runtime side of the tool-calling contract. The model only ever
    *requests*; this class validates and executes."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, description: str, params: dict, fn):
        """params: {"arg_name": {"type": type, "pattern": optional regex}}
        The description matters — the model chooses tools by reading it."""
        self._tools[name] = {"description": description, "params": params, "fn": fn}

    def schemas(self) -> str:
        """What the model sees in its prompt."""
        lines = []
        for name, tool in self._tools.items():
            sig = ", ".join(f"{p}: {spec['type'].__name__}"
                            for p, spec in tool["params"].items())
            lines.append(f"- {name}({sig}): {tool['description']}")
        return "\n".join(lines)

    def dispatch(self, request: dict) -> dict:
        """Execute a {'tool': ..., 'args': {...}} request. INVALID REQUESTS
        RETURN ERROR OBSERVATIONS — never exceptions. The model reads the
        error and gets a chance to correct itself."""
        name = request.get("tool")
        if name not in self._tools:
            return {"error": f"unknown tool {name!r}; available: "
                             f"{sorted(self._tools)}"}
        tool = self._tools[name]
        args = request.get("args", {})
        for param, spec in tool["params"].items():
            if param not in args:
                return {"error": f"missing argument {param!r}"}
            if not isinstance(args[param], spec["type"]):
                return {"error": f"argument {param!r} must be "
                                 f"{spec['type'].__name__}"}
            if "pattern" in spec and not re.fullmatch(spec["pattern"],
                                                      str(args[param])):
                return {"error": f"argument {param!r} must match "
                                 f"{spec['pattern']!r}"}
        extra = set(args) - set(tool["params"])
        if extra:
            return {"error": f"unexpected arguments {sorted(extra)}"}
        return {"result": tool["fn"](**args)}


INVOICES = {"2026-03": {"total": 4200, "status": "paid"},
            "2026-04": {"total": 5100, "status": "due"}}

registry = ToolRegistry()
registry.register(
    "lookup_invoice",
    "Get the invoice total and status for a month (format YYYY-MM).",
    {"month": {"type": str, "pattern": r"\d{4}-\d{2}"}},
    lambda month: INVOICES.get(month, "no invoice for that month"),
)
registry.register(
    "list_months",
    "List the months that have invoices.",
    {},
    lambda: sorted(INVOICES),
)

print("schemas shown to the model:")
print(registry.schemas())

ok = registry.dispatch({"tool": "lookup_invoice", "args": {"month": "2026-03"}})
print(f"valid call     -> {ok}")
assert ok["result"]["total"] == 4200

# The three stereotyped bad requests — all become observations, not crashes:
bad_tool = registry.dispatch({"tool": "send_email", "args": {}})
bad_type = registry.dispatch({"tool": "lookup_invoice", "args": {"month": 3}})
bad_fmt = registry.dispatch({"tool": "lookup_invoice", "args": {"month": "March"}})
for label, resp in (("hallucinated tool", bad_tool), ("wrong type", bad_type),
                    ("wrong format", bad_fmt)):
    print(f"{label:<18} -> {resp}")
    assert "error" in resp

# ============================================================================
# 2. The ReAct loop with a scripted model
# ============================================================================
print()
print("=" * 70)
print("2. ReAct: Reason -> Act -> Observe")
print("=" * 70)


def scripted_model(question: str, transcript: list[dict]) -> dict:
    """Stands in for the LLM. Reads the transcript (its own thoughts, actions,
    and the observations we fed back) and emits the next step. Note how it
    CORRECTS ITSELF after an error observation — that behavior is why
    dispatch() returns errors instead of raising."""
    observations = [t for t in transcript if t["kind"] == "observation"]
    if not observations:
        # First step: deliberately wrong format, like real models produce.
        return {"thought": "I need the March invoice; I'll look it up.",
                "action": {"tool": "lookup_invoice", "args": {"month": "March"}}}
    last = observations[-1]["payload"]
    if "error" in last:
        return {"thought": "Format was wrong; the schema wants YYYY-MM.",
                "action": {"tool": "lookup_invoice",
                           "args": {"month": "2026-03"}}}
    return {"thought": "I have the total; I can answer.",
            "final": f"Your March invoice totaled ${last['result']['total']} "
                     f"({last['result']['status']})."}


def react_loop(question: str, model, registry: ToolRegistry,
               max_steps: int = 6) -> dict:
    transcript: list[dict] = []
    seen_actions: set[str] = set()
    for step in range(1, max_steps + 1):
        move = model(question, transcript)
        transcript.append({"kind": "thought", "payload": move["thought"]})
        if "final" in move:
            return {"answer": move["final"], "steps": step,
                    "transcript": transcript}
        # Guard: repeated identical action = the model is looping.
        signature = json.dumps(move["action"], sort_keys=True)
        if signature in seen_actions:
            return {"answer": None, "steps": step, "transcript": transcript,
                    "stopped": "loop detected"}
        seen_actions.add(signature)
        transcript.append({"kind": "action", "payload": move["action"]})
        obs = registry.dispatch(move["action"])
        transcript.append({"kind": "observation", "payload": obs})
    return {"answer": None, "steps": max_steps, "transcript": transcript,
            "stopped": "step budget exhausted"}


result = react_loop("what was my March invoice?", scripted_model, registry)
for entry in result["transcript"]:
    payload = entry["payload"]
    print(f"  {entry['kind']:<12} {payload if isinstance(payload, str) else json.dumps(payload)}")
print(f"  answer: {result['answer']}")

assert result["answer"] is not None and "$4200" in result["answer"]
assert result["steps"] == 3, "wrong call, corrected call, final answer"
errors = [t for t in result["transcript"]
          if t["kind"] == "observation" and "error" in t["payload"]]
assert len(errors) == 1, "the model self-corrected after exactly one error"

# ============================================================================
# 3. Failure modes and guards
# ============================================================================
print()
print("=" * 70)
print("3. Failure modes caught by guards")
print("=" * 70)


def looping_model(question, transcript):
    """A model stuck re-issuing the same action — ignored observations."""
    return {"thought": "let me check the invoice",
            "action": {"tool": "lookup_invoice", "args": {"month": "2026-03"}}}


stuck = react_loop("what was my March invoice?", looping_model, registry)
print(f"looping model    -> stopped: {stuck['stopped']} after {stuck['steps']} steps")
assert stuck["stopped"] == "loop detected"
assert stuck["steps"] <= 3, "the loop detector fires on the FIRST repeat"


def chaotic_model(question, transcript):
    """A model that hallucinates a different tool every step — the step
    budget is the guard of last resort."""
    n = len(transcript)
    return {"thought": f"trying tool #{n}",
            "action": {"tool": f"imaginary_tool_{n}", "args": {}}}


chaos = react_loop("anything", chaotic_model, registry, max_steps=4)
print(f"chaotic model    -> stopped: {chaos['stopped']} after {chaos['steps']} steps")
assert chaos["stopped"] == "step budget exhausted"
assert chaos["steps"] == 4, "hard ceiling regardless of model behavior"

# Cost accounting: every step is a model call — agents multiply spend.
print(f"cost reminder    -> well-behaved: {result['steps']} calls, "
      f"chaotic without budget: unbounded")

print("\nAll Module 5 concept checks passed ✔")
