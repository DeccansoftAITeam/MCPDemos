# server.py - MCP Resource Server (Streamable HTTP) protected by JWT + RBAC middleware.
#
# The CustomHeaderMiddleware enforces, on every request:
#   1. an Authorization: Bearer <jwt> header is present   (else 401)
#   2. the JWT is valid (signature + not expired)         (else 403)
#   3. the token's "name" is a known user                 (else 403)
#   4. the token carries the required scope "Admin.Write"  (else 403)  <- RBAC
#

from typing import Any
import datetime

from dotenv import load_dotenv
#from mcp.server.fastmcp.server import FastMCP
from mcp.server.mcpserver import MCPServer
import uvicorn

from auth_middleware import CustomHeaderMiddleware

load_dotenv()

settings = {
    "host": "localhost",
    "port": 8000,
}

mcp = MCPServer(
    name="MCP Resource Server",
    instructions="Resource Server that validates tokens via Authorization Server introspection",
    # host=settings["host"],
    # port=settings["port"],
    debug=True,
)


@mcp.tool()
async def get_time() -> dict[str, Any]:
    """
    Get the current server time.

    This tool demonstrates that system information can be protected
    by OAuth authentication. User must be authenticated to access it.
    """
    now = datetime.datetime.now()
    return {"current_time": now.isoformat()}


def main():
    print("Running MCP Resource Server...")
    app = mcp.streamable_http_app()
    print("Adding custom middleware...")
    app.add_middleware(CustomHeaderMiddleware)

    # Start the server and serve the app on the configured host/port.
    # `uvicorn.run(...)` blocks the current thread until the server stops.
    # We pass the app object directly so requests go through the custom middleware added earlier.
    uvicorn.run(
        app,
        host=settings["host"],
        port=settings["port"],
        log_level=mcp.settings.log_level.lower(),
    )

if __name__ == "__main__":
    main()
