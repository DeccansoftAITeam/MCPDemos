# client.py - Streamable HTTP client that sends a Bearer JWT to the protected server.
# Reads TOKEN from .env (generate it first with: python util.py).
#   python client.py
import asyncio
import os

import httpx
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

load_dotenv()

port = 8000


async def main():
    token = os.getenv("TOKEN")
    if not token:
        print("TOKEN not found in .env file, run util.py to generate one.")
        raise ValueError("TOKEN not found in .env file")

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}
    ) as http_client:
        async with streamable_http_client(
            url=f"http://localhost:{port}/mcp",
            http_client=http_client,
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tool_result = await session.call_tool("get_time", {})
                print(f"Tool result: {tool_result.content[0].text}")


if __name__ == "__main__":
    print("Running MCP client...")
    asyncio.run(main())
