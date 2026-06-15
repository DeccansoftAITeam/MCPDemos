import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

openai_client = OpenAI(
    api_key="<YOUR_OPENAI_API_KEY>",
  #  base_url="https://api.openai.com/v1",
)
async def main():
    server_params = StdioServerParameters(command="python", args=["server.py"])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Fetch tools from MCP and convert to OpenAI format
            mcp_tools = await session.list_tools()
            openai_tools = [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                }
                for tool in mcp_tools.tools
            ]

            # 2. Send user message to OpenAI with tools available
            inputs = ["What is AI?"]
            previous_response_Id = None
        while(True):
            response = openai_client.responses.create(
                model="gpt-4.1",
                input=inputs,
                previous_response_id=previous_response_Id,
                tools=openai_tools,
            )
            previous_response_Id = response.id
            if response.output_text:
                print("Final answer:", response.output_text)
                return

            # 3. If LLM called a tool, execute it via MCP
            inputs = []
            for item in response.output:
                if item.type == "function_call":
                    args = json.loads(item.arguments)
                    print(f"LLM called '{item.name}' with args: {args}")

                    mcp_result = await session.call_tool(item.name, args)
                    tool_output = mcp_result.content[0].text
                    
                    inputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": tool_output,
                })

asyncio.run(main())
