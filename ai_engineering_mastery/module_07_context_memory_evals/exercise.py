"""
Module 7 Exercise: Budgeter, Memory, and the Grounding Check
============================================================
Goal
----
Implement the context budgeter, the rolling conversation memory with pinned
facts, and the grounding check that catches fabricated numbers.

Complete the TODOs below, then run:  python3 exercise.py
All assertions at the bottom must pass. Try it before opening solution.py!
"""


# ---------------------------------------------------------------------------
# Provided: word-count budgeting (simpler than subword, same discipline)
# ---------------------------------------------------------------------------
def count_tokens(text: str) -> int:
    return len(text.split())


def summarize(turns: list[str]) -> str:
    """Toy summarizer: keeps capitalized/numeric words. Lossy on purpose."""
    keep = [w for t in turns for w in t.split()
            if w[:1].isupper() or any(ch.isdigit() for ch in w)]
    return "digest: " + " ".join(keep[:12])


# ---------------------------------------------------------------------------
# TODO 1 — pack_context(system, question, evidence, digest, budget)
# ---------------------------------------------------------------------------
# evidence: list of (score, chunk) tuples.
# Priorities: system + question always included (assert they fit); then
# evidence chunks best-score-first while they fit; then the digest if it
# still fits. Return a dict with keys:
#   "evidence" (kept chunks in packed order), "dropped" (chunks that didn't
#   fit, any order), "digest" (the digest string or ""), and
#   "unused_tokens" (int).


# ---------------------------------------------------------------------------
# TODO 2 — class ConversationMemory(max_verbatim)
# ---------------------------------------------------------------------------
# * add_turn(turn): append to self.recent; when len(recent) > max_verbatim,
#   move the overflow (oldest turns) out, keep the newest max_verbatim, and
#   set self.digest = summarize([old_digest_if_any] + overflow)
# * pin(fact): facts that must never be lost to summarization
# * context() -> str: "PINNED: f1; f2" line (if any), then the digest (if
#   any), then recent turns, joined with newlines


# ---------------------------------------------------------------------------
# TODO 3 — check_grounding(answer, context)
# ---------------------------------------------------------------------------
# Return False if the answer contains a NUMBER (word.isdigit() after
# stripping ".,") that appears nowhere in the joined context; True otherwise.
# This one check catches the classic RAG hallucination: right shape,
# fabricated figure.


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    evidence = [
        (0.9, "Refunds take 5 business days."),          # 5 tokens
        (0.5, "Refunds need the original order id."),    # 6 tokens
        (0.1, "The office dog attends standups."),       # 5 tokens
    ]
    packed = pack_context("Answer from context.", "refund timing?",
                          evidence, "User gave id B-42.", budget=20)
    # 3 + 2 required; 15 left: 5 + 6 fit (4 left), dog chunk (5) doesn't; digest (4) fits.
    assert packed["evidence"] == ["Refunds take 5 business days.",
                                  "Refunds need the original order id."]
    assert packed["dropped"] == ["The office dog attends standups."]
    assert packed["digest"] == "User gave id B-42."
    assert packed["unused_tokens"] == 0

    tight = pack_context("Answer from context.", "refund timing?",
                         evidence, "User gave id B-42.", budget=11)
    assert tight["evidence"] == ["Refunds take 5 business days."]
    assert tight["digest"] == "", "no room left for the digest"

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
    assert "User: hi" not in ctx, "oldest turn only survives inside the digest"

    context = ["Refunds are processed within 5 business days."]
    assert check_grounding("Refunds take 5 days.", context)
    assert not check_grounding("Refunds take 3 days.", context), \
        "the fabricated 3 must fail grounding"
    assert check_grounding("Refunds are processed quickly.", context), \
        "no numbers claimed -> nothing to fail"

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Extend check_grounding to proper nouns: capitalized words in the answer
#    must appear in the context too (watch the false-positive rate!).
# 2. Give pack_context a reserve_for_output parameter — generation needs
#    room in the window as well.
# 3. Add a rubric judge scored 0-2 against a reference and compute a full
#    suite score like concepts.py — then break the pipeline and watch it drop.
