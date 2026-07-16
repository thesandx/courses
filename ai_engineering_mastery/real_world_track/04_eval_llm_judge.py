"""
Real-World Exercise 4: LLM-as-Judge Evals (pairs with Modules 7-8)
==================================================================
Run: python3 04_eval_llm_judge.py

Requires:  pip install openai
           export OPENROUTER_API_KEY="sk-or-..."

Module 7's three-layer eval harness with a real judge:
  layer 1: deterministic checks (free)
  layer 2: grounding check (free)
  layer 3: rubric-based LLM judge (one real call per case)
The suite prints the honest table — including a case designed to fail.
"""

import json
import os
import sys

try:
    from openai import OpenAI
except ImportError:
    sys.exit("The 'openai' package is missing. Run:  pip install openai")

API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY:
    sys.exit("OPENROUTER_API_KEY is not set (see README.md).")

MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

# ---------------------------------------------------------------------------
# The system under test: answers to grade. In a real project these come from
# your pipeline (exercise 2); here one is deliberately hallucinated so you can
# see every layer earn its keep.
# ---------------------------------------------------------------------------
CASES = [
    {"question": "how long do refunds take?",
     "context": ["Refunds are processed within 5 business days."],
     "answer": "Refunds are processed within 5 business days.",
     "reference": "Refunds take 5 business days."},
    {"question": "when do reset links expire?",
     "context": ["Password reset links expire after one hour."],
     "answer": "Reset links expire after one hour.",
     "reference": "Reset links expire after 1 hour."},
    {"question": "how long do refunds take?",                    # the plant
     "context": ["Refunds are processed within 5 business days."],
     "answer": "Refunds are processed within 3 days.",           # fabricated!
     "reference": "Refunds take 5 business days."},
]

# ---------------------------------------------------------------------------
# Layers 1 + 2: deterministic and grounding (from Module 7, unchanged)
# ---------------------------------------------------------------------------


def check_format(answer: str) -> bool:
    return answer.endswith(".") and 3 <= len(answer.split()) <= 40


def check_grounding(answer: str, context: list[str]) -> bool:
    ctx = " ".join(context).lower()
    for word in answer.lower().split():
        word = word.strip(".,")
        if word.isdigit() and word not in ctx:
            return False
    return True


# ---------------------------------------------------------------------------
# Layer 3: the real judge — rubric in the prompt, JSON verdict out
# ---------------------------------------------------------------------------
JUDGE_SYSTEM = (
    "You are an evaluation judge. Grade a candidate answer against a "
    "reference answer using this rubric:\n"
    "  2 = factually equivalent to the reference\n"
    "  1 = partially correct (right topic, wrong or missing detail)\n"
    "  0 = wrong or contradicts the reference\n"
    "Judge FACTS, not wording. Respond with JSON only: "
    '{"score": <0|1|2>, "reason": "<one sentence>"}'
)


def judge(question: str, answer: str, reference: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=200,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content":
                f"QUESTION: {question}\nREFERENCE: {reference}\n"
                f"CANDIDATE: {answer}"},
        ],
    )
    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# The suite: run everything, print the whole table (wins AND losses)
# ---------------------------------------------------------------------------
print("=" * 70)
print(f"Eval suite with a real LLM judge  (judge model: {MODEL})")
print("=" * 70)

rows = []
for case in CASES:
    verdict = judge(case["question"], case["answer"], case["reference"])
    rows.append({
        "answer": case["answer"][:44],
        "format": check_format(case["answer"]),
        "grounded": check_grounding(case["answer"], case["context"]),
        "judge": verdict["score"],
        "reason": verdict["reason"],
    })

print(f"\n{'answer':<46} {'fmt':<5} {'grnd':<6} judge")
for row in rows:
    print(f"{row['answer']:<46} {str(row['format']):<5} "
          f"{str(row['grounded']):<6} {row['judge']}/2  ({row['reason'][:50]})")

suite_score = sum(r["judge"] for r in rows) / (2 * len(rows))
grounded_rate = sum(r["grounded"] for r in rows) / len(rows)
print(f"\nsuite: judge_score={suite_score:.2f}  grounded_rate={grounded_rate:.2f}")

# The planted hallucination must be caught by grounding, the judge, or both:
plant = rows[2]
assert not plant["grounded"] or plant["judge"] < 2, \
    "the fabricated '3 days' sailed through every layer — tighten the rubric!"
print("planted hallucination was caught ✔")

print("\nExercise 4 complete ✔")

# ---------------------------------------------------------------------------
# YOUR TURN
# ---------------------------------------------------------------------------
# 1. Calibrate the judge (Module 7 rule 2): hand-label 5 answers yourself,
#    run the judge, and count disagreements before you trust it in CI.
# 2. Point the suite at exercise 2's ask() so it grades LIVE pipeline output.
# 3. Run the identical suite with two different OPENROUTER_MODELs as the judge
#    and compare verdicts — judge choice is itself a measurable decision.
