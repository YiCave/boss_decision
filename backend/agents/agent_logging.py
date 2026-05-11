"""
Shared helpers for consistent per-agent debug logging (evidence shape, context).
"""
from __future__ import annotations

from typing import Any, Dict, List


def summarize_evidence(evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Count items by `source` and collect a few `type` hints per source."""
    by_source: Dict[str, int] = {}
    types_per_source: Dict[str, List[str]] = {}
    for e in evidence or []:
        if not isinstance(e, dict):
            by_source["non_dict"] = by_source.get("non_dict", 0) + 1
            continue
        src = e.get("source") or "unknown"
        by_source[src] = by_source.get(src, 0) + 1
        t = e.get("type")
        if t:
            types_per_source.setdefault(src, []).append(str(t))
    type_hints = {
        k: list(dict.fromkeys(v))[:6] for k, v in types_per_source.items()
    }
    return {
        "total": len(evidence or []),
        "by_source": by_source,
        "types_by_source": type_hints,
    }


def context_for_log(context: Dict[str, Any] | None) -> Dict[str, Any]:
    """Safe subset of context for a single log line (no large blobs)."""
    ctx = context or {}
    out: Dict[str, Any] = {
        "target_type": ctx.get("target_type"),
        "target_id": ctx.get("target_id"),
        "target_name": ctx.get("target_name"),
        "has_document": bool(ctx.get("document_summary")),
    }
    ds = ctx.get("document_summary")
    if isinstance(ds, str) and len(ds) > 100:
        out["document_preview"] = ds[:100] + "…"
    elif isinstance(ds, str):
        out["document_preview"] = ds
    return {k: v for k, v in out.items() if v is not None}
