from __future__ import annotations

import json
import logging
import os
import random
import threading
import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# Serialize async Gemini calls so sub-agents + manager don't burst and trip RPM limits
_thread_init = threading.Lock()
_async_llm_lock: Optional[asyncio.Lock] = None


def _get_async_llm_lock() -> asyncio.Lock:
    global _async_llm_lock
    with _thread_init:
        if _async_llm_lock is None:
            _async_llm_lock = asyncio.Lock()
    return _async_llm_lock


def _max_429_attempts() -> int:
    return max(1, int(os.getenv("LLM_429_MAX_RETRIES", "8")))


def _between_calls_sec() -> float:
    """Optional tiny pause after a successful call (stagger, same lock is main guard)."""
    return max(0.0, float(os.getenv("LLM_BETWEEN_CALLS_SEC", "0.15")))


def _backoff_seconds(attempt: int, resp: Optional[httpx.Response] = None) -> float:
    """Exponential backoff with jitter. Honor Retry-After when present."""
    if resp is not None and resp.status_code == 429:
        ra = resp.headers.get("retry-after")
        if ra:
            try:
                return min(120.0, float(ra) + random.uniform(0, 0.5))
            except ValueError:
                pass
    cap = max(8.0, float(os.getenv("LLM_429_MAX_BACKOFF_SEC", "60")))
    base = 4.0 * (1.6**attempt)
    wait = min(cap, base + random.uniform(0, 1.0))
    return max(3.0, wait)


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _extract_json_object_text(raw: str) -> str:
    raw = _strip_json_fence(raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end >= start:
        return raw[start : end + 1]
    return ""


@dataclass
class LLMResponse:
    text: str
    model: str


class UnifiedLLMClient:
    """
    Clean client optimized for Gemini-2.5-flash-lite.
    """

    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")  # IMPORTANT: normalize once

    @classmethod
    def from_settings(cls) -> Optional["UnifiedLLMClient"]:
        """
        Enforces correct pairing of API key + endpoint for Gemini.
        """
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()

        if provider == "gemini":
            return cls(
                api_key=os.getenv("GOOGLE_API_KEY"),
                model=os.getenv("LLM_MODEL", "gemini-2.5-flash-lite"),
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            )

        return None

    def _endpoint(self) -> str:
        """
        No guessing. Always correct endpoint.
        """
        return self.base_url

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(
        self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int
    ) -> Dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    def _extract_text(self, data: Dict[str, Any]) -> str:
        """
        Handles multiple response formats safely.
        """
        try:
            # Standard OpenAI format
            return data["choices"][0]["message"]["content"]
        except Exception:
            # fallback: print debug-friendly info
            return json.dumps(data)[:500]

    async def acomplete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 600,
    ) -> LLMResponse:
        url = self._endpoint()
        headers = self._headers()
        payload = self._payload(system_prompt, user_prompt, temperature, max_tokens)
        max_attempts = _max_429_attempts()

        # One in-flight request at a time to avoid self-inflicted 429s from parallel agents
        async with _get_async_llm_lock():
            async with httpx.AsyncClient(timeout=120.0) as client:
                last_429_response: Optional[httpx.Response] = None
                for attempt in range(max_attempts):
                    try:
                        resp = await client.post(url, headers=headers, json=payload)
                        if resp.status_code == 429:
                            last_429_response = resp
                            wait = _backoff_seconds(attempt, resp)
                            body_hint = (resp.text or "")[:200]
                            logger.warning(
                                "[LLM] Rate limited (429), attempt %s/%s. Waiting %.1fs. Hint: %s",
                                attempt + 1,
                                max_attempts,
                                wait,
                                body_hint,
                            )
                            await asyncio.sleep(wait)
                            continue
                        resp.raise_for_status()
                        data = resp.json()
                        text = self._extract_text(data)
                        await asyncio.sleep(_between_calls_sec())
                        return LLMResponse(text=text, model=self.model)
                    except httpx.HTTPStatusError as e:
                        if e.response is not None and e.response.status_code == 429:
                            last_429_response = e.response
                            wait = _backoff_seconds(attempt, e.response)
                            logger.warning(
                                "[LLM] HTTP 429, attempt %s/%s, waiting %.1fs",
                                attempt + 1,
                                max_attempts,
                                wait,
                            )
                            await asyncio.sleep(wait)
                            continue
                        raise
                    except (httpx.RequestError, json.JSONDecodeError) as e:
                        if attempt >= max_attempts - 1:
                            raise Exception(
                                f"LLM request failed after {max_attempts} attempts: {url} | {e!s}"
                            ) from e
                        await asyncio.sleep(1.0 + attempt)

                hint = (last_429_response.text or "")[:300] if last_429_response else "n/a"
                raise Exception(
                    "LLM: exhausted retries after HTTP 429 (rate limit). "
                    "Wait a few minutes, reduce how many sub-agents are routed at once, enable billing/quota in Google AI Studio, "
                    f"or increase LLM_429_MAX_RETRIES / LLM_429_MAX_BACKOFF_SEC. Last response hint: {hint!r}"
                )

    def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 600,
    ) -> LLMResponse:

        url = self._endpoint()
        headers = self._headers()
        payload = self._payload(system_prompt, user_prompt, temperature, max_tokens)

        with httpx.Client(timeout=120.0) as client:
            last: Optional[httpx.Response] = None
            for attempt in range(_max_429_attempts()):
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 429:
                    last = resp
                    wait = _backoff_seconds(attempt, resp)
                    logger.warning("[LLM sync] 429, sleeping %.1fs (attempt %s)", wait, attempt + 1)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                text = self._extract_text(data)
                time.sleep(_between_calls_sec())
                return LLMResponse(text=text, model=self.model)
        raise Exception(
            "LLM (sync): rate limited (429) after all retries. "
            "Back off and retry, or check Gemini quota in Google Cloud / AI Studio."
        )

    async def acomplete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 600,
    ) -> Tuple[Dict[str, Any], str]:

        for attempt in range(2):
            prompt = user_prompt
            if attempt == 1:
                prompt += "\n\nReturn ONLY valid JSON."

            response = await self.acomplete_text(
                system_prompt, prompt, temperature, max_tokens
            )

            json_text = _extract_json_object_text(response.text)

            if not json_text:
                if attempt == 0:
                    continue
                raise Exception("Invalid JSON response")

            try:
                return json.loads(json_text), response.model
            except json.JSONDecodeError:
                if attempt == 0:
                    continue
                raise Exception("JSON parsing failed")

        raise Exception("JSON extraction failed")

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 600,
    ) -> Tuple[Dict[str, Any], str]:

        for attempt in range(2):
            prompt = user_prompt
            if attempt == 1:
                prompt += "\n\nReturn ONLY valid JSON."

            response = self.complete_text(
                system_prompt, prompt, temperature, max_tokens
            )

            json_text = _extract_json_object_text(response.text)

            if not json_text:
                if attempt == 0:
                    continue
                raise Exception("Invalid JSON response")

            try:
                return json.loads(json_text), response.model
            except json.JSONDecodeError:
                if attempt == 0:
                    continue
                raise Exception("JSON parsing failed")

        raise Exception("JSON extraction failed")