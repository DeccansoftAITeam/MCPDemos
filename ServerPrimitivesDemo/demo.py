import asyncio
from mcp.server.mcpserver import MCPServer, Context

mcp = MCPServer("Demo Server", "A demo server for the MCP framework.")

@mcp.tool()
def dummy_tool() -> str:
    """A simple tool that returns a string."""
    return "Hello from the dummy tool!"

def beta_feature() -> str:
    """A tool that only exists once the user opts in."""
    return "beta"

@mcp.tool()
async def enable_beta(ctx: Context) -> str:
    """Turn on the beta toolset for this session."""
    # MCPServer.add_tool() accepts the function and builds the Tool wrapper.
    mcp.add_tool(beta_feature)
    await ctx.session.send_tool_list_changed()      # ← the announcement
    return "Beta tools enabled."

if __name__ == "__main__":
    mcp.run(transport="stdio") 
