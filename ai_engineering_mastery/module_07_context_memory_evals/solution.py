"""
Module 7 Solution: Budgeter, Memory, and the Grounding Check
============================================================
Run: python3 solution.py — passes the same checks as exercise.py.
"""


def count_tokens(text: str) -> int:
    return len(text.split())


def summarize(turns: list[str]) -> str:
    keep = [w for t in turns for w in t.split()
            if w[:1].isupper() or any(ch.isdigit() for ch in w)]
    return "digest: " + " ".join(keep[:12])


# TODO 1 — priorities, not truncation: contract > question > evidence > digest.
def pack_context(system: str, question: str, evidence: list[tuple[float, str]],
                 digest: str, budget: int) -> dict:
    required = count_tokens(system) + count_tokens(question)
    assert required <= budget, "budget can't even fit the contract + question"
    remaining = budget - required

    kept, dropped = [], []
    for score, chunk in sorted(evidence, key=lambda p: -p[0]):
        cost = count_tokens(chunk)
        if cost <= remaining:
            kept.append(chunk)
            remaining -= cost
        else:
            dropped.append(chunk)

    kept_digest = digest if count_tokens(digest) <= remaining else ""
    if kept_digest:
        remaining -= count_tokens(kept_digest)
    return {"evidence": kept, "dropped": dropped, "digest": kept_digest,
            "unused_tokens": remaining}


# TODO 2 — verbatim recency + summarized overflow + pinned facts.
class ConversationMemory:
    def __init__(self, max_verbatim: int = 4):
        self.digest = ""
        self.recent: list[str] = []
        self.max_verbatim = max_verbatim
        self.pinned: list[str] = []

    def add_turn(self, turn: str):
        self.recent.append(turn)
        if len(self.recent) > self.max_verbatim:
            overflow = self.recent[:-self.max_verbatim]
            self.recent = self.recent[-self.max_verbatim:]
            merged = ([self.digest] if self.digest else []) + overflow
            self.digest = summarize(merged)

    def pin(self, fact: str):
        self.pinned.append(fact)

    def context(self) -> str:
        parts = []
        if self.pinned:
            parts.append("PINNED: " + "; ".join(self.pinned))
        if self.digest:
            parts.append(self.digest)
        parts.extend(self.recent)
        return "\n".join(parts)


# TODO 3 — a claimed number with no source is a hallucination, definitionally.
def check_grounding(answer: str, context: list[str]) -> bool:
    ctx = " ".join(context).lower()
    for word in answer.lower().split():
        word = word.strip(".,")
        if word.isdigit() and word not in ctx:
            return False
    return True


if __name__ == "__main__":
    evidence = [
        (0.9, "Refunds take 5 business days."),
        (0.5, "Refunds need the original order id."),
        (0.1, "The office dog attends standups."),
    ]
    packed = pack_context("Answer from context.", "refund timing?",
                          evidence, "User gave id B-42.", budget=20)
    assert packed["evidence"] == ["Refunds take 5 business days.",
                                  "Refunds need the original order id."]
    assert packed["dropped"] == ["The office dog attends standups."]
    assert packed["digest"] == "User gave id B-42."
    assert packed["unused_tokens"] == 0

    tight = pack_context("Answer from context.", "refund timing?",
                         evidence, "User gave id B-42.", budget=11)
    assert tight["evidence"] == ["Refunds take 5 business days."]
    assert tight["digest"] == ""

    memory = ConversationMemory(max_verbatim=2)
    memory.pin("order id is B-42")
    for turn in ["User: hi", "Assistant: hello, what's the order id?",
                 "User: B-42, from May 3rd", "Assistant: refund started"]:
        memory.add_turn(turn)
    assert len(memory.recent) == 2
    assert memory.digest.startswith("digest:")
    ctx = memory.context()
    assert ctx.splitlines()[0] == "PINNED: order id is B-42"
    assert "Assistant: refund started" in ctx
    assert "User: hi" not in ctx

    context = ["Refunds are processed within 5 business days."]
    assert check_grounding("Refunds take 5 days.", context)
    assert not check_grounding("Refunds take 3 days.", context)
    assert check_grounding("Refunds are processed quickly.", context)

    print("All solution checks passed ✔")
