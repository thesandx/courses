"""
Module 5 Exercise: Build the Agent Runtime
==========================================
Goal
----
Implement the two halves of a single-agent system: the validating tool
registry (the runtime's side of the contract) and the guarded ReAct loop.

Complete the TODOs below, then run:  python3 exercise.py
All assertions at the bottom must pass. Try it before opening solution.py!
"""

import json
import re


# ---------------------------------------------------------------------------
# Provided: business data and scripted models to drive your loop
# ---------------------------------------------------------------------------
ORDERS = {"A-17": {"item": "keyboard", "eta_days": 3},
          "B-42": {"item": "monitor", "eta_days": 7}}


def scripted_model(question: str, transcript: list[dict]) -> dict:
    """Asks for order B-42 with a bad id first, corrects after the error."""
    observations = [t for t in transcript if t["kind"] == "observation"]
    if not observations:
        return {"thought": "look up the order",
                "action": {"tool": "track_order", "args": {"order_id": "b42"}}}
    last = observations[-1]["payload"]
    if "error" in last:
        return {"thought": "ids look like X-NN; retry with B-42",
                "action": {"tool": "track_order", "args": {"order_id": "B-42"}}}
    return {"thought": "done",
            "final": f"ETA {last['result']['eta_days']} days"}


def looping_model(question: str, transcript: list[dict]) -> dict:
    return {"thought": "check the order",
            "action": {"tool": "track_order", "args": {"order_id": "A-17"}}}


# ---------------------------------------------------------------------------
# TODO 1 — class ToolRegistry
# ---------------------------------------------------------------------------
# Implement:
#   * register(name, description, params, fn)
#       params: {"arg": {"type": <python type>, "pattern": <optional regex>}}
#   * dispatch(request) -> dict
#       request: {"tool": name, "args": {...}}
#       Return {"result": fn(**args)} on success. Return {"error": "..."} —
#       NEVER raise — when: the tool is unknown, an argument is missing, an
#       argument has the wrong type, an argument fails its regex
#       (re.fullmatch), or unexpected arguments are present.


# ---------------------------------------------------------------------------
# TODO 2 — react_loop(question, model, registry, max_steps=6)
# ---------------------------------------------------------------------------
# Each step:
#   1. move = model(question, transcript)  — has "thought" plus either
#      "final" (str) or "action" ({"tool", "args"})
#   2. append {"kind": "thought", "payload": ...} to the transcript
#   3. "final" -> return {"answer": final, "steps": step, "transcript": ...}
#   4. otherwise: if this exact action (json.dumps(action, sort_keys=True))
#      was already executed, return answer=None with stopped="loop detected"
#   5. append the action to the transcript, dispatch it, append the
#      observation ({"kind": "observation", "payload": dispatch_result})
# If max_steps runs out: answer=None, stopped="step budget exhausted".


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    registry = ToolRegistry()
    registry.register(
        "track_order",
        "Track an order by id (format X-NN).",
        {"order_id": {"type": str, "pattern": r"[A-Z]-\d{2}"}},
        lambda order_id: ORDERS.get(order_id, "not found"),
    )

    ok = registry.dispatch({"tool": "track_order", "args": {"order_id": "A-17"}})
    assert ok == {"result": {"item": "keyboard", "eta_days": 3}}

    assert "error" in registry.dispatch({"tool": "nope", "args": {}})
    assert "error" in registry.dispatch({"tool": "track_order", "args": {}})
    assert "error" in registry.dispatch(
        {"tool": "track_order", "args": {"order_id": 42}})
    assert "error" in registry.dispatch(
        {"tool": "track_order", "args": {"order_id": "b42"}})
    assert "error" in registry.dispatch(
        {"tool": "track_order", "args": {"order_id": "A-17", "rush": True}})

    result = react_loop("where is order B-42?", scripted_model, registry)
    assert result["answer"] == "ETA 7 days"
    assert result["steps"] == 3, "bad call, corrected call, final"
    kinds = [t["kind"] for t in result["transcript"]]
    assert kinds == ["thought", "action", "observation",
                     "thought", "action", "observation", "thought"]

    stuck = react_loop("where is order A-17?", looping_model, registry)
    assert stuck["answer"] is None and stuck["stopped"] == "loop detected"
    assert stuck["steps"] <= 3

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Add a token budget: sum len(json.dumps(payload))//4 over the transcript
#    and stop with "token budget exhausted" past a limit.
# 2. Allow up to N validation-error retries per tool before hard-stopping —
#    the model deserves a second chance, not a tenth.
# 3. Add a read_only flag per tool and require explicit confirmation entries
#    in the transcript before dispatching non-read-only tools.
