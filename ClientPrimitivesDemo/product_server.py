"""
product_server.py — the MCP server (FastMCP, stdio transport).

Three tools, each demonstrating a client primitive:

  create_product   -> SAMPLING      : server asks the client to run an LLM
  book_vacation    -> ELICITATION   : server asks the user for structured input
  recommend_flight -> BOTH          : elicit preferences, then sample the LLM

IMPORTANT: over stdio, this process's STDOUT is the MCP protocol channel.
Never print() to stdout here — all human-readable narration goes to STDERR
via log(), which shows up in the client's terminal without corrupting traffic.
"""

import json
import sys
from typing import Literal

from pydantic import BaseModel, Field

from mcp.server.mcpserver import MCPServer, Context
from mcp.server.session import ServerSession
from mcp.types import (
    SamplingMessage,
    TextContent,
)

mcp = MCPServer("product server")


def log(msg: str) -> None:
    """Narrate to STDERR (stdout is reserved for the MCP protocol)."""
    print(f"[SERVER] {msg}", file=sys.stderr, flush=True)

# ---------------------------------------------------------------------------
# Schema — FastMCP turns this Pydantic model into the JSON schema the client
# receives in the elicitation/create request.
# ---------------------------------------------------------------------------
class LaunchConfirmation(BaseModel):
    confirmLaunch: bool = Field(
        description="Confirm you want to launch this product"
    )
    price: float = Field(
        default=29.99, ge=0, description="Retail price (USD)"
    )
    initialStock: int = Field(
        default=100, ge=0, description="Initial stock quantity"
    )
    shippingSpeed: str = Field(
        default="standard",
        description="Shipping speed to offer at launch",
        json_schema_extra={"enum": ["standard", "priority", "overnight"]},
    )

# ---------------------------------------------------------------------------
# 2. ELICITATION — launch_product
# ---------------------------------------------------------------------------
@mcp.tool()
async def launch_product(
    product_name: str,
    ctx: Context[ServerSession, None],
) -> str:
    """Launch a product, confirming pricing and inventory with the user first."""
    log(f"launch_product: eliciting launch details for '{product_name}'...")
    # Server -> Client: elicitation/create goes out here. The client renders
    # a form from LaunchConfirmation and the user fills / declines / cancels.
    result = await ctx.elicit(
        message=f"Please confirm launch details for '{product_name}':",
        schema=LaunchConfirmation,
    )

    if result.action == "accept" and result.data:
        data = result.data
        if not data.confirmLaunch:
            return "Launch not confirmed by user."
        log("launch_product: user accepted, finalizing launch.")
        return (
            f"Launched {product_name}! "
            f"Price: ${data.price:.2f}, "
            f"Initial stock: {data.initialStock}, "
            f"Shipping: {data.shippingSpeed}."
        )
    elif result.action == "decline":
        log("launch_product: user declined.")
        return "User declined to provide launch details."
    else:  # "cancel"
        log("launch_product: user cancelled.")
        return "User cancelled the launch flow."

@mcp.tool()
async def create_product(
    product_name: str,
    keywords: str,
    ctx: Context[ServerSession, None],
) -> str:
    """Create a product and generate its description using LLM sampling."""
    prompt = (
        f"Create a product description about {product_name} "
        f"described as {keywords}"
    )

    log(f"create_product: requesting sampling for '{product_name}'...")
    # Server -> Client: ask the client's LLM to generate text. The server
    # has no model key — create_message() hands the work to the client.
    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=prompt),
            )
        ],
        system_prompt="You are a helpful assistant. Create a compelling product description.",
        max_tokens=200,
    )

    description = result.content.text
    log("create_product: received description, returning JSON.")
    return json.dumps({"name": product_name, "description": description}, indent=2)

if __name__ == "__main__":
    log("product-server starting on stdio...")
    mcp.run()  # stdio transport by default
