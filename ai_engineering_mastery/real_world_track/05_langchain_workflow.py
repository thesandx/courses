"""
Real-World Exercise 5: LangChain & AI Workflows (pairs with Modules 2-4)
========================================================================
Run: python3 05_langchain_workflow.py

Requires:  pip install openai langchain langchain-openai
           export OPENROUTER_API_KEY="sk-or-..."

You built pipelines by hand in Modules 1-4; LangChain is the framework version
of the same shapes. This exercise builds three real workflows with LCEL
(LangChain Expression Language), all through OpenRouter:
  1. prompt -> model -> parser        (the atomic chain)
  2. classify -> route                (a branching workflow)
  3. retrieve -> generate             (the RAG chain, with YOUR retriever)

The lesson of Modules 1-8 applies here doubly: after building these by hand,
you can now see exactly what the framework does for you — and what it doesn't.
"""

import os
import sys

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnableLambda, RunnablePassthrough
except ImportError:
    sys.exit("LangChain is missing. Run:  pip install langchain langchain-openai")

API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY:
    sys.exit("OPENROUTER_API_KEY is not set (see README.md).")

MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

# The same OpenRouter endpoint, wrapped in LangChain's chat model:
llm = ChatOpenAI(
    model=MODEL,
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1",
    max_tokens=300,
)

# ---------------------------------------------------------------------------
# 1. The atomic chain: prompt -> model -> parser
# ---------------------------------------------------------------------------
print("=" * 70)
print(f"1. prompt | llm | parser  (model: {MODEL})")
print("=" * 70)

summarize = (
    ChatPromptTemplate.from_messages([
        ("system", "Summarize the user's text in exactly one sentence."),
        ("user", "{text}"),
    ])
    | llm
    | StrOutputParser()
)

summary = summarize.invoke({"text": (
    "The customer opened three tickets this week. Two were about the checkout "
    "page timing out during the gateway maintenance window, and one asked "
    "whether refunds triggered by those failures would be processed faster."
)})
print(f"summary: {summary}")

# ---------------------------------------------------------------------------
# 2. A branching workflow: classify, then route to a specialist chain
#    (this is Module 6's orchestrator idea as a fixed workflow, not an agent)
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("2. classify -> route")
print("=" * 70)

classify = (
    ChatPromptTemplate.from_messages([
        ("system", "Classify the ticket as exactly one word: "
                   "'billing' or 'technical'. Reply with only that word."),
        ("user", "{ticket}"),
    ])
    | llm
    | StrOutputParser()
)

billing_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "You are a billing specialist. Answer in one sentence."),
        ("user", "{ticket}"),
    ])
    | llm | StrOutputParser()
)
technical_chain = (
    ChatPromptTemplate.from_messages([
        ("system", "You are an infrastructure specialist. Answer in one sentence."),
        ("user", "{ticket}"),
    ])
    | llm | StrOutputParser()
)


def route(inputs: dict) -> str:
    label = inputs["label"].strip().lower()
    chain = billing_chain if "billing" in label else technical_chain
    return f"[routed to {('billing' if 'billing' in label else 'technical')}] " \
           + chain.invoke({"ticket": inputs["ticket"]})


workflow = (
    {"label": classify, "ticket": RunnablePassthrough()}
    | RunnableLambda(route)
)

for ticket in ["Why was I charged twice this month?",
               "The checkout page times out on every request."]:
    print(f"\nticket: {ticket}")
    print(f"  {workflow.invoke(ticket)}")

# ---------------------------------------------------------------------------
# 3. The RAG chain — LangChain generation on top of YOUR Module 2 retriever
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("3. retrieve -> generate (RAG as a chain)")
print("=" * 70)

KB = [
    "Refunds are processed within 5 business days of the request.",
    "Refund requests require the original order id.",
    "Password reset links expire after one hour.",
]


def retrieve(question: str) -> str:
    """Your retriever goes here. Keyword scoring keeps this file dependency-
    free; swap in the Module 2 vector store or a real vector DB unchanged —
    the chain doesn't care, which is the point of the abstraction."""
    def score(doc):
        q = set(question.lower().split())
        return len(q & set(doc.lower().split()))
    top = sorted(KB, key=score, reverse=True)[:2]
    return "\n".join(f"[doc] {d}" for d in top)


rag_chain = (
    {"context": RunnableLambda(retrieve), "question": RunnablePassthrough()}
    | ChatPromptTemplate.from_messages([
        ("system", "Answer ONLY from the context. If the answer is not "
                   "there, say \"I don't know\"."),
        ("user", "CONTEXT:\n{context}\n\nQUESTION: {question}"),
    ])
    | llm
    | StrOutputParser()
)

for question in ["how long do refunds take?", "who is the CEO?"]:
    print(f"\nQ: {question}")
    print(f"A: {rag_chain.invoke(question)}")

print("\nExercise 5 complete ✔")

# ---------------------------------------------------------------------------
# YOUR TURN
# ---------------------------------------------------------------------------
# 1. Add .with_retry() to the llm and observe LangChain's built-in resilience —
#    then compare with the retry logic you'd write by hand.
# 2. Replace retrieve() with the Module 2 VectorStore, then run the Module 3
#    retrieval evals over it: frameworks don't exempt you from measuring.
# 3. Stream the RAG chain with rag_chain.stream(question) and print chunks —
#    the UX difference for long answers is the reason streaming defaults exist.
# 4. When does a workflow beat an agent? Write down the answer using Module 5's
#    table, then check: this whole file has ZERO model-decided control flow.
