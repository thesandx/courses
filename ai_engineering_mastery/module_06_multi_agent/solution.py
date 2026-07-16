"""
Module 6 Solution: MCP Server/Client and the Honest Synthesizer
===============================================================
Run: python3 solution.py — passes the same checks as exercise.py.
"""


# TODO 1 — one uniform shape for discovery and invocation.
class MCPServer:
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


# TODO 2 — the client learns every server's tools once: M+N, not M*N.
class MCPClient:
    def __init__(self):
        self._servers: dict[str, MCPServer] = {}

    def connect(self, server: MCPServer):
        self._servers[server.name] = server

    def discover(self) -> dict[str, str]:
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


# TODO 3 — disagreement is a result, not noise to smooth over.
def synthesize(reports: list[dict]) -> dict:
    distinct_causes = {r["blames"] for r in reports if r["blames"] is not None}
    if len(distinct_causes) > 1:
        return {"status": "conflict", "answer": None}
    return {"status": "ok",
            "answer": " ".join(r["finding"] for r in reports)}


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

    print("All solution checks passed ✔")
