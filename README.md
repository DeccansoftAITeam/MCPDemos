# MCP Client Primitives — Sampling & Elicitation

A minimal, runnable demo of two MCP **client primitives** — the capabilities a
client exposes so a server can call *back into* it:

| Tool | Primitive | What happens |
|------|-----------|--------------|
| `create_product` | **Sampling** | Server asks the client to run an LLM and generate a product description. |
| `book_vacation` | **Elicitation** | Server asks the user to confirm booking details via a form. |
| `recommend_flight` | **Both** | Server *elicits* your flight preferences, then *samples* the LLM to pick a flight. |

The server holds **no** model key and renders **no** UI. It just asks; the
client supplies the LLM (Sampling) and the user form (Elicitation).

## Files

- `server.py` — FastMCP server with the three tools (stdio).
- `client.py` — interactive **console** client; spawns the server and hosts both callbacks.
- `web_client.py` — **web** client: a FastAPI bridge that hosts the same MCP session and serves a browser UI.
- `index.html` — the single-page front-end (cards, live event log, schema-driven form).
- `llm.py` — the LLM the client runs (OpenAI, with an offline fallback).

There are two front-ends for the **same** `server.py`: a console client and a web
client. The server never changes — only how the client surfaces sampling and
elicitation to the user does.

## Setup

### Option A — venv + pip

```bash
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### Option B — uv

```bash
uv venv
uv pip install -r requirements.txt
```

## Set your OpenAI key

```bash
# macOS / Linux
export OPENAI_API_KEY=sk-your-key-here
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-your-key-here"
```

Without a key, the client still runs — Sampling falls back to a deterministic
offline mock so the flow works end to end. Set the key to use a real model.

## Run (console)

```bash
python client.py
```

The client launches `server.py` for you over stdio, then shows a menu:

```
  1) Sampling      -> create_product
  2) Elicitation   -> book_vacation
  3) Both          -> recommend_flight
  q) quit
```

## Run (web)

```bash
uvicorn web_client:app --reload
# then open http://127.0.0.1:8000
```

The web client spawns the same `server.py`, holds one MCP session open, and
serves `index.html`. Sampling streams its progress into the live log; elicitation
pops a form built from the schema the server sent — submit, decline, or cancel,
and watch the result come back.

Watch the terminal: `[CLIENT]` lines show your side (callbacks firing, calling
the LLM), and `[SERVER]` lines (on stderr) show the server requesting sampling
or elicitation. That interleaving is the "direction flip" in action.

## The flow, briefly

Every tool call follows the same shape: `call_tool` goes in, the server makes
one or more `server -> client` callbacks in the middle, and a result comes back.
The only difference is *which* callback fires:

- `create_product`: `create_message()` → your `sampling_callback` → OpenAI → back.
- `book_vacation`: `ctx.elicit()` → your `elicitation_callback` → user → back.
- `recommend_flight`: elicitation first (preferences), then sampling (the pick).

## Try the three elicitation outcomes

When `book_vacation` (or phase 1 of `recommend_flight`) prompts you, you can:

- press **Enter** to fill the form (→ `accept`),
- type **d** to **decline**,
- type **c** to **cancel**.

The server branches its return value on each.
