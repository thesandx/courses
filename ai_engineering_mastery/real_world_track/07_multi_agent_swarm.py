"""
Real-World Exercise 7: A Multi-Agent Swarm (pairs with Module 6)
================================================================
Run: python3 07_multi_agent_swarm.py

Requires:  pip install openai
           export OPENROUTER_API_KEY="sk-or-..."

Module 6's orchestrator-worker pattern with real models and real parallelism:
  1. an ORCHESTRATOR model decomposes the task into subtasks (JSON plan)
  2. specialist WORKERS run in PARALLEL, each with its own system prompt and
     only its scoped briefing (information isolation)
  3. a SYNTHESIZER merges the reports — and is told to surface disagreement
     instead of averaging it away

Watch the cost line at the end: a swarm multiplies calls. Module 6's rule
stands — you earn this architecture with parallel structure, not with hype.
"""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

try:
    from openai import OpenAI
except ImportError:
    sys.exit("The 'openai' package is missing. Run:  pip install openai")

API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY:
    sys.exit("OPENROUTER_API_KEY is not set (see README.md).")

MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

TOTAL_TOKENS = {"count": 0}


def call(system: str, user: str, json_mode: bool = False) -> str:
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    response = client.chat.completions.create(
        model=MODEL, max_tokens=500, **kwargs,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}])
    TOTAL_TOKENS["count"] += response.usage.total_tokens
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# The specialists available to the swarm — each is a system prompt, i.e. a
# persona plus rules. Isolation means each sees ONLY its briefing.
# ---------------------------------------------------------------------------
SPECIALISTS = {
    "billing": "You are a billing specialist. Investigate ONLY the billing "
               "angle of the briefing. Report findings in 2-3 sentences and "
               "end with exactly one line 'BLAMES: billing' or 'BLAMES: none'.",
    "infra": "You are an infrastructure specialist. Investigate ONLY the "
             "infrastructure angle of the briefing. Report findings in 2-3 "
             "sentences and end with exactly one line 'BLAMES: infra' or "
             "'BLAMES: none'.",
    "comms": "You are a customer-communications specialist. Draft what we "
             "should tell the customer, in 2-3 sentences. End with "
             "'BLAMES: none'.",
}

TASK = ("Customer reports: checkout has been failing since yesterday's "
        "gateway maintenance window. Their card was charged once but the "
        "order never appeared. They are angry and considering churn.")

# ---------------------------------------------------------------------------
# 1. Orchestrator: decompose into scoped subtasks (a real planning call)
# ---------------------------------------------------------------------------
print("=" * 70)
print(f"Multi-agent swarm  (model: {MODEL})")
print("=" * 70)

plan_raw = call(
    system=("You are an incident orchestrator. Split the task into subtasks "
            "for the available specialists: " + ", ".join(SPECIALISTS) + ". "
            "Each briefing must contain ONLY what that specialist needs — no "
            "customer identity details for infra. Respond with JSON: "
            '{"subtasks": [{"specialist": "<name>", "briefing": "<text>"}]}'),
    user=TASK,
    json_mode=True,
)
plan = json.loads(plan_raw)["subtasks"]
plan = [s for s in plan if s["specialist"] in SPECIALISTS]
print(f"\nplan: {len(plan)} subtasks")
for sub in plan:
    print(f"  -> {sub['specialist']}: {sub['briefing'][:70]}...")

# ---------------------------------------------------------------------------
# 2. Workers: run the swarm IN PARALLEL (threads; each is one API call)
# ---------------------------------------------------------------------------


def run_worker(subtask):
    report = call(system=SPECIALISTS[subtask["specialist"]],
                  user=subtask["briefing"])
    blames = "none"
    for line in report.splitlines():
        if line.strip().upper().startswith("BLAMES:"):
            blames = line.split(":", 1)[1].strip().lower()
    return {"specialist": subtask["specialist"], "report": report,
            "blames": blames}


with ThreadPoolExecutor(max_workers=len(plan)) as pool:
    reports = list(pool.map(run_worker, plan))

print("\nworker reports (ran in parallel):")
for r in reports:
    first_line = r["report"].splitlines()[0][:80]
    print(f"  [{r['specialist']}] {first_line}...  (blames: {r['blames']})")

# ---------------------------------------------------------------------------
# 3. Synthesis: merge — and DETECT disagreement instead of averaging it
# ---------------------------------------------------------------------------
distinct_blames = {r["blames"] for r in reports if r["blames"] not in ("none", "")}
if len(distinct_blames) > 1:
    print(f"\nCONFLICT: specialists disagree ({distinct_blames}) — escalating, "
          f"not averaging (Module 6's rule).")
else:
    synthesis = call(
        system=("You are the incident commander. Merge the specialist reports "
                "into one 3-sentence summary: root cause, customer impact, and "
                "the message to send the customer. If reports contradict each "
                "other, say so explicitly instead of smoothing it over."),
        user="\n\n".join(f"[{r['specialist']}]\n{r['report']}" for r in reports),
    )
    print(f"\nsynthesis:\n{synthesis}")

# ---------------------------------------------------------------------------
# 4. The bill — agency is never free
# ---------------------------------------------------------------------------
calls_made = 1 + len(plan) + (0 if len(distinct_blames) > 1 else 1)
print(f"\ncost: {calls_made} model calls, {TOTAL_TOKENS['count']} tokens total")
print("(a single-agent answer would have been 1 call — the swarm must earn "
      "its multiplier with parallel speed or specialist quality)")

print("\nExercise 7 complete ✔")

# ---------------------------------------------------------------------------
# YOUR TURN
# ---------------------------------------------------------------------------
# 1. Time the parallel worker phase, then rerun with max_workers=1 and compare
#    wall-clock — parallelism is the honest argument FOR a swarm.
# 2. Give each specialist a different OPENROUTER model (cheap for comms,
#    strong for infra) — that's Module 8's tiered routing meeting Module 6.
# 3. Redact PII in the orchestrator's briefings programmatically (Module 6's
#    redact()) instead of trusting the prompt to do it, and assert on it.
# 4. Answer honestly: for THIS task, did the swarm beat one good agent?
#    Run both, compare quality and cost, and write the two-line verdict.
