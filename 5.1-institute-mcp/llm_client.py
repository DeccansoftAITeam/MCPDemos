"""
Deccansoft Institute — LLM Tool Call Loop Client
Implements the exact flow from the diagram:

  list_tools → convert_to_llm_tool → call_llm → tool_calls?
                                          ↑           │ yes
                                          └── feed ←─ session.call_tool
                                                no → final answer

Uses: OpenAI Responses API  (POST /v1/responses)
      State chained via previous_response_id — no manual message history needed.

Requires:
    pip install openai python-dotenv
  OPENAI_API_KEY environment variable set
"""

import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SEP  = "─" * 60

def section(title: str):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

# ─────────────────────────────────────────────────────────────
# Step 2 — convert MCP tool → OpenAI Responses API tool schema
#
# Responses API uses a FLAT schema (no "function" nesting):
#   { "type": "function", "name": ..., "description": ..., "parameters": ... }
#
# Chat Completions uses nested:
#   { "type": "function", "function": { "name": ..., ... } }
# ─────────────────────────────────────────────────────────────

def convert_to_llm_tool(mcp_tool) -> dict:
    return {
        "type":        "function",
        "name":        mcp_tool.name,
        "description": mcp_tool.description,
        "parameters":  mcp_tool.inputSchema or {"type": "object", "properties": {}},
    }

# ─────────────────────────────────────────────────────────────
# THE LOOP
# ─────────────────────────────────────────────────────────────

async def tool_call_loop(session: ClientSession, user_query: str):
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("\n  ERROR: OPENAI_API_KEY environment variable not set.")
        return

    llm = OpenAI(api_key=api_key, api_base="https://api.openai.com/v1")

    # ── Step 1: session.list_tools() ─────────────────────────
    section("Step 1 · session.list_tools()")
    resp = await session.list_tools()
    print(f"  Discovered {len(resp.tools)} tools:")
    for t in resp.tools:
        print(f"    • {t.name}")

    # ── Step 2: convert_to_llm_tool() for each ───────────────
    section("Step 2 · convert_to_llm_tool()  for each")
    llm_tools = [convert_to_llm_tool(t) for t in resp.tools]
    print(f"  Converted {len(llm_tools)} tools to Responses API format.")
    ex = llm_tools[3]
    print(f"  Example — {ex['name']}:")
    print(f"    description : {ex['description']}")
    print(f"    parameters  : {list(ex['parameters'].get('properties', {}).keys())}")

    iteration        = 0
    tool_calls_count = 0
    prev_response_id = None   # chains responses — replaces manual message history

    # First input is the user query string.
    # Subsequent inputs are tool result objects.
    current_input = user_query

    while True:
        iteration += 1

        # ── Step 3: call_llm(prompt, functions) ──────────────
        section(f"Step 3 · responses.create()  [iteration {iteration}]")

        kwargs = dict(
            model="gpt-4.1-mini",
            input=current_input,
            tools=llm_tools,
        )
        if prev_response_id:
            kwargs["previous_response_id"] = prev_response_id
            print(f"  previous_response_id : {prev_response_id}")

        print(f"  Sending to GPT via Responses API...")
        response = llm.responses.create(**kwargs)
        prev_response_id = response.id
        print(f"  response.id          : {response.id}")

        # ── Collect function_call items from output ───────────
        fn_calls = [item for item in response.output if item.type == "function_call"]

        # ── Decision: model returns tool_calls? ──────────────
        if fn_calls:
            tool_calls_count += 1
            section(f"Decision · tool_calls? → YES  (call #{tool_calls_count})")

            tool_outputs = []

            for item in fn_calls:
                args = json.loads(item.arguments)
                print(f"  Tool     : {item.name}")
                print(f"  Args     : {json.dumps(args)}")
                print(f"  call_id  : {item.call_id}")

                # ── session.call_tool(name, args) ─────────────
                print(f"\n  → session.call_tool('{item.name}', {args})")
                mcp_result = await session.call_tool(item.name, arguments=args)
                raw = mcp_result.content[0].text if mcp_result.content else ""

                print(f"  ← Result:")
                try:
                    print(json.dumps(json.loads(raw), indent=6))
                except Exception:
                    print(f"    {raw}")

                tool_outputs.append({
                    "type":    "function_call_output",
                    "call_id": item.call_id,
                    "output":  raw,
                })

            # ── Feed result back via next input ───────────────
            # No message array needed — previous_response_id carries context
            section("Feed result back to model  →  looping to Step 3")
            current_input    = tool_outputs
            print(f"  Passing {len(tool_outputs)} tool output(s) as next input.")
            print(f"  State chained via previous_response_id — no message array needed.")
            print(f"  Looping...")
        else:
            # ── Final answer ──────────────────────────────────
            section("Decision · tool_calls? → NO  →  Final Answer")
            print(f"\n  {response.output_text}")

            print(f"\n  {SEP}")
            print(f"  Loop iterations  : {iteration}")
            print(f"  Tool calls made  : {tool_calls_count}")
            print(f"  Final response id: {response.id}")
            print(f"  {SEP}")
            break

# ─────────────────────────────────────────────────────────────
# SCENARIOS  — each requires more than one tool call
# ─────────────────────────────────────────────────────────────

SCENARIOS = [
    # 2 calls: search_students → enroll_student
    "Find student Arjun Mehta and enroll him in batch 2.",

    # 2 calls: add_student → enroll_student
    "Register a new student Ravi Kumar, email ravi@gmail.com, phone 9111111111. Then enroll him in batch 3.",

    # 2 calls: get_batch_students + get_students_by_course
    "Show me who is in batch 1 and also list all students in the Python Full Stack course.",
]


async def run():
    server_params = StdioServerParameters(command="python", args=["main.py"])

    print("  Connecting to MCP server (stdio)...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("  Connected!\n")

            section("Choose a scenario  (each needs multiple tool calls)")
            for i, s in enumerate(SCENARIOS, 1):
                print(f"  {i}. {s}")
            print(f"  4. Enter your own query")
            print(SEP)

            choice = input("  Choose (1-4): ").strip()
            if choice in ("1", "2", "3"):
                query = SCENARIOS[int(choice) - 1]
            else:
                query = input("  Your query: ").strip()

            print(f"\n  Query: {query}")
            await tool_call_loop(session, query)

if __name__ == "__main__":
    asyncio.run(run())
