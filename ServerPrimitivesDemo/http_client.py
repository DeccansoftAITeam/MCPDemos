"""
Deccansoft Institute — MCP HTTP Client
Connects to the institute MCP server over Streamable HTTP transport.

Requires the server to be running first:
    python main.py http
"""

import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = "http://127.0.0.1:8000/mcp"
SEP        = "─" * 60
DSEP       = "═" * 60


def header(title: str):
    print(f"\n{DSEP}")
    print(f"  {title}")
    print(DSEP)


def section(title: str):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


# ─────────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────────

async def handle_tools(session: ClientSession):
    resp = await session.list_tools()

    section("Available Tools")
    for i, tool in enumerate(resp.tools, 1):
        print(f"  {i}. {tool.name}")
        print(f"     {tool.description}")

    try:
        choice = int(input("\nSelect tool number (0 to go back): "))
        if choice == 0:
            return
        tool = resp.tools[choice - 1]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return

    print(f"\n  Tool  : {tool.name}")
    print(f"  Desc  : {tool.description}")

    args       = {}
    schema     = tool.inputSchema or {}
    properties = schema.get("properties", {})
    required   = schema.get("required", [])

    if properties:
        print("\n  Enter arguments:")
        for param, meta in properties.items():
            hint = "(required)" if param in required else "(optional — Enter to skip)"
            val  = input(f"    {param} {hint}: ").strip()
            if val:
                args[param] = int(val) if meta.get("type") == "integer" else val

    result = await session.call_tool(tool.name, arguments=args)
    section("Tool Result")
    for c in result.content:
        try:
            print(json.dumps(json.loads(c.text), indent=2))
        except Exception:
            print(c.text)


# ─────────────────────────────────────────────────────────────
# RESOURCES & RESOURCE TEMPLATES
# ─────────────────────────────────────────────────────────────

async def handle_resources(session: ClientSession):
    resources = await session.list_resources()
    templates = await session.list_resource_templates()

    items = []  # list of (uri_or_template, is_template)

    if resources.resources:
        section("Static Resources")
        for i, r in enumerate(resources.resources, 1):
            print(f"  {i}. {r.uri}")
            print(f"     {r.description or r.name}")
            items.append((str(r.uri), False))

    if templates.resourceTemplates:
        offset = len(items)
        section("Resource Templates  (parameterised)")
        for i, t in enumerate(templates.resourceTemplates, offset + 1):
            print(f"  {i}. {t.uriTemplate}")
            print(f"     {t.description or t.name}")
            items.append((t.uriTemplate, True))

    if not items:
        print("  No resources available.")
        return

    try:
        choice = int(input("\nSelect number (0 to go back): "))
        if choice == 0:
            return
        uri, is_template = items[choice - 1]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return

    if is_template:
        print(f"\n  Template : {uri}")
        uri = input("  Enter full URI (replace {param} with actual value): ").strip()

    print(f"\n  Fetching : {uri}")
    result = await session.read_resource(uri)

    section("Resource Content")
    for c in result.contents:
        try:
            print(json.dumps(json.loads(c.text), indent=2))
        except Exception:
            print(c.text)


# ─────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────

async def handle_prompts(session: ClientSession):
    resp = await session.list_prompts()

    section("Available Prompts")
    for i, p in enumerate(resp.prompts, 1):
        print(f"  {i}. {p.name}")
        print(f"     {p.description}")

    try:
        choice = int(input("\nSelect prompt number (0 to go back): "))
        if choice == 0:
            return
        prompt = resp.prompts[choice - 1]
    except (ValueError, IndexError):
        print("  Invalid choice.")
        return

    print(f"\n  Prompt : {prompt.name}")

    args = {}
    if prompt.arguments:
        print("  Enter arguments:")
        for arg in prompt.arguments:
            hint = "(required)" if arg.required else "(optional — Enter to skip)"
            val  = input(f"    {arg.name} {hint}: ").strip()
            if val:
                args[arg.name] = val

    result = await session.get_prompt(prompt.name, arguments=args)

    section("Rendered Prompt  (ready to send to LLM)")
    for msg in result.messages:
        print(msg.content.text)
    print(SEP)


# ─────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────

async def run():
    print(f"  Connecting to MCP server at {SERVER_URL} ...")

    async with streamable_http_client(SERVER_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("  Connected successfully!\n")

            while True:
                print(f"\n{SEP}")
                print("  MAIN MENU")
                print(SEP)
                print("  1. Tools          — call add_student, enroll, search, etc.")
                print("  2. Resources      — browse courses, faculty, students, batches")
                print("  3. Prompts        — render progress report, announcement, etc.")
                print("  0. Exit")
                print(SEP)

                choice = input("  Choose: ").strip()

                if choice == "1":
                    await handle_tools(session)
                elif choice == "2":
                    await handle_resources(session)
                elif choice == "3":
                    await handle_prompts(session)
                elif choice == "0":
                    print("\n  Goodbye!\n")
                    break
                else:
                    print("  Invalid choice, try again.")

if __name__ == "__main__":
    asyncio.run(run())
