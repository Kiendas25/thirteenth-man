"""Thin wrapper around the OpenAI chat-completions API."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.config import settings

log = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        key = settings.openai_api_key
        if not key or key == "sk-your-key-here":
            raise RuntimeError(
                "OPENAI_API_KEY not configured. "
                "Edit your .env file and set a valid key."
            )
        _client = AsyncOpenAI(api_key=key)
    return _client


async def chat(
    system: str,
    user: str,
    *,
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 4096,
    response_format: dict[str, Any] | None = None,
) -> str:
    """Send a chat completion request and return the assistant content."""
    client = _get_client()
    kwargs: dict[str, Any] = {
        "model": model or settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format

    log.debug("LLM request: model=%s tokens=%d", kwargs["model"], max_tokens)
    try:
        resp = await client.chat.completions.create(**kwargs)
    except Exception as exc:
        log.error("OpenAI API error: %s", exc)
        raise RuntimeError(f"OpenAI API error: {exc}") from exc
    content = resp.choices[0].message.content or ""
    log.debug("LLM response length: %d chars", len(content))
    return content


async def chat_json(
    system: str,
    user: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Chat completion that returns parsed JSON."""
    raw = await chat(
        system,
        user,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Failed to parse JSON from LLM, returning raw text wrapper")
        return {"raw": raw}
