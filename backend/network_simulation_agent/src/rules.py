from __future__ import annotations

from typing import Any

LEGAL_ACTION_TYPES = {
    "observe",
    "message",
    "price_adjust",
    "budget_shift",
    "negotiate_supply",
    "community_campaign",
    "risk_mitigation",
    "wait",
}


def _as_float(value: Any, default: float) -> float:
    """Best-effort float conversion with a deterministic fallback value."""
    try:
        return float(value)
    except Exception:
        return default


def _clean_action_type(value: Any) -> str:
    """Normalize action type strings so free-form model outputs map to legal actions."""
    token = str(value or "").strip().lower().replace(" ", "_")
    alias_map = {
        "raise_price": "price_adjust",
        "pricing_change": "price_adjust",
        "chat": "message",
        "talk": "message",
        "negotiate": "negotiate_supply",
        "campaign": "community_campaign",
        "mitigate_risk": "risk_mitigation",
        "no_op": "wait",
    }
    token = alias_map.get(token, token)
    if token not in LEGAL_ACTION_TYPES:
        return "observe"
    return token


def normalize_action(action: dict[str, Any], node_ids: set[str] | None = None) -> dict[str, Any]:
    """Normalize a candidate action payload into the canonical typed contract."""
    source_node_id = str(action.get("source_node_id") or action.get("source") or "").strip()
    target_node_id = action.get("target_node_id")
    if target_node_id is not None:
        target_node_id = str(target_node_id).strip() or None

    payload = action.get("payload")
    if not isinstance(payload, dict):
        payload = {"note": str(payload) if payload is not None else ""}

    normalized = {
        "action_type": _clean_action_type(action.get("action_type")),
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
        "payload": payload,
        "rationale": str(action.get("rationale") or "No rationale provided."),
        "confidence": max(0.0, min(1.0, _as_float(action.get("confidence"), 0.5))),
    }

    if node_ids is not None:
        if normalized["source_node_id"] not in node_ids:
            normalized["source_node_id"] = ""
        if normalized["target_node_id"] is not None and normalized["target_node_id"] not in node_ids:
            normalized["target_node_id"] = None
    return normalized


def validate_action(action: dict[str, Any], node_ids: set[str] | None = None) -> tuple[bool, str]:
    """Validate that a node action contains required contract fields and legal values.

    Args:
        action: Candidate action payload emitted by a node.
        node_ids: Optional set of valid node ids for source/target validation.

    Returns:
        Tuple of `(is_valid, reason)` where `reason` is `"ok"` or missing-field details.
    """
    required = {"action_type", "source_node_id", "payload", "rationale", "confidence"}
    missing = sorted(required - set(action.keys()))
    if missing:
        return False, f"missing fields: {', '.join(missing)}"

    action_type = str(action.get("action_type") or "").strip().lower()
    if action_type not in LEGAL_ACTION_TYPES:
        return False, f"invalid action_type: {action_type or 'empty'}"

    source_node_id = str(action.get("source_node_id") or "").strip()
    if not source_node_id:
        return False, "invalid source_node_id: empty"
    if node_ids is not None and source_node_id not in node_ids:
        return False, f"invalid source_node_id: {source_node_id}"

    target_node_id = action.get("target_node_id")
    if target_node_id is not None and node_ids is not None and str(target_node_id) not in node_ids:
        return False, f"invalid target_node_id: {target_node_id}"

    payload = action.get("payload")
    if not isinstance(payload, dict):
        return False, "invalid payload: must be object"

    confidence = _as_float(action.get("confidence"), -1.0)
    if confidence < 0.0 or confidence > 1.0:
        return False, "invalid confidence: expected range [0,1]"
    return True, "ok"
