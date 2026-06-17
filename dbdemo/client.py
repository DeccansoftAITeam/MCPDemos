# mcp_client.py

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            await session.initialize()

            print("\n=== Available Tools ===")
            tools = await session.list_tools()
            for tool in tools.tools:
                print(tool.name)

            print("\n=== 1. List Tables ===")
            result = await session.call_tool("list_tables", {})
            print(result.content[0].text)

            print("\n=== 2. SELECT Query ===")
            result = await session.call_tool(
                "query", {"sql": "SELECT name, price FROM products ORDER BY price DESC"}
            )
            json_result = json.loads(result.content[0].text)
            for row in json_result["rows"]:
                print(row)

            print("\n=== 3. Parameterized Query ===")
            result = await session.call_tool(
                "query",
                {
                    "sql": "SELECT * FROM products WHERE category = ?",
                    "params": ["hardware"]
                }
            )
            json_result = json.loads(result.content[0].text)
            for row in json_result["rows"]:
                print(row)

            print("\n=== 4. Write Attempt (Should Fail) ===")
            try:
                result = await session.call_tool(
                    "query",
                    {
                        "sql": "INSERT INTO products(name) VALUES ('x')"
                    }
                )
                print(result.content[0].text)
            except Exception as e:
                print("Expected Error:", e)

            print("\n=== 5. Stacked Query Injection (Should Fail) ===")
            try:
                result = await session.call_tool(
                    "query",
                    {
                        "sql": "SELECT 1; DROP TABLE products"
                    }
                )
                print(result.content[0].text)
            except Exception as e:
                print("Expected Error:", e)

            print("\n=== 6. Table Name Injection (Should Fail) ===")
            try:
                result = await session.call_tool(
                    "describe_table",
                    {
                        "table": "products; DROP TABLE products"
                    }
                )
                print(result.content[0].text)
            except Exception as e:
                print("Expected Error:", e)


if __name__ == "__main__":
    asyncio.run(main())
