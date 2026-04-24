"""
Zhipu (OpenAI-compatible) JSON helpers for HR / Legal / Finance agents.
Falls back to Gemini automatically when Zhipu returns 504 / times out.
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


@lru_cache()
def get_gemini_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.google_api_key or "sk-placeholder",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )


def get_zhipu_model() -> str:
    return get_settings().zhipu_model


def get_gemini_model() -> str:
    return get_settings().llm_model


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


async def _call_llm(client: AsyncOpenAI, model: str, system: str, user: str, temperature: float) -> Dict[str, Any]:
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


async def llm_json(system: str, user: str, temperature: float = 0.2) -> Dict[str, Any]:
    zhipu_model = get_zhipu_model()
    logger.info(
        "[Zhipu] chat.completions model=%r user_chars=%d system_chars=%d temp=%s",
        zhipu_model,
        len(user or ""),
        len(system or ""),
        temperature,
    )
    try:
        return await _call_llm(get_zhipu_client(), zhipu_model, system, user, temperature)
    except Exception as zhipu_exc:
        gemini_model = get_gemini_model()
        logger.warning(
            "[Zhipu] failed (%s), falling back to Gemini (%s)",
            type(zhipu_exc).__name__,
            gemini_model,
        )
        try:
            result = await _call_llm(get_gemini_client(), gemini_model, system, user, temperature)
            logger.info("[Gemini fallback] success for specialist agent")
            return result
        except Exception as gemini_exc:
            logger.error("[Gemini fallback] also failed: %s", gemini_exc)
            raise zhipu_exc from None
