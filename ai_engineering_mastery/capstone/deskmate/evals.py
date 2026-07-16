"""Modules 3 + 7: grounding check, rubric judge, and the suite runner."""


def check_grounding(answer: str, evidence: list[str]) -> bool:
    """Every number the answer claims must appear in the evidence."""
    ctx = " ".join(evidence).lower()
    for word in answer.lower().split():
        word = word.strip(".,")
        if word.isdigit() and word not in ctx:
            return False
    return True


def judge(answer: str, reference: str) -> int:
    """Rubric 0-2 by reference-word overlap. In production this is an LLM
    call carrying the rubric; calibrate it on hand-labeled cases first."""
    ref = set(reference.lower().split())
    ans = set(answer.lower().split())
    overlap = len(ref & ans) / len(ref)
    return 2 if overlap > 0.8 else 1 if overlap > 0.4 else 0


EVAL_CASES = [
    {"question": "how long do refunds take?",
     "reference": "Refunds are processed within 5 business days."},
    {"question": "what do I need to get my money back?",
     "reference": "Refund requests require the original order id."},
    {"question": "when do password reset links expire?",
     "reference": "Password reset links are sent by email and expire after one hour."},
    {"question": "how fast is priority support on the pro plan?",
     "reference": "The pro plan includes priority support with a 4 hour response target."},
]


def run_suite(ask) -> dict:
    """ask(question) -> {"answer": str|None, "evidence": [...], "cost": float}.
    Returns the full honest table: no single-metric cherry-picking."""
    rows = []
    for case in EVAL_CASES:
        out = ask(case["question"])
        answered = out["answer"] is not None
        rows.append({
            "question": case["question"],
            "answered": answered,
            "grounded": check_grounding(out["answer"], out["evidence"])
                        if answered else None,
            "judge": judge(out["answer"], case["reference"]) if answered else 0,
            "cost": out["cost"],
        })
    n = len(rows)
    answered_rows = [r for r in rows if r["answered"]]
    return {
        "rows": rows,
        "answer_rate": len(answered_rows) / n,
        "grounded_rate": (sum(r["grounded"] for r in answered_rows)
                          / len(answered_rows)) if answered_rows else 0.0,
        "judge_score": sum(r["judge"] for r in rows) / (2 * n),
        "total_cost": sum(r["cost"] for r in rows),
    }
