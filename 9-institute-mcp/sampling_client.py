"""
Deccansoft Institute — Module 9 Demo Client
Demonstrates three advanced MCP protocol features:

  1. Sampling    — server requests LLM completion → client runs it
  2. Elicitation — server asks user for structured input → client renders console form
  3. Roots       — client declares filesystem boundaries → server can query them

Requires:
  OPENAI_API_KEY environment variable set
  python sampling_client.py
"""

import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.shared.context import RequestContext
from mcp.types import Root, ListRootsResult
from openai import OpenAI
from pydantic import AnyUrl

SEP  = "─" * 60
DSEP = "═" * 60


def banner(title: str):
    print(f"\n{DSEP}")
    print(f"  {title}")
    print(DSEP)


def section(title: str):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


# ─────────────────────────────────────────────────────────────
# SAMPLING CALLBACK
# Fires when server calls ctx.session.create_message()
# ─────────────────────────────────────────────────────────────

async def sampling_callback(
    context: RequestContext,
    params: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    """Client-side handler: server asked us to run an LLM completion."""

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return types.ErrorData(code=-1, message="OPENAI_API_KEY not set.")

    llm = OpenAI(api_key=api_key)

    user_text = params.messages[0].content.text if params.messages else ""
    sys_prompt = params.systemPrompt or "You are a helpful assistant for a software training institute."
    max_tok    = params.maxTokens or 300

    print(f"\n  [SAMPLING CALLBACK FIRED]")
    print(f"  Server requested LLM completion")
    print(f"  Prompt preview : {user_text[:80]}...")
    print(f"  Max tokens     : {max_tok}")
    print(f"  Calling OpenAI (gpt-4o-mini)...")

    response = llm.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": user_text},
        ],
        max_tokens=max_tok,
    )

    text = response.choices[0].message.content
    print(f"  OpenAI responded ({len(text)} chars) — returning to server.")

    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(type="text", text=text),
        model="gpt-4o-mini",
        stopReason="endTurn",
    )


# ─────────────────────────────────────────────────────────────
# ELICITATION CALLBACK
# Fires when server calls ctx.elicit()
# ─────────────────────────────────────────────────────────────

async def elicitation_callback(
    context: RequestContext,
    params: types.ElicitRequestFormParams,
) -> types.ElicitResult:
    """Client-side handler: server asked us to collect structured input from user."""

    print(f"\n  [ELICITATION CALLBACK FIRED]")
    print(f"\n  {params.message}\n")

    schema = params.requestedSchema
    props  = schema.get("properties", {})
    req    = schema.get("required", [])

    if not props:
        val = input("  Confirm? (y/n): ").strip().lower()
        action = "accept" if val in ("y","yes") else "cancel"
        return types.ElicitResult(action=action)

    print("  Fill in the fields below:")
    content = {}

    for field, info in props.items():
        ftype   = info.get("type", "string")
        desc    = info.get("description", "")
        default = info.get("default", None)
        is_req  = field in req

        hint     = f" — {desc}" if desc else ""
        def_hint = f" [default: {default}]" if default is not None else ""
        req_hint = " (required)" if is_req else " (optional, Enter to skip)"

        if ftype == "boolean":
            val = input(f"  {field}{hint}{def_hint} (y/n): ").strip().lower()
            content[field] = val in ("y", "yes", "true", "1")
        else:
            val = input(f"  {field}{hint}{def_hint}{req_hint}: ").strip()
            if val:
                content[field] = val
            elif default is not None:
                content[field] = default

    print()
    action = input("  Submit (y) or Cancel (n)? ").strip().lower()
    if action not in ("y", "yes"):
        return types.ElicitResult(action="cancel")

    return types.ElicitResult(action="accept", content=content)


# ─────────────────────────────────────────────────────────────
# ROOTS CALLBACK
# Called when server calls ctx.session.list_roots()
# ─────────────────────────────────────────────────────────────

async def list_roots_callback(
    context: RequestContext,
) -> ListRootsResult:
    """Declares this client's filesystem roots to the server."""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"\n  [ROOTS CALLBACK FIRED]")
    print(f"  Declaring root: {project_dir}")
    return ListRootsResult(roots=[
        Root(uri=AnyUrl(f"file://{project_dir}"), name="Institute MCP Project"),
    ])


# ─────────────────────────────────────────────────────────────
# MENU HANDLERS
# ─────────────────────────────────────────────────────────────

async def demo_sampling(session: ClientSession):
    section("Demo 1 — Sampling")
    print("  The server tool generate_course_summary will call the LLM")
    print("  through THIS client using the sampling protocol.\n")

    course_id = input("  Enter course ID (1=Python, 2=Data Science, 3=Java, 4=DevOps): ").strip()
    if not course_id.isdigit():
        print("  Invalid ID.")
        return

    print(f"\n  Calling tool: generate_course_summary(course_id={course_id})")
    print("  (Watch for [SAMPLING CALLBACK FIRED] below)\n")

    result = await session.call_tool("generate_course_summary", {"course_id": int(course_id)})
    section("Tool Result")
    for c in result.content:
        print(c.text)


async def demo_elicitation(session: ClientSession):
    section("Demo 2 — Elicitation")
    print("  The server tool enroll_with_confirmation will ask YOU")
    print("  to confirm enrollment details via the elicitation protocol.\n")

    student_name = input("  Student name to search (e.g. Sneha): ").strip()
    batch_id     = input("  Batch ID to enroll in (1-5): ").strip()

    if not batch_id.isdigit():
        print("  Invalid batch ID.")
        return

    print(f"\n  Calling tool: enroll_with_confirmation")
    print("  (Watch for [ELICITATION CALLBACK FIRED] below)\n")

    result = await session.call_tool(
        "enroll_with_confirmation",
        {"student_name": student_name, "batch_id": int(batch_id)},
    )
    section("Tool Result")
    for c in result.content:
        print(c.text)


async def demo_roots(session: ClientSession):
    section("Demo 3 — Roots")
    print("  The server tool list_roots will ask this client")
    print("  what filesystem paths it has declared as roots.\n")
    print("  (Watch for [ROOTS CALLBACK FIRED] below)\n")

    result = await session.call_tool("list_roots", {})
    section("Tool Result")
    for c in result.content:
        try:
            print(json.dumps(json.loads(c.text), indent=2))
        except Exception:
            print(c.text)


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

async def run():
    server_params = StdioServerParameters(command="python", args=["main.py"])

    banner("Deccansoft Institute — Module 9 Demo Client")
    print("  Features: Sampling | Elicitation | Roots")
    print("  Connecting to MCP server (stdio)...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read, write,
            sampling_callback    = sampling_callback,
            elicitation_callback = elicitation_callback,
            list_roots_callback  = list_roots_callback,
        ) as session:
            await session.initialize()
            print("  Connected!\n")

            while True:
                print(f"\n{SEP}")
                print("  MAIN MENU — Module 9 Demos")
                print(SEP)
                print("  1. Sampling    — AI generates a course summary (LLM runs here on client)")
                print("  2. Elicitation — Enroll a student with your confirmation")
                print("  3. Roots       — Server reads this client's declared filesystem roots")
                print("  0. Exit")
                print(SEP)

                choice = input("  Choose: ").strip()

                if choice == "1":
                    await demo_sampling(session)
                elif choice == "2":
                    await demo_elicitation(session)
                elif choice == "3":
                    await demo_roots(session)
                elif choice == "0":
                    print("\n  Goodbye!\n")
                    break
                else:
                    print("  Invalid choice.")


if __name__ == "__main__":
    asyncio.run(run())
