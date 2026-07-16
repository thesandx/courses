"""
Module 4 Exercise: GraphRAG and the Agentic Loop
================================================
Goal
----
Build the knowledge-graph triple store, answer a multi-hop question by
traversal, and implement the bounded agentic retrieval loop.

Complete the TODOs below, then run:  python3 exercise.py
All assertions at the bottom must pass. Try it before opening solution.py!
"""

import re


# ---------------------------------------------------------------------------
# Provided: corpus and a scripted retriever + policy (the "LLM" parts)
# ---------------------------------------------------------------------------
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
    """Stands in for vector search: returns the best doc for known queries."""
    if "fixed" in query and "E-1234" in query:
        return CORPUS[1]
    if "Priya report" in query:
        return CORPUS[2]
    if "Marcus report" in query:
        return CORPUS[3]
    return None


def scripted_policy(evidence: list[str]) -> tuple[str, str]:
    """Stands in for the model's decision. Returns (action, argument) where
    action is 'retrieve' or 'answer'."""
    text = " ".join(evidence)
    if "fixed ticket" not in text:
        return ("retrieve", "who fixed ticket E-1234")
    m = re.search(r"(\w+) fixed ticket", text)
    if f"{m.group(1)} reports to" not in text:
        return ("retrieve", f"who does {m.group(1)} report to")
    mgr = re.search(rf"{m.group(1)} reports to (\w+)", text).group(1)
    return ("answer", f"{mgr} manages {m.group(1)}")


# ---------------------------------------------------------------------------
# TODO 1 — class KnowledgeGraph
# ---------------------------------------------------------------------------
# Implement:
#   * add(subj, rel, obj) — store the triple; ignore exact duplicates
#   * objects(subj, rel) -> list[str]   — all o where (subj, rel, o)
#   * subjects(rel, obj) -> list[str]   — all s where (s, rel, obj)
#   * hop(start, *relations) -> list[str]
#       follow relations in sequence from `start`, breadth-style:
#       hop("Priya", "reports_to") == ["Marcus"]
#       hop("Priya", "reports_to", "reports_to") == ["Dana"]
#       hop("Priya", "reports_to", "leads") == ["payments team"]


# ---------------------------------------------------------------------------
# TODO 2 — agentic_loop(policy, retrieve, max_steps=5)
# ---------------------------------------------------------------------------
# The bounded loop:
#   * start with empty evidence
#   * each step: (action, arg) = policy(evidence)
#       - "retrieve": doc = retrieve(arg); append it to evidence if it is
#         not None and not already present
#       - "answer": return {"answer": arg, "steps": steps_used,
#                           "evidence": evidence}
#   * if max_steps is exhausted, return {"answer": None, "steps": max_steps,
#     "evidence": evidence}  — an agent without a step budget is an outage.


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    kg = KnowledgeGraph()
    for t in TRIPLES:
        kg.add(*t)
    kg.add(*TRIPLES[0])                       # duplicate must be ignored
    assert len(kg.triples) == len(TRIPLES)

    assert kg.objects("Priya", "reports_to") == ["Marcus"]
    assert kg.subjects("fixed", "E-1234") == ["Priya"]
    assert kg.hop("Priya", "reports_to") == ["Marcus"]
    assert kg.hop("Priya", "reports_to", "reports_to") == ["Dana"]
    assert kg.hop("Priya", "reports_to", "leads") == ["payments team"]
    assert kg.hop("Priya", "manages") == []

    # Multi-hop question answered by traversal, no embeddings involved:
    fixer = kg.subjects("fixed", "E-1234")[0]
    skip_manager = kg.hop(fixer, "reports_to", "reports_to")
    assert skip_manager == ["Dana"], "who is the fixer's skip-level manager?"

    result = agentic_loop(scripted_policy, scripted_retrieve, max_steps=5)
    assert result["answer"] == "Marcus manages Priya"
    assert result["steps"] == 3, "retrieve, retrieve, answer"
    assert len(result["evidence"]) == 2

    # A policy that never answers must hit the budget, not hang:
    looping = lambda evidence: ("retrieve", "who fixed ticket E-1234")
    result2 = agentic_loop(looping, scripted_retrieve, max_steps=4)
    assert result2["answer"] is None and result2["steps"] == 4

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Write extract_triples(corpus) with regexes to build TRIPLES from CORPUS.
# 2. Add hop() support for inverse relations ("~fixed" walks object->subject).
# 3. Make the loop detect a repeated (action, arg) pair and stop early with
#    reason="loop detected" — you will build this guard for real in Module 5.
