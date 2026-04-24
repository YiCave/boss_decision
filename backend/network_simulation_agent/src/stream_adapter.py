from __future__ import annotations

from datetime import datetime
from typing import Any

from .schema import NETWORK_EVENT_TYPES


def make_event(event_type: str, **payload: Any) -> dict[str, Any]:
    """Create a typed stream event with server-side UTC timestamp.

    Raises:
        ValueError: If `event_type` is not part of `NETWORK_EVENT_TYPES`.
    """
    if event_type not in NETWORK_EVENT_TYPES:
        raise ValueError(f"Unknown network event type: {event_type}")
    return {"type": event_type, "ts": datetime.utcnow().isoformat(), **payload}


def status_event(message: str) -> dict[str, Any]:
    """Create a standard status event with human-readable progress text."""
    return make_event("status", message=message)


def progress_event(tick: int, max_ticks: int, summary: str) -> dict[str, Any]:
    """Create a structured per-tick progress event for UI progress rendering."""
    return make_event("progress", tick=tick, max_ticks=max_ticks, summary=summary)


def done_event() -> dict[str, Any]:
    """Create a terminal done event indicating stream completion."""
    return make_event("done")
