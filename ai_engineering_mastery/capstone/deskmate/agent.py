"""Modules 4-5: the tool registry and the guarded ReAct loop.

The 'model' is a scripted policy: search the KB with the user's question,
then answer extractively from the best chunk. Swap `scripted_policy` for a
real LLM call and nothing else changes — that is the point of the shape.
"""

import json


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, description: str, fn):
        self._tools[name] = {"description": description, "fn": fn}

    def dispatch(self, request: dict) -> dict:
        name = request.get("tool")
        if name not in self._tools:
            return {"error": f"unknown tool {name!r}"}
        try:
            return {"result": self._tools[name]["fn"](**request.get("args", {}))}
        except TypeError as exc:
            return {"error": str(exc)}


def scripted_policy(question: str, transcript: list[dict]) -> dict:
    observations = [t for t in transcript if t["kind"] == "observation"]
    if not observations:
        return {"thought": "search the knowledge base first",
                "action": {"tool": "search_kb", "args": {"query": question}}}
    last = observations[-1]["payload"]
    if "error" in last:
        return {"thought": "tool failed; give up honestly",
                "final": None}
    chunks = last["result"]
    if not chunks:
        return {"thought": "nothing relevant found; refuse",
                "final": None}
    return {"thought": "answer extractively from the best chunk",
            "final": chunks[0]}


def react_loop(question: str, policy, registry: ToolRegistry,
               max_steps: int = 5) -> dict:
    transcript: list[dict] = []
    seen: set[str] = set()
    evidence: list[str] = []
    for step in range(1, max_steps + 1):
        move = policy(question, transcript)
        transcript.append({"kind": "thought", "payload": move["thought"]})
        if "final" in move:
            return {"answer": move["final"], "steps": step,
                    "evidence": evidence, "transcript": transcript}
        signature = json.dumps(move["action"], sort_keys=True)
        if signature in seen:
            return {"answer": None, "steps": step, "evidence": evidence,
                    "transcript": transcript, "stopped": "loop detected"}
        seen.add(signature)
        transcript.append({"kind": "action", "payload": move["action"]})
        obs = registry.dispatch(move["action"])
        if "result" in obs and isinstance(obs["result"], list):
            evidence.extend(obs["result"])
        transcript.append({"kind": "observation", "payload": obs})
    return {"answer": None, "steps": max_steps, "evidence": evidence,
            "transcript": transcript, "stopped": "step budget exhausted"}
