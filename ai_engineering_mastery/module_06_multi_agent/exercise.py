"""
Module 6 Exercise: MCP Server/Client and the Honest Synthesizer
===============================================================
Goal
----
Implement the two protocol halves (server: discovery + invocation; client:
multi-server catalog + routing) and a synthesizer that surfaces specialist
disagreement instead of averaging it away.

Complete the TODOs below, then run:  python3 exercise.py
All assertions at the bottom must pass. Try it before opening solution.py!
"""


# ---------------------------------------------------------------------------
# TODO 1 — class MCPServer(name)
# ---------------------------------------------------------------------------
# * add_tool(name, description, input_schema, fn)
#     input_schema: {"arg_name": "type description"} — keys are required args
# * handle(message) -> dict, where message is one of:
#     {"method": "tools/list"}
#        -> {"tools": [{"name", "description", "inputSchema"}, ...]}
#     {"method": "tools/call", "params": {"name": ..., "arguments": {...}}}
#        -> {"content": fn(**arguments)}
#        -> {"error": ...} if the tool is unknown or any schema key is
#           missing from arguments
#     anything else -> {"error": "unknown method ..."}


# ---------------------------------------------------------------------------
# TODO 2 — class MCPClient
# ---------------------------------------------------------------------------
# * connect(server)
# * discover() -> {tool_name: server_name} across ALL connected servers
# * call(tool_name, arguments) -> the owning server's tools/call response,
#     or {"error": ...} if no connected server offers the tool


# ---------------------------------------------------------------------------
# TODO 3 — synthesize(reports)
# ---------------------------------------------------------------------------
# Each report: {"specialist": str, "finding": str, "blames": str | None}.
# * If two or more DISTINCT non-None `blames` values exist ->
#     {"status": "conflict", "answer": None}
# * Otherwise -> {"status": "ok", "answer": all findings joined with " "}


# ---------------------------------------------------------------------------
# Self-Verification — do not modify below this line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    weather = MCPServer("weather-server")
    weather.add_tool("forecast", "Get the forecast for a city.",
                     {"city": "string"},
                     lambda city: {"city": city, "temp_c": 21})
    orders = MCPServer("orders-server")
    orders.add_tool("track", "Track an order.",
                    {"order_id": "string"},
                    lambda order_id: {"order_id": order_id, "eta_days": 2})

    listed = weather.handle({"method": "tools/list"})
    assert listed["tools"][0]["name"] == "forecast"
    assert "inputSchema" in listed["tools"][0]

    ok = weather.handle({"method": "tools/call",
                         "params": {"name": "forecast",
                                    "arguments": {"city": "Pune"}}})
    assert ok == {"content": {"city": "Pune", "temp_c": 21}}
    assert "error" in weather.handle({"method": "tools/call",
                                      "params": {"name": "nope",
                                                 "arguments": {}}})
    assert "error" in weather.handle({"method": "tools/call",
                                      "params": {"name": "forecast",
                                                 "arguments": {}}})
    assert "error" in weather.handle({"method": "resources/list"})

    client = MCPClient()
    client.connect(weather)
    client.connect(orders)
    assert client.discover() == {"forecast": "weather-server",
                                 "track": "orders-server"}
    assert client.call("track", {"order_id": "A-17"})["content"]["eta_days"] == 2
    assert "error" in client.call("teleport", {})

    agree = synthesize([
        {"specialist": "infra", "finding": "node draining", "blames": "infra"},
        {"specialist": "billing", "finding": "no failed charges", "blames": None},
    ])
    assert agree["status"] == "ok"
    assert "node draining" in agree["answer"] and "no failed charges" in agree["answer"]

    disagree = synthesize([
        {"specialist": "infra", "finding": "node draining", "blames": "infra"},
        {"specialist": "billing", "finding": "processor outage", "blames": "billing"},
    ])
    assert disagree["status"] == "conflict" and disagree["answer"] is None

    print("All exercise checks passed ✔")

# ---------------------------------------------------------------------------
# Stretch Goals
# ---------------------------------------------------------------------------
# 1. Cache discover() in the client and invalidate on connect() — rediscovery
#    per call is an N-server tax.
# 2. Add redact(text) with regexes for emails and card fragments; assert a
#    briefing passed through it carries no PII (Module 6 concepts.py shows how).
# 3. Two servers exposing the SAME tool name: make discover() report the
#    collision instead of silently keeping the last one.
