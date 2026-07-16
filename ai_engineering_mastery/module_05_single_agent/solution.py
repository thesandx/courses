"""
Module 5 Solution: The Agent Runtime
====================================
Run: python3 solution.py — passes the same checks as exercise.py.
"""

import json
import re

ORDERS = {"A-17": {"item": "keyboard", "eta_days": 3},
          "B-42": {"item": "monitor", "eta_days": 7}}


def scripted_model(question: str, transcript: list[dict]) -> dict:
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


# TODO 1 — validate everything; errors are observations, not exceptions.
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, description: str, params: dict, fn):
        self._tools[name] = {"description": description, "params": params,
                             "fn": fn}

    def dispatch(self, request: dict) -> dict:
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


# TODO 2 — a while-loop around an unreliable planner, with guards.
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
        signature = json.dumps(move["action"], sort_keys=True)
        if signature in seen_actions:
            return {"answer": None, "steps": step, "transcript": transcript,
                    "stopped": "loop detected"}
        seen_actions.add(signature)
        transcript.append({"kind": "action", "payload": move["action"]})
        transcript.append({"kind": "observation",
                           "payload": registry.dispatch(move["action"])})
    return {"answer": None, "steps": max_steps, "transcript": transcript,
            "stopped": "step budget exhausted"}


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
    assert result["steps"] == 3
    kinds = [t["kind"] for t in result["transcript"]]
    assert kinds == ["thought", "action", "observation",
                     "thought", "action", "observation", "thought"]

    stuck = react_loop("where is order A-17?", looping_model, registry)
    assert stuck["answer"] is None and stuck["stopped"] == "loop detected"
    assert stuck["steps"] <= 3

    print("All solution checks passed ✔")
