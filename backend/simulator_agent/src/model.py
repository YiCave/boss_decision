import os
import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


logger = logging.getLogger(__name__)

DEFAULT_SIMULATOR_MODEL = "openai:ilmu-glm-5.1"

_MODEL_CACHE: dict[str, Any] = {}
_MODEL_INIT_ATTEMPTS: set[str] = set()


def _load_env_for_simulator() -> None:
    # The backend loads `.env` via pydantic settings, but simulator nodes read os.getenv directly.
    # Load both candidate env files so provider SDKs can see API keys.
    root_backend = Path(__file__).resolve().parents[2]
    simulator_root = Path(__file__).resolve().parents[1]
    load_dotenv(root_backend / ".env", override=False)
    load_dotenv(simulator_root / ".env", override=False)

    zhipu_key = os.getenv("ZHIPU_API_KEY")
    zhipu_base_url = os.getenv("ZHIPU_BASE_URL")
    if zhipu_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = zhipu_key
    if zhipu_base_url and not os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = zhipu_base_url

    # Normalize Gemini key aliasing for provider SDK compatibility.
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key and not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = google_key

    # Normalize ZHIPU (OpenAI-compatible) keys for provider SDK compatibility.
    zhipu_key = os.getenv("ZHIPU_API_KEY")
    if zhipu_key and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = zhipu_key
    zhipu_base_url = os.getenv("ZHIPU_BASE_URL")
    if zhipu_base_url and not os.getenv("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = zhipu_base_url


def _infer_provider_default_model() -> str:
    _load_env_for_simulator()

    if os.getenv("SIMULATOR_MODEL"):
        return os.getenv("SIMULATOR_MODEL", DEFAULT_SIMULATOR_MODEL)

    if os.getenv("ZHIPU_API_KEY"):
        zhipu_model = os.getenv("ZHIPU_MODEL", "ilmu-glm-5.1")
        return zhipu_model if ":" in zhipu_model else f"openai:{zhipu_model}"

    # Keep defaults aligned with whichever provider key is configured.
    if os.getenv("ZHIPU_API_KEY"):
        zhipu_model = os.getenv("ZHIPU_MODEL") or os.getenv("LLM_MODEL") or "ilmu-glm-5.1"
        return zhipu_model if ":" in zhipu_model else f"openai:{zhipu_model}"
    if os.getenv("OPENAI_API_KEY"):
        llm_model = os.getenv("LLM_MODEL", "ilmu-glm-5.1")
        return llm_model if ":" in llm_model else f"openai:{llm_model}"
    if os.getenv("GOOGLE_API_KEY"):
        return DEFAULT_SIMULATOR_MODEL
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic:claude-3-5-sonnet-latest"
    return DEFAULT_SIMULATOR_MODEL


def _get_model(model_name: str) -> Any:
    global _MODEL_CACHE
    global _MODEL_INIT_ATTEMPTS

    _load_env_for_simulator()

    if model_name in _MODEL_INIT_ATTEMPTS:
        return _MODEL_CACHE.get(model_name)

    _MODEL_INIT_ATTEMPTS.add(model_name)
    try:
        from langchain.chat_models import init_chat_model

        kwargs: dict[str, Any] = {}
        if model_name.startswith("openai:") or ":" not in model_name:
            openai_key = os.getenv("OPENAI_API_KEY")
            openai_base = os.getenv("OPENAI_BASE_URL")
            if openai_key:
                kwargs["api_key"] = openai_key
            if openai_base:
                kwargs["base_url"] = openai_base
        _MODEL_CACHE[model_name] = init_chat_model(model=model_name, **kwargs)
    except Exception as exc:
        logger.warning("Simulator model init failed for '%s': %s", model_name, exc)
        _MODEL_CACHE[model_name] = None
    return _MODEL_CACHE[model_name]


def get_openai_compat_kwargs() -> dict[str, str]:
    """Return OpenAI-compatible connection overrides for custom gateways."""
    _load_env_for_simulator()
    kwargs: dict[str, str] = {}
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_base = os.getenv("OPENAI_BASE_URL")
    if openai_key:
        kwargs["api_key"] = openai_key
    if openai_base:
        kwargs["base_url"] = openai_base
    return kwargs


def get_parser_model() -> Any:
    return _get_model(os.getenv("PARSER_MODEL", _infer_provider_default_model()))


def get_selector_model() -> Any:
    return _get_model(os.getenv("SELECTOR_MODEL", _infer_provider_default_model()))


def get_persona_model_name() -> str:
    return os.getenv("PERSONA_MODEL", _infer_provider_default_model())


def get_branch_model() -> Any:
    return _get_model(os.getenv("BRANCH_MODEL", _infer_provider_default_model()))


def get_recommendation_model() -> Any:
    return _get_model(os.getenv("RECOMMENDATION_MODEL", _infer_provider_default_model()))
