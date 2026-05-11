from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


logger = logging.getLogger(__name__)

DEFAULT_NETWORK_MODEL = "openai:ilmu-glm-5.1"
_MODEL_CACHE: dict[str, Any] = {}
_MODEL_INIT_ATTEMPTS: set[str] = set()


def _load_env() -> None:
    """Load backend env files and normalize provider-specific key aliases."""
    backend_root = Path(__file__).resolve().parents[2]
    load_dotenv(backend_root / ".env", override=False)

    zhipu_key = os.getenv("ZHIPU_API_KEY")
    zhipu_base_url = os.getenv("ZHIPU_BASE_URL")
    if zhipu_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = zhipu_key
    if zhipu_base_url and not os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = zhipu_base_url

    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key and not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = google_key

    zhipu_key = os.getenv("ZHIPU_API_KEY")
    if zhipu_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = zhipu_key
    zhipu_base_url = os.getenv("ZHIPU_BASE_URL")
    if zhipu_base_url and not os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = zhipu_base_url


def _infer_default_model() -> str:
    """Infer a model identifier from available provider credentials."""
    _load_env()
    if os.getenv("NETWORK_SIM_MODEL"):
        return os.getenv("NETWORK_SIM_MODEL", DEFAULT_NETWORK_MODEL)
    if os.getenv("ZHIPU_API_KEY"):
        model = os.getenv("ZHIPU_MODEL", "ilmu-glm-5.1")
        zhipu_model = os.getenv("ZHIPU_MODEL") or os.getenv("LLM_MODEL") or model
        return zhipu_model if ":" in zhipu_model else f"openai:{zhipu_model}"
    if os.getenv("OPENAI_API_KEY"):
        model = os.getenv("LLM_MODEL", "ilmu-glm-5.1")
        return model if ":" in model else f"openai:{model}"
    if os.getenv("GOOGLE_API_KEY"):
        return DEFAULT_NETWORK_MODEL
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic:claude-3-5-sonnet-latest"
    return DEFAULT_NETWORK_MODEL


def _get_model(model_name: str) -> Any:
    """Initialize and cache a chat model; return `None` if initialization fails."""
    _load_env()
    if model_name in _MODEL_INIT_ATTEMPTS:
        return _MODEL_CACHE.get(model_name)
    _MODEL_INIT_ATTEMPTS.add(model_name)
    try:
        from langchain.chat_models import init_chat_model

        kwargs: dict[str, Any] = {"temperature": 0}
        if model_name.startswith("openai:") or ":" not in model_name:
            openai_key = os.getenv("OPENAI_API_KEY")
            openai_base = os.getenv("OPENAI_BASE_URL")
            if openai_key:
                kwargs["api_key"] = openai_key
            if openai_base:
                kwargs["base_url"] = openai_base
        _MODEL_CACHE[model_name] = init_chat_model(model=model_name, **kwargs)
    except Exception as exc:
        logger.warning("Network simulator model init failed for '%s': %s", model_name, exc)
        _MODEL_CACHE[model_name] = None
    return _MODEL_CACHE[model_name]


def get_world_builder_model() -> Any:
    """Return model used for generating scenario-specific nodes/edges/personas."""
    return _get_model(os.getenv("NETWORK_WORLD_MODEL", _infer_default_model()))


def get_node_turn_model() -> Any:
    """Return model used for per-node action generation."""
    return _get_model(os.getenv("NETWORK_NODE_MODEL", _infer_default_model()))


def get_observer_chat_model() -> Any:
    """Return model used for observer-chat answers."""
    return _get_model(os.getenv("NETWORK_OBSERVER_MODEL", _infer_default_model()))
