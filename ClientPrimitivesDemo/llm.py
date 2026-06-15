"""
llm.py — the LLM the CLIENT runs on the server's behalf (Sampling).

The whole point of Sampling is that the *client* owns model access, not the
server. So this module lives on the client side. The server never sees a key.

Real path  : OpenAI Chat Completions (set OPENAI_API_KEY).
Fallback   : a deterministic offline generator, so a live demo never hard-fails
             if the network or key is missing. Set a key to use the real model.
"""

import os

MODEL = "gpt-5"
_API_KEY = "<ENTER KEY HERE>"

async def call_llm(prompt: str, system_prompt: str = "") -> str:
    """Run one completion. Returns the generated text."""
    system_prompt = system_prompt or "You are a helpful assistant."

    # ---- Real model: OpenAI SDK (client's own credentials) ----
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=_API_KEY)
    resp = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],        
    )
    return (resp.choices[0].message.content or "").strip()


