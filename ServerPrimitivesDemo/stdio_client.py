"""
MCP Console Client
Connects to the institute MCP server (main.py) via stdio transport.
Demonstrates Tools, Resources, Resource Templates, and Prompts.
"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SEP = "─" * 60
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

    # Collect arguments dynamically from JSON schema
    args = {}
    schema = tool.input_schema or {}
    properties = schema.get("properties", {})
    required    = schema.get("required", [])

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
    resources  = await session.list_resources()
    templates  = await session.list_resource_templates()

    items = []   # list of (label, uri_or_template, is_template)

    if resources.resources:
        section("Static Resources")
        for i, r in enumerate(resources.resources, 1):
            label = r.description or str(r.uri)
            print(f"  {i}. {r.uri}")
            print(f"     {label}")
            items.append((str(r.uri), False))

    if templates.resource_templates:
        offset = len(items)
        section("Resource Templates  (parameterised)")
        for i, t in enumerate(templates.resource_templates, offset + 1):
            label = t.description or t.name
            print(f"  {i}. {t.uri_template}")
            print(f"     {label}")
            items.append((t.uri_template, True))

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
    server_params = StdioServerParameters(
        command="python",
        args=["main.py"],
    )

    print("  Connecting to MCP server (main.py) via stdio...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("  Connected successfully!\n")

            while True:
                print(f"\n{SEP}")
                print("  MAIN MENU")
                print(f"{SEP}")
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
