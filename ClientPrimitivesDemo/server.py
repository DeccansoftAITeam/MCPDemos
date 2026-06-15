"""
server.py — the MCP server (FastMCP, stdio transport).

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

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession
from mcp.types import (
    SamplingMessage,
    TextContent,
    ModelPreferences,
    ModelHint,
)

mcp = FastMCP("travel-server")


def log(msg: str) -> None:
    """Narrate to STDERR (stdout is reserved for the MCP protocol)."""
    print(f"[SERVER] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Schemas — FastMCP turns these Pydantic models into the JSON schema the
# client receives in the elicitation/create request.
# ---------------------------------------------------------------------------
class BookingConfirmation(BaseModel):
    confirmBooking: bool = Field(
        description="Confirm the booking (Flights + Hotel = $3,000)"
    )
    seatPreference: str = Field(
        default="no preference",
        description="Preferred seat type for flights",
        json_schema_extra={"enum": ["window", "aisle", "no preference"]},
    )
    roomType: str = Field(
        default="city view",
        description="Preferred room type at hotel",
        json_schema_extra={"enum": ["sea view", "city view", "garden view"]},
    )
    travelInsurance: bool = Field(
        default=False,
        description="Add travel insurance ($150)",
    )
 
 
class FlightPreferences(BaseModel):
    departureTime: str = Field(
        default="no preference",
        description="Preferred departure time of day",
        json_schema_extra={"enum": ["morning", "afternoon", "evening", "no preference"]},
    )
    maxLayovers: int = Field(
        default=1, ge=0, le=3, description="Maximum number of layovers"
    )
    prioritizeCost: bool = Field(
        default=False, description="Prioritize cheaper flights over speed"
    )
    
# ---------------------------------------------------------------------------
# 1. SAMPLING — create_product
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 2. ELICITATION — book_vacation
# ---------------------------------------------------------------------------
@mcp.tool()
async def book_vacation(
    destination: str,
    ctx: Context[ServerSession, None],
) -> str:
    """Book a vacation package, confirming details with the user first."""
    log(f"book_vacation: eliciting confirmation for '{destination}'...")
    # Server -> Client: elicitation/create goes out here. The client renders
    # a form from BookingConfirmation and the user fills / declines / cancels.
    result = await ctx.elicit(
        message=f"Please confirm your {destination} vacation booking details:",
        schema=BookingConfirmation,
    )

    if result.action == "accept" and result.data:
        data = result.data
        if not data.confirmBooking:
            return "Booking not confirmed by user."
        insurance = " + insurance ($150)" if data.travelInsurance else ""
        log("book_vacation: user accepted, finalizing booking.")
        return (
            f"Booked {destination}! "
            f"Seat: {data.seatPreference}, "
            f"Room: {data.roomType}{insurance}. Total: $3,000."
        )
    elif result.action == "decline":
        log("book_vacation: user declined.")
        return "User declined to provide booking details."
    else:  # "cancel"
        log("book_vacation: user cancelled.")
        return "User cancelled the booking flow."


# ---------------------------------------------------------------------------
# 3. BOTH — recommend_flight (elicit preferences, then sample the LLM)
# ---------------------------------------------------------------------------
@mcp.tool()
async def recommend_flight(
    flight_data: str,
    ctx: Context[ServerSession, None],
) -> str:
    """Recommend a flight: ask the user for preferences, then ask the LLM to choose."""
    # --- Phase 1: ELICITATION — get preferences from the user ---
    log("recommend_flight: phase 1 — eliciting preferences...")
    pref = await ctx.elicit(
        message="What are your flight preferences?",
        schema=FlightPreferences,
    )

    if pref.action == "decline":
        return "Cannot recommend a flight — user declined to share preferences."
    if pref.action == "cancel" or not pref.data:
        return "Flight recommendation cancelled by user."

    p = pref.data
    prefs_text = (
        f"departure: {p.departureTime}, "
        f"max layovers: {p.maxLayovers}, "
        f"prioritize cost: {p.prioritizeCost}"
    )

    # --- Phase 2: SAMPLING — ask the LLM to reason over flights + preferences ---
    log("recommend_flight: phase 2 — requesting sampling for recommendation...")
    prompt = (
        "Analyze these flight options and recommend the best choice:\n"
        f"{flight_data}\n"
        f"User preferences: {prefs_text}"
    )
    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=prompt),
            )
        ],
        system_prompt="You are a travel expert. Recommend exactly one flight and explain why in 2-3 sentences.",
        model_preferences=ModelPreferences(
            hints=[ModelHint(name="gpt-4o-mini")],
            costPriority=0.3,
            speedPriority=0.2,
            intelligencePriority=0.9,
        ),
        max_tokens=400,
    )

    log("recommend_flight: received recommendation, returning.")
    return result.content.text


if __name__ == "__main__":
    log("travel-server starting on stdio...")
    mcp.run()  # stdio transport by default