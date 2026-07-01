"""Thin wrapper around LLM APIs — supports OpenAI and Ollama."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from app.config import settings

log = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if settings.llm_provider == "ollama":
            _client = AsyncOpenAI(
                base_url=settings.ollama_base_url,
                api_key="ollama",  # Ollama doesn't need a real key
            )
            log.info(
                "Using Ollama at %s with model %s",
                settings.ollama_base_url,
                settings.llm_model,
            )
        else:
            key = settings.openai_api_key
            if not key or key == "sk-your-key-here":
                raise RuntimeError(
                    "OPENAI_API_KEY not configured. "
                    "Edit your .env file and set a valid key."
                )
            _client = AsyncOpenAI(api_key=key)
            log.info("Using OpenAI API with model %s", settings.llm_model)
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
    # Ollama supports JSON format via the OpenAI-compatible API
    if response_format is not None:
        kwargs["response_format"] = response_format

    log.debug("LLM request: model=%s tokens=%d", kwargs["model"], max_tokens)
    try:
        resp = await client.chat.completions.create(**kwargs)
    except Exception as exc:
        log.error("LLM API error: %s", exc)
        raise RuntimeError(f"LLM API error: {exc}") from exc
    content = resp.choices[0].message.content or ""
    log.debug("LLM response length: %d chars", len(content))
    return content


def _extract_json(text: str) -> dict[str, Any]:
    """Try to extract a JSON object from text, handling markdown fences."""
    # Try direct parse
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from markdown code block
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try finding first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    log.warning("Failed to extract JSON from LLM response")
    return {"raw": text}


async def chat_json(
    system: str,
    user: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Chat completion that returns parsed JSON."""
    try:
        raw = await chat(
            system,
            user,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return _extract_json(raw)
    except Exception:
        # Some models don't support response_format; retry without it
        log.info("Retrying without response_format (model may not support it)")
        system_with_json = system + "\n\nIMPORTANT: You MUST respond with ONLY a valid JSON object. No other text."
        raw = await chat(
            system_with_json,
            user,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return _extract_json(raw)
