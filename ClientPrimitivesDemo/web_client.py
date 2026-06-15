"""
web_client.py — a browser front-end for the same MCP server.

This is the console client's job, moved to the web:
  * it spawns server.py over stdio and holds one ClientSession open,
  * it registers the sampling_callback and elicitation_callback,
  * sampling runs the LLM and streams progress to the browser,
  * elicitation pushes the schema to the browser as a real form, then waits
    for the user's submit / decline / cancel before returning.

server.py and llm.py are unchanged — only the client's transport to the
*user* is different (HTML form instead of console prompts).

Run:  uvicorn web_client:app --reload      (or: python web_client.py)
Open: http://127.0.0.1:8000
"""

import asyncio
import contextlib
import json
import os
import sys
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse

from mcp import ClientSession, types
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.shared.context import RequestContext

import llm

HERE = os.path.dirname(os.path.abspath(__file__))

# --- shared state (single-user demo) -------------------------------------
SESSION: ClientSession | None = None
EVENTS: asyncio.Queue | None = None              # server -> browser event bus
PENDING: dict[str, asyncio.Future] = {}          # in-flight elicitations


def emit(kind: str, **data) -> None:
    """Push an event to the browser (over SSE)."""
    if EVENTS is not None:
        EVENTS.put_nowait({"kind": kind, **data})


# --- MCP callbacks (the "direction flip" lands here) ---------------------
async def sampling_callback(
    context: RequestContext["ClientSession", None],
    params: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    emit("log", source="client", text="sampling_callback fired — server asked for an LLM completion")
    user_text = params.messages[0].content.text
    system_prompt = params.systemPrompt or ""

    emit("log", source="llm", text=f"calling {llm.model_name()}...")
    response = await llm.call_llm(user_text, system_prompt=system_prompt)
    emit("log", source="client", text="returning completion to server")

    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(type="text", text=response),
        model=llm.model_name(),
        stopReason="endTurn",
    )


async def elicitation_callback(
    context: RequestContext["ClientSession", None],
    params: types.ElicitRequestParams,
) -> types.ElicitResult:
    emit("log", source="client", text="elicitation_callback fired — asking the user for input")

    rid = uuid.uuid4().hex
    fut: asyncio.Future = asyncio.get_event_loop().create_future()
    PENDING[rid] = fut

    # Hand the schema to the browser to render as a form.
    emit("form_request", id=rid, message=params.message, schema=params.requestedSchema or {})

    action, content = await fut          # resolved by POST /api/elicit/{rid}
    PENDING.pop(rid, None)

    if action == "accept":
        emit("log", source="client", text="submitting the user's answers to the server")
        return types.ElicitResult(action="accept", content=content)
    emit("log", source="client", text=f"user {action}d the request")
    return types.ElicitResult(action=action)


# --- app lifecycle: keep one MCP session open for the app's lifetime -----
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global SESSION, EVENTS
    EVENTS = asyncio.Queue()

    server_params = StdioServerParameters(
        command=sys.executable, args=[os.path.join(HERE, "server.py")]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read,
            write,
            sampling_callback=sampling_callback,
            elicitation_callback=elicitation_callback,
        ) as session:
            await session.initialize()
            SESSION = session
            try:
                yield
            finally:
                SESSION = None


app = FastAPI(lifespan=lifespan)


# --- tool runner ----------------------------------------------------------
async def run_tool(tool: str, args: dict) -> None:
    emit("running", tool=tool)
    emit("log", source="client", text=f"call_tool: {tool}")
    try:
        result = await SESSION.call_tool(tool, args)
        text = "\n".join(
            b.text for b in result.content if isinstance(b, types.TextContent)
        )
        emit("result", tool=tool, text=text)
    except Exception as exc:  # surface tool/validation errors in the UI
        emit("error", text=f"{type(exc).__name__}: {exc}")
    finally:
        emit("done", tool=tool)


# --- routes ---------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    with open(os.path.join(HERE, "index.html"), encoding="utf-8") as fh:
        return fh.read()


@app.get("/api/status")
async def status() -> JSONResponse:
    return JSONResponse({"llm_mode": llm.model_name(), "real": llm.using_real_llm()})


@app.post("/api/run/{tool}")
async def api_run(tool: str, request: Request) -> JSONResponse:
    if SESSION is None:
        return JSONResponse({"ok": False, "error": "session not ready"}, status_code=503)
    args = await request.json()
    asyncio.create_task(run_tool(tool, args))   # stream results via SSE
    return JSONResponse({"ok": True})


@app.post("/api/elicit/{rid}")
async def api_elicit(rid: str, request: Request) -> JSONResponse:
    body = await request.json()
    fut = PENDING.get(rid)
    if fut is None or fut.done():
        return JSONResponse({"ok": False, "error": "no pending elicitation"}, status_code=404)
    action = body.get("action", "cancel")
    content = body.get("content") or {}
    fut.set_result((action, content))
    return JSONResponse({"ok": True})


@app.get("/events")
async def events(request: Request) -> StreamingResponse:
    async def stream():
        while True:
            if await request.is_disconnected():
                break
            try:
                ev = await asyncio.wait_for(EVENTS.get(), timeout=15)
                yield f"data: {json.dumps(ev)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_client:app", host="127.0.0.1", port=8000, reload=False)
