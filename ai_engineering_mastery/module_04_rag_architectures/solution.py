"""
Module 4 Solution: GraphRAG and the Agentic Loop
================================================
Run: python3 solution.py — passes the same checks as exercise.py.
"""

import re

CORPUS = [
    "The billing outage on May 3rd was traced to ticket E-1234.",
    "Priya fixed ticket E-1234 after the billing outage.",
    "Priya reports to Marcus, who leads the payments team.",
    "Marcus reports to Dana, who leads engineering.",
]

TRIPLES = [
    ("Priya", "fixed", "E-1234"),
    ("Priya", "reports_to", "Marcus"),
    ("Marcus", "leads", "payments team"),
    ("Marcus", "reports_to", "Dana"),
    ("Dana", "leads", "engineering"),
]


def scripted_retrieve(query: str) -> str | None:
    if "fixed" in query and "E-1234" in query:
        return CORPUS[1]
    if "Priya report" in query:
        return CORPUS[2]
    if "Marcus report" in query:
        return CORPUS[3]
    return None


def scripted_policy(evidence: list[str]) -> tuple[str, str]:
    text = " ".join(evidence)
    if "fixed ticket" not in text:
        return ("retrieve", "who fixed ticket E-1234")
    m = re.search(r"(\w+) fixed ticket", text)
    if f"{m.group(1)} reports to" not in text:
        return ("retrieve", f"who does {m.group(1)} report to")
    mgr = re.search(rf"{m.group(1)} reports to (\w+)", text).group(1)
    return ("answer", f"{mgr} manages {m.group(1)}")


# TODO 1 — a triple store where multi-hop questions become edge walks.
class KnowledgeGraph:
    def __init__(self):
        self.triples: list[tuple[str, str, str]] = []

    def add(self, subj: str, rel: str, obj: str):
        triple = (subj, rel, obj)
        if triple not in self.triples:
            self.triples.append(triple)

    def objects(self, subj: str, rel: str) -> list[str]:
        return [o for s, r, o in self.triples if s == subj and r == rel]

    def subjects(self, rel: str, obj: str) -> list[str]:
        return [s for s, r, o in self.triples if r == rel and o == obj]

    def hop(self, start: str, *relations: str) -> list[str]:
        frontier = [start]
        for rel in relations:
            next_frontier: list[str] = []
            for node in frontier:
                for obj in self.objects(node, rel):
                    if obj not in next_frontier:
                        next_frontier.append(obj)
            frontier = next_frontier
        return frontier


# TODO 2 — the bounded loop: inspect evidence, act, never run forever.
def agentic_loop(policy, retrieve, max_steps: int = 5) -> dict:
    evidence: list[str] = []
    for step in range(1, max_steps + 1):
        action, arg = policy(evidence)
        if action == "answer":
            return {"answer": arg, "steps": step, "evidence": evidence}
        doc = retrieve(arg)
        if doc is not None and doc not in evidence:
            evidence.append(doc)
    return {"answer": None, "steps": max_steps, "evidence": evidence}


if __name__ == "__main__":
    kg = KnowledgeGraph()
    for t in TRIPLES:
        kg.add(*t)
    kg.add(*TRIPLES[0])
    assert len(kg.triples) == len(TRIPLES)

    assert kg.objects("Priya", "reports_to") == ["Marcus"]
    assert kg.subjects("fixed", "E-1234") == ["Priya"]
    assert kg.hop("Priya", "reports_to") == ["Marcus"]
    assert kg.hop("Priya", "reports_to", "reports_to") == ["Dana"]
    assert kg.hop("Priya", "reports_to", "leads") == ["payments team"]
    assert kg.hop("Priya", "manages") == []

    fixer = kg.subjects("fixed", "E-1234")[0]
    skip_manager = kg.hop(fixer, "reports_to", "reports_to")
    assert skip_manager == ["Dana"]

    result = agentic_loop(scripted_policy, scripted_retrieve, max_steps=5)
    assert result["answer"] == "Marcus manages Priya"
    assert result["steps"] == 3
    assert len(result["evidence"]) == 2

    looping = lambda evidence: ("retrieve", "who fixed ticket E-1234")
    result2 = agentic_loop(looping, scripted_retrieve, max_steps=4)
    assert result2["answer"] is None and result2["steps"] == 4

    print("All solution checks passed ✔")
