"""
flight_client.py — the MCP client (stdio). Spawns flight_server.py and drives it live.

It registers the two callbacks that make the "direction flip" possible:

  sampling_callback     fires when the server calls create_message()
                        -> we call the LLM directly and return the text.

  elicitation_callback  fires when the server calls ctx.elicit()
                        -> we render a console form, collect the user's input,
                           and return accept / decline / cancel.

Run:  python flight_client.py
The client launches flight_server.py automatically over stdio.
"""

import asyncio
import os
import sys
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()  # load .env file if present

from mcp import ClientSession, types
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientRequestContext

_API_KEY = os.getenv("OPENAI_API_KEY")

async def handle_sampling_message(
    context: ClientRequestContext,
    params: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    print(f"[CLIENT] sampling_callback fired — the server asked for an LLM completion.", flush=True)

    # Everything the server sent is in params.
    user_text = params.messages[0].content.text
    system_prompt = params.system_prompt or ""

    print(f"  calling LLM...", flush=True)
    client = AsyncOpenAI(api_key=_API_KEY)
    response = await client.chat.completions.create(
        model="gpt-5.6-luna",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    )
    print(f"  returning the completion to the server.", flush=True)
    response = response.choices[0].message.content
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(type="text", text=response),
        model="gpt-5.6-luna",
        stopReason="endTurn",
    )

# ---------------------------------------------------------------------------
# ELICITATION callback — the client renders a form and collects user input
# ---------------------------------------------------------------------------
async def handle_elicitation(
    context: ClientRequestContext,
    params: types.ElicitRequestParams,
) -> types.ElicitResult:
    print(f"[CLIENT] elicitation_callback fired — the server is asking the user for input.", flush=True)

    schema = params.requested_schema or {}
    print(f"\n  {params.message}")
    choice = input(
        "  Proceed? [Enter = fill form,  d = decline,  c = cancel]: "
    ).strip().lower()

    if choice == "d":
        print(f"[CLIENT]   user declined.", flush=True)
        return types.ElicitResult(action="decline")
    if choice == "c":
        print(f"[CLIENT]   user cancelled.", flush=True)
        return types.ElicitResult(action="cancel")

    answers = _fill_form(schema)
    print(f"[CLIENT]   submitting the user's answers to the server.", flush=True)
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

async def demo_elicitation(session: ClientSession) -> None:
    print("ELICITATION demo  ->  book_vacation")
    destination = input("Destination [Paris]: ").strip() or "Paris"
    print(f"calling tool book_vacation(destination='{destination}')...", flush=True)
    result = await session.call_tool("book_vacation", {"destination": destination})
    print("\n--- tool result ---")
    print(_result_text(result))

async def demo_both(session: ClientSession) -> None:
    print("BOTH demo  ->  recommend_flight  (elicit, then sample)", flush=True)
    flight_data = (
        "1) AirOne   06:10 -> 14:30  $420  1 layover\n"
        "2) SkyJet   09:00 -> 12:15  $560  nonstop\n"
        "3) BudgetAir 22:40 -> 06:05 $310  2 layovers\n"
        "4) GlobalWings 07:30 -> 15:50 $480 1 layover"
    )
    print("Flights on offer:")
    print(flight_data)
    print("calling tool recommend_flight(...)  [will elicit, then sample]", flush=True)
    result = await session.call_tool("recommend_flight", {"flight_data": flight_data})
    print("\n--- tool result ---")
    print(_result_text(result))


# ---------------------------------------------------------------------------
# Main — spawn the server, wire both callbacks, run the menu
# ---------------------------------------------------------------------------
async def main() -> None:
    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flight_server.py")
    server_params = StdioServerParameters(command=sys.executable, args=[server_path])

    print("MCP Client Primitives — Sampling & Elicitation", flush=True)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read,
            write,
            sampling_callback=handle_sampling_message,
            elicitation_callback=handle_elicitation,
        ) as session:
            await session.initialize()
            print("connected to travel-server.", flush=True)

            while True:
                print(
                    "\nChoose a demo:\n"
                    "  1) Elicitation   -> book_vacation\n"
                    "  2) Both          -> recommend_flight\n"
                    "  q) quit"
                )
                pick = input("> ").strip().lower()
                if pick == "1":
                    await demo_elicitation(session)
                elif pick == "2":
                    await demo_both(session)
                elif pick in ("q", "quit", "exit"):
                    print("bye.", flush=True)
                    break
                else:
                    print("Pick 1, 2, 3, or q.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[CLIENT] interrupted.")