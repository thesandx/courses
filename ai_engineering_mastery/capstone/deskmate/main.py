"""DeskMate: the full pipeline, end to end.

Run from the capstone/ directory:  python3 -m deskmate.main

question -> semantic cache -> agent (ReAct + search_kb) -> gateway
         -> grounding gate -> answer, traced and metered throughout;
then the eval suite scores the whole system and prints the honest table.
"""

from .agent import ToolRegistry, react_loop, scripted_policy
from .evals import run_suite, check_grounding
from .knowledge import build_store
from .production import Gateway, SemanticCache, Tracer


class DeskMate:
    def __init__(self):
        self.store = build_store()
        self.gateway = Gateway()
        self.cache = SemanticCache(threshold=0.85, ttl_seconds=3600)
        self.tracer = Tracer()
        self.registry = ToolRegistry()
        self.registry.register(
            "search_kb", "Search the support knowledge base.",
            lambda query: [rec["text"] for _, rec in
                           self.store.search(query, k=2)])
        self._clock = 0.0

    def ask(self, question: str) -> dict:
        self._clock += 1.0
        self.tracer.start("ask", question=question[:40])

        self.tracer.start("cache_lookup")
        cached = self.cache.get(question, self._clock)
        self.tracer.end(hit=bool(cached))
        if cached:
            self.tracer.end(cached=True, cost=0.0)
            return {"answer": cached, "evidence": [cached], "cost": 0.0,
                    "cached": True}

        self.tracer.start("agent_loop")
        run = react_loop(question, scripted_policy, self.registry)
        self.tracer.end(steps=run["steps"])

        if run["answer"] is None:
            self.tracer.end(refused=True, cost=0.0)
            return {"answer": None, "evidence": run["evidence"], "cost": 0.0,
                    "cached": False}

        self.tracer.start("llm_call")
        result = self.gateway.complete(prompt=question, answer=run["answer"])
        self.tracer.end(model=result["model"], tokens=result["tokens"],
                        cost=round(result["cost"], 5))

        self.tracer.start("grounding_gate")
        grounded = check_grounding(result["answer"], run["evidence"])
        self.tracer.end(grounded=grounded)
        if not grounded:
            # Never ship a fabricated figure: refuse and flag for review.
            self.tracer.end(refused=True, cost=round(result["cost"], 5))
            return {"answer": None, "evidence": run["evidence"],
                    "cost": result["cost"], "cached": False, "flagged": True}

        self.cache.put(question, result["answer"], source="handbook.md",
                       now=self._clock)
        self.tracer.end(cached=False, cost=round(result["cost"], 5))
        return {"answer": result["answer"], "evidence": run["evidence"],
                "cost": result["cost"], "cached": False}


def main():
    desk = DeskMate()

    print("=" * 70)
    print("DeskMate demo")
    print("=" * 70)
    first = desk.ask("how long do refunds take?")
    print(f"Q: how long do refunds take?\nA: {first['answer']}")
    assert first["answer"] and "5 business days" in first["answer"]
    assert not first["cached"]

    # A paraphrase hits the semantic cache: zero cost, zero model calls.
    repeat = desk.ask("how long do refunds usually take?")
    assert repeat["cached"] and repeat["cost"] == 0.0
    print(f"Q: how long do refunds usually take?  -> semantic cache hit ($0)")

    # The handbook changes: purge, and the next ask pays for a fresh answer.
    purged = desk.cache.invalidate_source("handbook.md")
    fresh = desk.ask("how long do refunds take?")
    assert purged >= 1 and not fresh["cached"]
    print(f"handbook updated -> purged {purged} cached answer(s), re-answered")

    print()
    print("=" * 70)
    print("Trace of the first request")
    print("=" * 70)
    first_spans = [s for s in desk.tracer.spans][:6]
    print(desk.tracer.report().split("\n\n")[0])
    assert any(s["name"] == "grounding_gate" for s in first_spans)

    print()
    print("=" * 70)
    print("Eval suite (the honest table)")
    print("=" * 70)
    suite_desk = DeskMate()                      # fresh: no cache warm-up
    suite = run_suite(suite_desk.ask)
    for row in suite["rows"]:
        print(f"  {row['question']:<48} answered={row['answered']} "
              f"grounded={row['grounded']} judge={row['judge']}/2")
    print(f"\n  answer_rate={suite['answer_rate']:.2f}  "
          f"grounded_rate={suite['grounded_rate']:.2f}  "
          f"judge_score={suite['judge_score']:.2f}  "
          f"total_cost=${suite['total_cost']:.4f}")
    print(f"  gateway usage: {suite_desk.gateway.usage['calls']} calls, "
          f"${suite_desk.gateway.usage['cost']:.4f}")

    assert suite["answer_rate"] == 1.0
    assert suite["grounded_rate"] == 1.0
    assert suite["judge_score"] >= 0.75
    assert suite_desk.gateway.usage["cost"] < 0.20, "demo must not burn the budget"

    print("\nDeskMate: all capstone checks passed ✔")


if __name__ == "__main__":
    main()
