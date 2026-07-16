"""
Real-World Exercise 2: RAG with a Real LLM (pairs with Modules 2-3)
===================================================================
Run: python3 02_rag_with_real_llm.py

Requires:  pip install openai
           export OPENROUTER_API_KEY="sk-or-..."

The retrieval half is YOUR vector store from Module 2 (hash embeddings, exact
top-k). The generation half is now a real model, with two production rules:
  * grounded generation — the model may only use retrieved context
  * machine-readable output — JSON mode, with cited doc ids you can verify
"""

import hashlib
import json
import math
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
# Retrieval: the Module 2 vector store, unchanged
# ---------------------------------------------------------------------------


def tokenize(text):
    tokens = []
    for word in text.lower().split():
        word = word.strip(".,!?;:()\"'")
        if not word:
            continue
        while len(word) > 4:
            tokens.append(word[:4])
            word = word[4:]
        tokens.append(word)
    return tokens


def embed(text, dims=256):
    vec = [0.0] * dims
    for token in tokenize(text):
        h = hashlib.sha256(token.encode()).digest()
        vec[h[0] % dims] += 1.0 if h[1] % 2 == 0 else -1.0
    return vec


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


KB = [
    "Refunds are processed within 5 business days of the request.",
    "Refund requests require the original order id from the receipt.",
    "Password reset links are sent by email and expire after one hour.",
    "The pro plan includes priority support with a 4 hour response target.",
    "Invoices are emailed on the first day of each month.",
]
KB_VECTORS = [embed(d) for d in KB]


def retrieve(question, k=2):
    q = embed(question)
    scored = sorted(range(len(KB)), key=lambda i: -cosine_similarity(q, KB_VECTORS[i]))
    return scored[:k]


# ---------------------------------------------------------------------------
# Generation: real model, grounded, JSON mode with citations
# ---------------------------------------------------------------------------
SYSTEM = (
    "You answer support questions using ONLY the numbered context documents "
    "provided. Respond with a JSON object exactly like: "
    '{"answer": "<one sentence>", "sources": [<doc numbers used>], '
    '"answerable": <true|false>}. '
    "If the context does not contain the answer, set answerable to false, "
    "sources to [], and answer to \"I don't know\"."
)


def ask(question):
    doc_ids = retrieve(question)
    context = "\n".join(f"[doc {i + 1}] {KB[i]}" for i in doc_ids)
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=300,
        response_format={"type": "json_object"},        # JSON mode
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user",
             "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}"},
        ],
    )
    raw = response.choices[0].message.content
    result = json.loads(raw)                            # ALWAYS parse, never regex
    result["retrieved"] = [i + 1 for i in doc_ids]
    result["usage"] = response.usage.total_tokens
    return result


print("=" * 70)
print(f"Grounded RAG with citations  (model: {MODEL})")
print("=" * 70)

for question in [
    "how do I get my money back?",
    "when do password reset links expire?",
    "what is the capital of France?",          # NOT in the KB — must refuse
]:
    result = ask(question)
    print(f"\nQ: {question}")
    print(f"  retrieved docs : {result['retrieved']}")
    print(f"  answer         : {result['answer']}")
    print(f"  cited sources  : {result['sources']}   answerable: {result['answerable']}")
    print(f"  tokens         : {result['usage']}")

    # The verification your production code should do on every response:
    assert isinstance(result["sources"], list)
    for s in result["sources"]:
        assert s in result["retrieved"], \
            f"model cited doc {s} which was never in its context — hallucinated citation!"

print("\nExercise 2 complete ✔  (every citation verified against the retrieval)")

# ---------------------------------------------------------------------------
# YOUR TURN
# ---------------------------------------------------------------------------
# 1. Break retrieval on purpose: retrieve(question, k=1) with an unrelated
#    question and watch answerable flip to false — retrieval caps generation.
# 2. Add the Module 7 grounding check on result["answer"]: any number in the
#    answer must appear in the retrieved docs.
# 3. Port hybrid retrieval (Module 3 RRF) in place of vector-only retrieve()
#    and compare which questions change their retrieved sets.
