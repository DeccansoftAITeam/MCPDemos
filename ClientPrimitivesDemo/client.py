"""
client.py — the MCP client (stdio). Spawns server.py and drives it live.

It registers the two callbacks that make the "direction flip" possible:

  sampling_callback     fires when the server calls create_message()
                        -> we run the LLM (llm.call_llm) and return the text.

  elicitation_callback  fires when the server calls ctx.elicit()
                        -> we render a console form, collect the user's input,
                           and return accept / decline / cancel.

Run:  python client.py
The client launches server.py automatically over stdio.
"""

import asyncio
import os
import sys

from mcp import ClientSession, types
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.shared.context import RequestContext

import llm


# ---------------------------------------------------------------------------
# Tiny console helpers (client stdout is the user's terminal — printing is fine)
# ---------------------------------------------------------------------------
def c(msg: str) -> None:
    print(f"[CLIENT] {msg}", flush=True)


def rule(title: str) -> None:
    print("\n" + "=" * 64)
    print(f"  {title}")
    print("=" * 64)


# ---------------------------------------------------------------------------
# SAMPLING callback — the client runs the LLM on the server's behalf
# ---------------------------------------------------------------------------
async def handle_sampling_message(
    context: RequestContext["ClientSession", None],
    params: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    c("sampling_callback fired — the server asked for an LLM completion.")

    # Everything the server sent is in params.
    user_text = params.messages[0].content.text
    system_prompt = params.systemPrompt or ""

    c(f"  calling LLM...")
    response = await llm.call_llm(user_text, system_prompt=system_prompt)
    c("  returning the completion to the server.")

    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(type="text", text=response),
        model=llm.MODEL,
        stopReason="endTurn",
    )


# ---------------------------------------------------------------------------
# ELICITATION callback — the client renders a form and collects user input
# ---------------------------------------------------------------------------
async def handle_elicitation(
    context: RequestContext["ClientSession", None],
    params: types.ElicitRequestParams,
) -> types.ElicitResult:
    c("elicitation_callback fired — the server is asking the user for input.")

    schema = params.requestedSchema or {}
    print(f"\n  {params.message}")
    choice = input(
        "  Proceed? [Enter = fill form,  d = decline,  c = cancel]: "
    ).strip().lower()

    if choice == "d":
        c("  user declined.")
        return types.ElicitResult(action="decline")
    if choice == "c":
        c("  user cancelled.")
        return types.ElicitResult(action="cancel")

    answers = _fill_form(schema)
    c("  submitting the user's answers to the server.")
    return types.ElicitResult(action="accept", content=answers)


def _fill_form(schema: dict) -> dict:
    """Walk the JSON schema and prompt for each field (console 'form')."""
    props = schema.get("properties", {})
    answers: dict = {}

    for name, spec in props.items():
        desc = spec.get("description", name)
        default = spec.get("default")
        enum = spec.get("enum")
        # enums may be nested via anyOf in some schema shapes
        if enum is None:
            for sub in spec.get("anyOf", []):
                if "enum" in sub:
                    enum = sub["enum"]
                    break
        jtype = spec.get("type")

        label = f"  - {desc}"
        if default is not None:
            label += f" [default: {default}]"

        if enum:
            print(label)
            for i, opt in enumerate(enum, 1):
                print(f"      {i}) {opt}")
            raw = input("    choose number (or Enter for default): ").strip()
            if raw == "" and default is not None:
                answers[name] = default
            elif raw.isdigit() and 1 <= int(raw) <= len(enum):
                answers[name] = enum[int(raw) - 1]
            else:
                answers[name] = default if default is not None else enum[0]

        elif jtype == "boolean":
            raw = input(f"{label} (y/n): ").strip().lower()
            if raw == "" and default is not None:
                answers[name] = bool(default)
            else:
                answers[name] = raw in ("y", "yes", "true", "1")

        elif jtype in ("integer", "number"):
            raw = input(f"{label}: ").strip()
            if raw == "" and default is not None:
                answers[name] = default
            else:
                try:
                    answers[name] = int(raw) if jtype == "integer" else float(raw)
                except ValueError:
                    answers[name] = default if default is not None else 0

        else:  # string / fallback
            raw = input(f"{label}: ").strip()
            answers[name] = raw if raw else (default if default is not None else "")

    return answers


# ---------------------------------------------------------------------------
# Tool invocations (each prints the live round-trip)
# ---------------------------------------------------------------------------
def _result_text(result) -> str:
    parts = [b.text for b in result.content if isinstance(b, types.TextContent)]
    return "\n".join(parts)


async def demo_sampling(session: ClientSession) -> None:
    rule("SAMPLING demo  ->  create_product")
    name = input("Product name [EcoBottle]: ").strip() or "EcoBottle"
    keywords = (

        input("Keywords [sustainable, stainless steel, keeps drinks cold 24h]: ").strip()
        or "sustainable, stainless steel, keeps drinks cold 24h"
    )
    c(f"calling tool create_product(name='{name}')...")
    result = await session.call_tool(
        "create_product", {"product_name": name, "keywords": keywords}
    )
    print("\n--- tool result ---")
    print(_result_text(result))


async def demo_elicitation(session: ClientSession) -> None:
    rule("ELICITATION demo  ->  book_vacation")
    destination = input("Destination [Paris]: ").strip() or "Paris"
    c(f"calling tool book_vacation(destination='{destination}')...")
    result = await session.call_tool("book_vacation", {"destination": destination})
    print("\n--- tool result ---")
    print(_result_text(result))


async def demo_both(session: ClientSession) -> None:
    rule("BOTH demo  ->  recommend_flight  (elicit, then sample)")
    flight_data = (
        "1) AirOne   06:10 -> 14:30  $420  1 layover\n"
        "2) SkyJet   09:00 -> 12:15  $560  nonstop\n"
        "3) BudgetAir 22:40 -> 06:05 $310  2 layovers\n"
        "4) GlobalWings 07:30 -> 15:50 $480 1 layover"
    )
    print("Flights on offer:")
    print(flight_data)
    c("calling tool recommend_flight(...)  [will elicit, then sample]")
    result = await session.call_tool("recommend_flight", {"flight_data": flight_data})
    print("\n--- tool result ---")
    print(_result_text(result))


# ---------------------------------------------------------------------------
# Main — spawn the server, wire both callbacks, run the menu
# ---------------------------------------------------------------------------
async def main() -> None:
    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
    server_params = StdioServerParameters(command=sys.executable, args=[server_path])

    rule("MCP Client Primitives — Sampling & Elicitation")    

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read,
            write,
            sampling_callback=handle_sampling_message,
            elicitation_callback=handle_elicitation,
        ) as session:
            await session.initialize()
            c("connected to travel-server.")

            while True:
                print(
                    "\nChoose a demo:\n"
                    "  1) Sampling      -> create_product\n"
                    "  2) Elicitation   -> book_vacation\n"
                    "  3) Both          -> recommend_flight\n"
                    "  q) quit"
                )
                pick = input("> ").strip().lower()
                if pick == "1":
                    await demo_sampling(session)
                elif pick == "2":
                    await demo_elicitation(session)
                elif pick == "3":
                    await demo_both(session)
                elif pick in ("q", "quit", "exit"):
                    c("bye.")
                    break
                else:
                    print("Pick 1, 2, 3, or q.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[CLIENT] interrupted.")