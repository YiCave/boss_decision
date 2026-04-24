import json
import re
from typing import Any


def extract_text_content(raw_content: Any) -> str:
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, list):
        chunks: list[str] = []
        for item in raw_content:
            if isinstance(item, str):
                chunks.append(item)
                continue
            if isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    chunks.append(text_value)
        return "\n".join(chunks)
    return ""


def _try_parse_json(candidate: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None
    return None


def _extract_brace_objects(text: str) -> list[str]:
    candidates: list[str] = []
    start_idx = -1
    depth = 0
    in_string = False
    escaped = False

    for idx, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            if depth == 0:
                start_idx = idx
            depth += 1
            continue

        if ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start_idx >= 0:
                candidates.append(text[start_idx : idx + 1])
                start_idx = -1
    return candidates


def extract_json_block(text: str) -> dict[str, Any] | None:
    # Accept raw JSON, fenced JSON, or first valid JSON object inside mixed text.
    parsed = _try_parse_json(text.strip())
    if parsed is not None:
        return parsed

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        parsed = _try_parse_json(fenced.group(1).strip())
        if parsed is not None:
            return parsed

    for candidate in _extract_brace_objects(text):
        parsed = _try_parse_json(candidate)
        if parsed is not None:
            return parsed

    return None


def fallback_parse_decision(query: str) -> dict[str, Any]:
    # This parser intentionally stays narrow; it only covers the MVP fields from plan.md.
    lowered = query.lower()

    decision_type = "unknown"
    if "price" in lowered and ("increase" in lowered or "raise" in lowered):
        decision_type = "price_increase"
    elif "price" in lowered and ("decrease" in lowered or "lower" in lowered or "discount" in lowered):
        decision_type = "price_decrease"
    elif "launch" in lowered or "new product" in lowered:
        decision_type = "product_launch"

    delta_match = re.search(
        r"([+-]?\d+(?:\.\d+)?)\s*(%|percent|pct|points|bps|basis points|\$|dollars)?",
        query,
        flags=re.IGNORECASE,
    )
    delta_value: float | None = None
    delta_unit: str | None = None
    if delta_match:
        delta_value = float(delta_match.group(1))
        unit = (delta_match.group(2) or "").lower().strip()
        if unit in {"%", "percent", "pct"}:
            delta_unit = "percent"
        elif unit in {"points"}:
            delta_unit = "points"
        elif unit in {"bps", "basis points"}:
            delta_unit = "bps"
        elif unit in {"$", "dollars"}:
            delta_unit = "dollars"

    time_horizon = "unspecified"
    horizon_match = re.search(
        r"(next\s+quarter|next\s+month|next\s+year|this\s+quarter|this\s+month|this\s+year|in\s+\d+\s+(?:day|days|week|weeks|month|months|year|years))",
        lowered,
    )
    if horizon_match:
        time_horizon = horizon_match.group(1)

    target_segments: list[str] = []
    segment_matches = re.findall(r"for\s+([a-z0-9,\s\-]+)", lowered)
    if segment_matches:
        for segment in re.split(r",| and ", segment_matches[0]):
            cleaned = segment.strip()
            if cleaned:
                target_segments.append(cleaned)

    return {
        "decision_type": decision_type,
        "delta_value": delta_value,
        "delta_unit": delta_unit,
        "time_horizon": time_horizon,
        "target_segments": target_segments,
        "confidence": 0.25,
        "assumptions": ["Fallback parser used because model output was not valid JSON."],
    }


def normalize_decision(data: dict[str, Any]) -> dict[str, Any]:
    # Coerce mixed parser outputs into the typed state shape expected by downstream nodes.
    return {
        "decision_type": str(data.get("decision_type") or "unknown"),
        "delta_value": float(data["delta_value"]) if isinstance(data.get("delta_value"), (int, float)) else None,
        "delta_unit": str(data["delta_unit"]) if isinstance(data.get("delta_unit"), str) else None,
        "time_horizon": str(data.get("time_horizon") or "unspecified"),
        "target_segments": [str(item) for item in data.get("target_segments", []) if isinstance(item, str)],
        "confidence": float(data["confidence"]) if isinstance(data.get("confidence"), (int, float)) else 0.0,
        "assumptions": [str(item) for item in data.get("assumptions", []) if isinstance(item, str)],
    }
