"""
Zhipu (OpenAI-compatible) JSON helpers for HR / Legal / Finance agents.

Separated from services/llm_client.py (Gemini) so specialist agents can use
Ilmu/Zhipu without changing the manager or document pipeline.
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from typing import Any, Dict

from openai import AsyncOpenAI

from config import get_settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_zhipu_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.zhipu_api_key or "sk-placeholder",
        base_url=settings.zhipu_base_url,
    )


def get_zhipu_model() -> str:
    return get_settings().zhipu_model


def _extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        return json.loads(m.group(1))
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return json.loads(m.group(0))
    raise ValueError(f"Cannot extract JSON from LLM response: {text[:300]!r}")


async def llm_json(system: str, user: str, temperature: float = 0.2) -> Dict[str, Any]:
    client = get_zhipu_client()
    model = get_zhipu_model()
    logger.info(
        "[Zhipu] chat.completions model=%r user_chars=%d system_chars=%d temp=%s",
        model,
        len(user or ""),
        len(system or ""),
        temperature,
    )
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    raw = (response.choices[0].message.content or "").strip()
    return _extract_json(raw)
