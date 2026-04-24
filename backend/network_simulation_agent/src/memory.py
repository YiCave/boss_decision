from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


SESSION_STATE_SCHEMA_VERSION = "2.0"


def build_session_id() -> str:
    """Generate a unique session id with UTC timestamp and short random suffix."""
    return f"netsim_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"


def get_run_dir(base_dir: Path, session_id: str) -> Path:
    """Create (if needed) and return the per-session run directory path."""
    run_dir = base_dir / "runs" / session_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def session_state_path(base_dir: Path, session_id: str) -> Path:
    """Return the absolute JSONL file path used to persist stream events."""
    return get_run_dir(base_dir, session_id) / "session_state.jsonl"


def append_event(base_dir: Path, session_id: str, event: dict[str, Any]) -> None:
    """Append one JSON-serialized event line to the session state file."""
    target = session_state_path(base_dir, session_id)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")


def read_events(base_dir: Path, session_id: str, max_events: int = 200) -> list[dict[str, Any]]:
    """Read the latest events from a session state file.

    Args:
        base_dir: Root directory for the network simulation agent package.
        session_id: Session identifier for the run.
        max_events: Maximum number of events to return from the file tail.

    Returns:
        Chronological list of parsed JSON objects. Malformed lines are skipped.
    """
    target = session_state_path(base_dir, session_id)
    if not target.exists():
        return []

    with target.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    parsed: list[dict[str, Any]] = []
    for line in lines[-max_events:]:
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            parsed.append(item)
    return parsed


def build_node_context(base_dir: Path, session_id: str, node_id: str, max_events: int = 60) -> dict[str, Any]:
    """Build a concise shared context payload for one node LLM.

    Args:
        base_dir: Root directory for the network simulation agent package.
        session_id: Session identifier for the run.
        node_id: Node id requesting context.
        max_events: Event window size used to summarize recent world state.

    Returns:
        Dictionary with `latest_shared_state`, `recent_events`, and `node_timeline` fields.
    """
    events = read_events(base_dir=base_dir, session_id=session_id, max_events=max_events)
    latest_shared_state: dict[str, Any] = {}
    recent_events: list[dict[str, Any]] = []
    node_timeline: list[dict[str, Any]] = []

    for item in events:
        shared = item.get("shared_state")
        if isinstance(shared, dict):
            latest_shared_state = shared
        event = item.get("event")
        if isinstance(event, dict):
            recent_events.append(
                {
                    "seq": item.get("seq"),
                    "tick": item.get("tick"),
                    "type": event.get("type"),
                    "summary": event.get("summary") or event.get("message"),
                }
            )
            if event.get("type") == "node_action":
                action = event.get("action")
                if isinstance(action, dict) and (
                    action.get("source_node_id") == node_id or action.get("target_node_id") == node_id
                ):
                    node_timeline.append(action)
            if event.get("type") == "node_message":
                msg = event.get("message")
                if isinstance(msg, dict) and msg.get("node_id") == node_id:
                    node_timeline.append(msg)

    return {
        "schema_version": SESSION_STATE_SCHEMA_VERSION,
        "session_id": session_id,
        "node_id": node_id,
        "latest_shared_state": latest_shared_state,
        "recent_events": recent_events[-15:],
        "node_timeline": node_timeline[-20:],
    }
