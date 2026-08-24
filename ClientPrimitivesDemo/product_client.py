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

# ---------------------------------------------------------------------------
# ELICITATION callback — the client renders a form and collects user input
# ---------------------------------------------------------------------------
async def handle_elicitation(
    context: ClientRequestContext,
    params: types.ElicitRequestParams,
) -> types.ElicitResult:
    print(
        f"[CLIENT] elicitation_callback fired — the server is asking the user for input.",
        flush=True,
    )

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

    answers = _fill_form()
    print(f"[CLIENT]   submitting the user's answers to the server.", flush=True)
    return types.ElicitResult(action="accept", content=answers)

def _fill_form() -> dict:
    """Prompt for the fields of LaunchConfirmation (console 'form')."""
    confirm = input("  - Confirm you want to launch this product (y/n): ").strip().lower()
    confirm_launch = confirm in ("y", "yes", "true", "1")

    price_raw = input("  - Retail price (USD) [default: 29.99]: ").strip()
    price = float(price_raw) if price_raw else 29.99

    stock_raw = input("  - Initial stock quantity [default: 100]: ").strip()
    initial_stock = int(stock_raw) if stock_raw else 100

    shipping_options = ["standard", "priority", "overnight"]
    print("  - Shipping speed to offer at launch [default: standard]")
    for i, opt in enumerate(shipping_options, 1):
        print(f"      {i}) {opt}")
    shipping_raw = input("    choose number (or Enter for default): ").strip()
    if shipping_raw.isdigit() and 1 <= int(shipping_raw) <= len(shipping_options):
        shipping_speed = shipping_options[int(shipping_raw) - 1]
    else:
        shipping_speed = "standard"

    return {
        "confirmLaunch": confirm_launch,
        "price": price,
        "initialStock": initial_stock,
        "shippingSpeed": shipping_speed,
    }


async def demo_elicitation(session: ClientSession) -> None:
    print("ELICITATION demo  ->  launch_product")
    name = input("Product name [EcoBottle]: ").strip() or "EcoBottle"
    print(f"[CLIENT] Calling tool launch_product(name='{name}')...", flush=True)
    result = await session.call_tool("launch_product", {"product_name": name})
    print("\n--- tool result ---")
    print(_result_text(result))

async def handle_sampling_message(
    context: ClientRequestContext,
    params: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    print(
        f"[CLIENT] sampling_callback fired — the server asked for an LLM completion.",
        flush=True,
    )

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
# Tool invocations (each prints the live round-trip)
# ---------------------------------------------------------------------------
def _result_text(result) -> str:
    parts = [b.text for b in result.content if isinstance(b, types.TextContent)]
    return "\n".join(parts)

async def demo_sampling(session: ClientSession) -> None:
    print("SAMPLING demo  ->  create_product")
    name = input("Product name [EcoBottle]: ").strip() or "EcoBottle"
    keywords = (
        input(
            "Keywords [sustainable, stainless steel, keeps drinks cold 24h]: "
        ).strip()
        or "sustainable, stainless steel, keeps drinks cold 24h"
    )
    print(f"[CLIENT] Calling tool create_product(name='{name}')...", flush=True)
    result = await session.call_tool(
        "create_product", {"product_name": name, "keywords": keywords}
    )
    print("\n--- tool result ---")
    print(_result_text(result))

async def main() -> None:
    server_params = StdioServerParameters(command=sys.executable, args=["product_server.py"])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read,
            write,
            sampling_callback=handle_sampling_message,
            elicitation_callback=handle_elicitation,
        ) as session:
            await session.initialize()
            print(f"[CLIENT] connected to product-server.", flush=True)

            while True:
                print(
                    "\nChoose a demo:\n"
                    "  1) Sampling      -> create_product\n"
                    "  2) Elicitation   -> launch_product\n"
                    "  q) quit"
                )
                pick = input("> ").strip().lower()
                if pick == "1":
                    await demo_sampling(session)
                elif pick == "2":
                    await demo_elicitation(session)
                elif pick in ("q", "quit", "exit"):
                    print("bye.", flush=True)
                    break
                else:
                    print("Pick 1, 2, or q.")

if __name__ == "__main__":
        asyncio.run(main())
