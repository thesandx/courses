"""
Module 6: Multi-Agent Systems & MCP — Concepts in Action
========================================================
Run: python3 concepts.py

An orchestrator-worker system with information isolation (including tested
PII redaction), conflict-detecting synthesis, and an MCP-style protocol pair
that turns Module 5's registry into one server among many.
"""

import json
import re

# ============================================================================
# 1. Orchestrator-worker with information isolation
# ============================================================================
print("=" * 70)
print("1. Orchestrator-worker")
print("=" * 70)

TASK = ("Customer Ada (card ending 4242, email ada@example.com) reports the "
        "checkout page erroring since the gateway maintenance window.")

# --- Workers: specialists with their own instructions and SCOPED context ---


def billing_worker(briefing: str) -> dict:
    """Specialist: billing. In production this is an agent with billing tools;
    scripted here. It only knows what its briefing says."""
    knows_customer = "Ada" in briefing
    return {"specialist": "billing",
            "finding": "No failed charges recorded for this customer today."
                       if knows_customer else
                       "No customer identified in briefing.",
            "blames": None,                 # billing is NOT the cause
            "context_seen": briefing}


def infra_worker(briefing: str) -> dict:
    """Specialist: infrastructure. Must NEVER receive customer PII."""
    saw_maintenance = "maintenance" in briefing
    return {"specialist": "infra",
            "finding": "Gateway maintenance left one node draining; checkout "
                       "errors match its error budget." if saw_maintenance else
                       "No infra signal in briefing.",
            "blames": "infra" if saw_maintenance else None,
            "context_seen": briefing}


# --- Orchestrator: plan -> route scoped context -> collect ---

PII_PATTERNS = [re.compile(r"card ending \d{4}"),
                re.compile(r"[\w.]+@[\w.]+")]


def redact(text: str) -> str:
    for pattern in PII_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def orchestrate(task: str) -> dict:
    """The three orchestrator jobs. Each 'plan' entry is a subtask with an
    assigned specialist and a scoped briefing — never the raw task."""
    plan = [
        {"specialist": billing_worker,
         "briefing": f"Check for failed charges. Customer: Ada. "
                     f"Symptom: checkout page erroring."},
        {"specialist": infra_worker,
         # Isolation as a security boundary: the infra worker gets the
         # symptom and timeline, with PII stripped.
         "briefing": redact(f"Investigate checkout errors that began around "
                            f"the gateway maintenance window. Original "
                            f"report: {task}")},
    ]
    reports = [step["specialist"](step["briefing"]) for step in plan]
    return {"plan_size": len(plan), "reports": reports}


result = orchestrate(TASK)
for report in result["reports"]:
    print(f"  [{report['specialist']}] {report['finding']}")

infra_report = next(r for r in result["reports"] if r["specialist"] == "infra")
assert "4242" not in infra_report["context_seen"], "card PII leaked to infra!"
assert "ada@example.com" not in infra_report["context_seen"], "email leaked!"
assert "maintenance" in infra_report["context_seen"], \
    "redaction must not destroy the signal the worker needs"
print("  isolation verified: infra worker never saw card or email ✔")

# ============================================================================
# 2. Synthesis: merging reports, detecting contradictions
# ============================================================================
print()
print("=" * 70)
print("2. Conflict-detecting synthesis")
print("=" * 70)


def synthesize(reports: list[dict]) -> dict:
    """Merge worker findings. The cheap-and-wrong version picks reports[0].
    The honest version compares the workers' explicit verdicts (`blames`)
    and DETECTS disagreement instead of averaging it away."""
    blames = {r["specialist"]: r["blames"] for r in reports}
    distinct_causes = {b for b in blames.values() if b is not None}
    if len(distinct_causes) > 1:
        return {"status": "conflict", "blames": blames, "answer": None,
                "note": "specialists disagree; escalate, don't average"}
    summary = " ".join(r["finding"] for r in reports)
    return {"status": "ok", "blames": blames, "answer": summary}


merged = synthesize(result["reports"])
print(f"  status: {merged['status']}   blames: {merged['blames']}")
print(f"  answer: {merged['answer']}")
assert merged["status"] == "ok"
assert "maintenance" in merged["answer"] and "No failed charges" in merged["answer"]

# Now force a contradiction: two specialists blaming different subsystems.
conflict = synthesize([
    {"specialist": "infra", "blames": "infra",
     "finding": "maintenance node draining"},
    {"specialist": "billing-2", "blames": "billing",
     "finding": "processor outage caused the failures"},
])
print(f"  forced disagreement -> status: {conflict['status']} ({conflict['note']})")
assert conflict["status"] == "conflict" and conflict["answer"] is None, \
    "conflicting specialist verdicts must surface, not vanish into a summary"

# ============================================================================
# 3. MCP-style protocol: discovery + invocation in one uniform shape
# ============================================================================
print()
print("=" * 70)
print("3. An MCP-style client/server pair")
print("=" * 70)


class MCPServer:
    """One tool provider speaking the protocol shape: tools/list for
    discovery, tools/call for invocation. Message in, message out — in
    production these are JSON-RPC over stdio or HTTP."""

    def __init__(self, name: str):
        self.name = name
        self._tools: dict[str, dict] = {}

    def add_tool(self, name: str, description: str, input_schema: dict, fn):
        self._tools[name] = {"description": description,
                             "inputSchema": input_schema, "fn": fn}

    def handle(self, message: dict) -> dict:
        method = message.get("method")
        if method == "tools/list":
            return {"tools": [{"name": n,
                               "description": t["description"],
                               "inputSchema": t["inputSchema"]}
                              for n, t in self._tools.items()]}
        if method == "tools/call":
            params = message.get("params", {})
            name = params.get("name")
            if name not in self._tools:
                return {"error": f"unknown tool {name!r}"}
            tool = self._tools[name]
            args = params.get("arguments", {})
            missing = [k for k in tool["inputSchema"] if k not in args]
            if missing:
                return {"error": f"missing arguments {missing}"}
            return {"content": tool["fn"](**args)}
        return {"error": f"unknown method {method!r}"}


class MCPClient:
    """The agent-runtime side: connects to MANY servers, discovers all their
    tools once, and calls any tool through the same shape. M+N, not M*N."""

    def __init__(self):
        self._servers: dict[str, MCPServer] = {}

    def connect(self, server: MCPServer):
        self._servers[server.name] = server

    def discover(self) -> dict[str, str]:
        """tool name -> owning server, for every connected server."""
        catalog = {}
        for server in self._servers.values():
            for tool in server.handle({"method": "tools/list"})["tools"]:
                catalog[tool["name"]] = server.name
        return catalog

    def call(self, tool_name: str, arguments: dict) -> dict:
        catalog = self.discover()
        if tool_name not in catalog:
            return {"error": f"no connected server offers {tool_name!r}"}
        server = self._servers[catalog[tool_name]]
        return server.handle({"method": "tools/call",
                              "params": {"name": tool_name,
                                         "arguments": arguments}})


# Two independent servers — a billing system and an infra system:
billing_srv = MCPServer("billing-server")
billing_srv.add_tool("failed_charges", "Count failed charges for a customer.",
                     {"customer": "string"},
                     lambda customer: {"customer": customer, "failed": 0})

infra_srv = MCPServer("infra-server")
infra_srv.add_tool("node_status", "Status of a gateway node.",
                   {"node": "string"},
                   lambda node: {"node": node, "state": "draining"})

client = MCPClient()
client.connect(billing_srv)
client.connect(infra_srv)

catalog = client.discover()
print(f"  discovered: {catalog}")
assert catalog == {"failed_charges": "billing-server",
                   "node_status": "infra-server"}

resp = client.call("node_status", {"node": "gw-3"})
print(f"  call node_status(gw-3) -> {resp}")
assert resp["content"]["state"] == "draining"

resp = client.call("failed_charges", {"customer": "Ada"})
assert resp["content"]["failed"] == 0

# The protocol also standardizes FAILURE:
assert "error" in client.call("teleport", {})
assert "error" in billing_srv.handle({"method": "tools/call",
                                      "params": {"name": "failed_charges",
                                                 "arguments": {}}})
print("  one client shape, two unrelated backends, uniform errors ✔")

# ...and the anti-pattern check: a fixed pipeline that always calls the same
# one internal function gains nothing from the protocol — it's not discovered,
# not shared, just wrapped. Count the layers you actually need.

print("\nAll Module 6 concept checks passed ✔")
