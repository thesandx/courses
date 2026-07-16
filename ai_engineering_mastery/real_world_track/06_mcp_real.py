"""
Real-World Exercise 6: MCP for Real (pairs with Module 6)
=========================================================
Run: python3 06_mcp_real.py

Requires:  pip install openai mcp
           export OPENROUTER_API_KEY="sk-or-..."

In Module 6 you built an MCP-*style* protocol in one file. This is the real
Model Context Protocol, using the official `mcp` SDK:

  * the SERVER half: a FastMCP server exposing two tools (this same file,
    launched with --server, speaking JSON-RPC over stdio)
  * the CLIENT half: connects over stdio, DISCOVERS the tools, converts their
    schemas to OpenAI function format, and lets a real LLM call them

That last step is the whole point of MCP: the LLM never knew this server
existed until the client discovered it at runtime — M+N, not M*N.
"""

import asyncio
import json
import os
import sys

# ---------------------------------------------------------------------------
# SERVER half — runs when invoked as:  python3 06_mcp_real.py --server
# ---------------------------------------------------------------------------
if "--server" in sys.argv:
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("support-desk")

    ORDERS = {"A-17": {"item": "keyboard", "eta_days": 3},
              "B-42": {"item": "monitor", "eta_days": 7}}

    @server.tool()
    def track_order(order_id: str) -> str:
        """Track an order by id (format like A-17). Returns item and ETA."""
        order = ORDERS.get(order_id)
        return json.dumps(order if order else {"error": "order not found"})

    @server.tool()
    def refund_policy() -> str:
        """Get the refund policy text."""
        return "Refunds are processed within 5 business days of the request."

    server.run()          # stdio transport — blocks, serving JSON-RPC
    sys.exit(0)

# ---------------------------------------------------------------------------
# CLIENT half — the default entrypoint
# ---------------------------------------------------------------------------
try:
    from openai import OpenAI
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    sys.exit("Missing packages. Run:  pip install openai mcp")

API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY:
    sys.exit("OPENROUTER_API_KEY is not set (see README.md).")

MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
llm = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)


def mcp_tools_to_openai(tools) -> list[dict]:
    """The bridge: MCP tool declarations -> OpenAI function schemas.
    This 8-line function is what 'MCP support' in an agent runtime means."""
    return [{"type": "function",
             "function": {"name": t.name,
                          "description": t.description or "",
                          "parameters": t.inputSchema}}
            for t in tools]


async def main():
    print("=" * 70)
    print(f"Real MCP over stdio  (model: {MODEL})")
    print("=" * 70)

    # Launch this same file as the MCP server, speak JSON-RPC to it:
    params = StdioServerParameters(command=sys.executable,
                                   args=[os.path.abspath(__file__), "--server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. DISCOVERY — the client learns what exists at runtime
            listed = await session.list_tools()
            print("\ndiscovered tools:")
            for tool in listed.tools:
                print(f"  - {tool.name}: {tool.description}")
            assert {t.name for t in listed.tools} == {"track_order",
                                                      "refund_policy"}

            # 2. Direct invocation — prove the protocol round-trips
            result = await session.call_tool("track_order",
                                             {"order_id": "B-42"})
            print(f"\ndirect call track_order(B-42) -> {result.content[0].text}")

            # 3. The real-world wiring: LLM + discovered MCP tools
            openai_tools = mcp_tools_to_openai(listed.tools)
            messages = [
                {"role": "system",
                 "content": "Use the tools to answer. One sentence."},
                {"role": "user",
                 "content": "Where is order B-42, and what's the refund policy?"},
            ]
            print("\nagent loop over MCP tools:")
            for step in range(5):                       # bounded, as always
                response = llm.chat.completions.create(
                    model=MODEL, max_tokens=400,
                    tools=openai_tools, messages=messages)
                choice = response.choices[0]
                if choice.finish_reason != "tool_calls":
                    print(f"  answer: {choice.message.content}")
                    break
                messages.append(choice.message)
                for call in choice.message.tool_calls:
                    args = json.loads(call.function.arguments)
                    print(f"  [{step + 1}] LLM -> MCP: {call.function.name}({args})")
                    mcp_result = await session.call_tool(call.function.name,
                                                         args)
                    messages.append({"role": "tool",
                                     "tool_call_id": call.id,
                                     "content": mcp_result.content[0].text})

    print("\nExercise 6 complete ✔  (the LLM used tools it discovered via MCP)")


asyncio.run(main())

# ---------------------------------------------------------------------------
# YOUR TURN
# ---------------------------------------------------------------------------
# 1. Add a third tool to the server and re-run WITHOUT touching the client
#    code — discovery picks it up. That is the M+N economics, live.
# 2. Connect a second FastMCP server (billing) in the same client and merge
#    both tool catalogs — Module 6's MCPClient.discover(), for real.
# 3. Point the client at a real public MCP server instead of the built-in one,
#    and reflect on Module 6's rule: wrap APIs in MCP when something DISCOVERS
#    them at runtime — which is exactly what your loop just did.
