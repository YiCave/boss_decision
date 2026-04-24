from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .memory import get_run_dir
from .memory import read_events
from .model import get_observer_chat_model

FINAL_REPORT_FILENAME = "final_report.json"
OBSERVER_SUMMARY_FILENAME = "observer_summary.md"
GRAPH_SNAPSHOT_FILENAME = "graph_snapshot.json"
STORYLINE_FILENAME = "storyline.md"


def persist_run_artifacts(
    base_dir: Path,
    session_id: str,
    query: str,
    summary: str,
    kpis: dict[str, float],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> None:
    """Persist replayable observer artifacts for a completed session.

    Args:
        base_dir: Root path for the `network_simulation_agent` package.
        session_id: Session identifier.
        query: Original user scenario.
        summary: Final observer summary text.
        kpis: Final KPI deltas dictionary.
        nodes: Final node state list.
        edges: Final edge state list.
    """
    run_dir = get_run_dir(base_dir, session_id)
    final_report = {
        "session_id": session_id,
        "query": query,
        "summary": summary,
        "kpis": kpis,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
    (run_dir / FINAL_REPORT_FILENAME).write_text(json.dumps(final_report, indent=2), encoding="utf-8")
    (run_dir / OBSERVER_SUMMARY_FILENAME).write_text(summary, encoding="utf-8")
    graph_snapshot = {"session_id": session_id, "nodes": nodes, "edges": edges}
    (run_dir / GRAPH_SNAPSHOT_FILENAME).write_text(json.dumps(graph_snapshot, indent=2), encoding="utf-8")
    storyline = build_storyline_markdown(
        base_dir=base_dir,
        session_id=session_id,
        query=query,
        final_summary=summary,
        kpis=kpis,
    )
    (run_dir / STORYLINE_FILENAME).write_text(storyline, encoding="utf-8")


def storyline_path(base_dir: Path, session_id: str) -> Path:
    """Return absolute path to storyline markdown artifact for one session."""
    return get_run_dir(base_dir, session_id) / STORYLINE_FILENAME


def build_observer_answer(base_dir: Path, session_id: str, question: str, summary: str = "") -> dict[str, Any]:
    """Build a grounded observer-chat response with event-level citations.

    Args:
        base_dir: Root path for the `network_simulation_agent` package.
        session_id: Session identifier to read artifacts from.
        question: User question submitted after simulation completion.
        summary: Optional fallback summary from in-memory session store.

    Returns:
        Dictionary with `answer` and `citations`, each citation referencing concrete event ids.
    """
    events = read_events(base_dir=base_dir, session_id=session_id, max_events=600)
    if not events:
        raise ValueError("No session events found for observer grounding.")

    matched = _select_grounding_events(question=question, events=events)
    citations = [_to_citation(item) for item in matched]
    recent_narratives = _extract_recent_narratives(events=events, max_items=6)

    final_result = _extract_final_result(events)
    answer_text = _compose_answer(
        question=question,
        final_result=final_result,
        citations=citations,
        summary=summary,
        recent_narratives=recent_narratives,
    )
    return {
        "answer": answer_text,
        "citations": citations,
    }


def build_storyline_markdown(
    base_dir: Path,
    session_id: str,
    query: str,
    final_summary: str,
    kpis: dict[str, float],
) -> str:
    """Build human-readable simulation storyline markdown from canonical events."""
    events = read_events(base_dir=base_dir, session_id=session_id, max_events=2400)
    node_turns: list[dict[str, Any]] = []
    shocks: list[dict[str, Any]] = []
    for item in events:
        event = item.get("event")
        if not isinstance(event, dict):
            continue
        if event.get("type") == "node_message":
            message = event.get("message")
            if isinstance(message, dict) and isinstance(message.get("narrative"), dict):
                node_turns.append(
                    {
                        "tick": item.get("tick"),
                        "node_id": message.get("node_id"),
                        "narrative": message.get("narrative"),
                    }
                )
        if event.get("type") == "shock_event":
            shock = event.get("shock")
            if isinstance(shock, dict):
                shocks.append({"tick": item.get("tick"), **shock})

    recent_turns = node_turns[-40:]
    revenue = float(kpis.get("revenue_delta", 0.0))
    cost = float(kpis.get("cost_delta", 0.0))
    risk = float(kpis.get("risk_delta", 0.0))
    lines = [
        "# Network Simulation Storyline",
        "",
        "## Scenario",
        query,
        "",
        "## Final Outcome",
        final_summary,
        "",
        f"- Revenue delta: {revenue:+.2%}",
        f"- Cost delta: {cost:+.2%}",
        f"- Risk delta: {risk:+.2%}",
        "",
    ]
    if shocks:
        lines.extend(["## Shock Events", ""])
        for shock in shocks[-12:]:
            lines.append(
                f"- Day {shock.get('tick', '?')}: {str(shock.get('summary', 'Shock injected')).strip()}"
            )
        lines.append("")

    lines.extend(["## Timeline Highlights", ""])
    if not recent_turns:
        lines.append("- No node-turn narrative was captured for this run.")
    else:
        for turn in recent_turns:
            narrative = turn.get("narrative") if isinstance(turn.get("narrative"), dict) else {}
            day = turn.get("tick", "?")
            headline = str(narrative.get("headline", "Node reacted to market conditions")).strip()
            summary_short = str(narrative.get("summary_short", "")).strip()
            reason = str(narrative.get("reason", "")).strip()
            watch_next = str(narrative.get("watch_next", "")).strip()
            node_id = str(turn.get("node_id", "node")).strip()
            lines.append(f"### Day {day} - {node_id}")
            lines.append(f"**{headline}**")
            if summary_short:
                lines.append(summary_short)
            if reason:
                lines.append(f"- Why: {reason}")
            if watch_next:
                lines.append(f"- Watch next: {watch_next}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def _extract_final_result(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract final simulation payload from session events."""
    for item in reversed(events):
        event = item.get("event")
        if isinstance(event, dict) and event.get("type") == "final":
            result = event.get("result")
            if isinstance(result, dict):
                return result
    return {}


def _select_grounding_events(question: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select relevant grounding events via simple keyword overlap with deterministic fallback."""
    tokens = {
        token
        for token in re.findall(r"[a-zA-Z]{3,}", question.lower())
        if token not in {"what", "when", "where", "which", "with", "from", "that", "this", "would", "could"}
    }
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in events:
        event = item.get("event")
        if not isinstance(event, dict):
            continue
        text = _event_text(event).lower()
        score = sum(1 for token in tokens if token in text)
        if score > 0:
            scored.append((score, item))

    if scored:
        scored.sort(key=lambda pair: (pair[0], pair[1].get("seq", 0)), reverse=True)
        return [pair[1] for pair in scored[:4]]

    fallback: list[dict[str, Any]] = []
    for item in reversed(events):
        event = item.get("event")
        if not isinstance(event, dict):
            continue
        if event.get("type") in {"observer_summary", "final", "node_action", "network_state"}:
            fallback.append(item)
        if len(fallback) >= 4:
            break
    return list(reversed(fallback))


def _event_text(event: dict[str, Any]) -> str:
    """Return searchable text representation for one canonical event."""
    payload_bits = [
        str(event.get("type", "")),
        str(event.get("summary", "")),
        str(event.get("message", "")),
        str(event.get("action", "")),
        str(event.get("result", "")),
    ]
    return " ".join(payload_bits)


def _to_citation(item: dict[str, Any]) -> dict[str, Any]:
    """Convert one canonical event record to API citation format."""
    event = item.get("event", {})
    event_type = event.get("type", "unknown") if isinstance(event, dict) else "unknown"
    return {
        "source": "session_state.jsonl",
        "seq": item.get("seq"),
        "tick": item.get("tick"),
        "event_type": event_type,
        "excerpt": _event_text(event if isinstance(event, dict) else {})[:240],
    }


def _compose_answer(
    question: str,
    final_result: dict[str, Any],
    citations: list[dict[str, Any]],
    summary: str,
    recent_narratives: list[dict[str, str]],
) -> str:
    """Compose grounded observer answer with intent-aware fallback and model enhancement."""
    kpis = final_result.get("kpis") if isinstance(final_result, dict) else {}
    revenue = float(kpis.get("revenue_delta", 0.0)) if isinstance(kpis, dict) else 0.0
    cost = float(kpis.get("cost_delta", 0.0)) if isinstance(kpis, dict) else 0.0
    risk = float(kpis.get("risk_delta", 0.0)) if isinstance(kpis, dict) else 0.0
    summary_text = str(final_result.get("summary") or summary or "No summary available.")
    question_text = question.strip()
    question_l = question_text.lower()
    cited_ids = ", ".join(
        f"seq:{citation.get('seq')}/tick:{citation.get('tick')}" for citation in citations[:3]
    )

    model_answer = _try_model_answer(
        question=question_text,
        summary_text=summary_text,
        revenue=revenue,
        cost=cost,
        risk=risk,
        citations=citations,
        recent_narratives=recent_narratives,
    )
    if model_answer:
        return model_answer

    if _is_greeting(question_l):
        return (
            "I am tracking this completed simulation run and can answer grounded questions.\n"
            "Try asking:\n"
            "- What happened in the last few days?\n"
            "- Which actions most influenced revenue, cost, and risk?\n"
            "- What risks should we monitor next?\n"
            f"Current trajectory: revenue {revenue:+.2%}, cost {cost:+.2%}, risk {risk:+.2%}."
        )

    if _is_status_question(question_l):
        highlight_lines = _format_narrative_highlights(recent_narratives=recent_narratives, max_items=3)
        highlights_block = "\n".join(highlight_lines) if highlight_lines else "- No recent node highlights captured."
        return (
            "Current run snapshot:\n"
            f"- Revenue: {revenue:+.2%}\n"
            f"- Cost: {cost:+.2%}\n"
            f"- Risk: {risk:+.2%}\n"
            f"- Summary: {summary_text}\n"
            "Recent highlights:\n"
            f"{highlights_block}\n"
            f"Grounding: {cited_ids if cited_ids else 'none'}."
        )

    return (
        f"Answer to: {question_text}\n"
        f"- Revenue: {revenue:+.2%}\n"
        f"- Cost: {cost:+.2%}\n"
        f"- Risk: {risk:+.2%}\n"
        f"- Observer summary: {summary_text}\n"
        f"- Grounding: {cited_ids if cited_ids else 'none'}."
    )


def _extract_recent_narratives(events: list[dict[str, Any]], max_items: int = 6) -> list[dict[str, str]]:
    """Extract recent node narratives for observer-chat context."""
    rows: list[dict[str, str]] = []
    for item in events:
        event = item.get("event")
        if not isinstance(event, dict) or event.get("type") != "node_message":
            continue
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        narrative = message.get("narrative")
        if not isinstance(narrative, dict):
            continue
        rows.append(
            {
                "tick": str(item.get("tick", "?")),
                "node_id": str(message.get("node_id", "node")),
                "headline": str(narrative.get("headline", "")),
                "summary_short": str(narrative.get("summary_short", "")),
            }
        )
    return rows[-max_items:]


def _is_greeting(question_l: str) -> bool:
    """Return true when user input is mainly a greeting or acknowledgement."""
    compact = re.sub(r"[^a-z ]+", " ", question_l).strip()
    if compact in {"hi", "hello", "hey", "yo", "thanks", "thank you"}:
        return True
    tokens = [token for token in compact.split() if token]
    return len(tokens) <= 2 and any(token in {"hi", "hello", "hey"} for token in tokens)


def _is_status_question(question_l: str) -> bool:
    """Return true for broad status/progress questions."""
    return any(
        phrase in question_l
        for phrase in {"what is happening", "what's happening", "status", "what happened", "current situation"}
    )


def _format_narrative_highlights(recent_narratives: list[dict[str, str]], max_items: int = 3) -> list[str]:
    """Format recent node highlights into concise lines."""
    rows = recent_narratives[-max_items:]
    lines: list[str] = []
    for row in rows:
        lines.append(
            f"- Day {row.get('tick', '?')} {row.get('node_id', 'node')}: "
            f"{row.get('headline', 'Node update')} - {row.get('summary_short', '')}"
        )
    return lines


def _try_model_answer(
    question: str,
    summary_text: str,
    revenue: float,
    cost: float,
    risk: float,
    citations: list[dict[str, Any]],
    recent_narratives: list[dict[str, str]],
) -> str | None:
    """Attempt model-generated observer answer grounded on run evidence."""
    model = get_observer_chat_model()
    if model is None:
        return None

    citations_pack = [
        {
            "seq": row.get("seq"),
            "tick": row.get("tick"),
            "event_type": row.get("event_type"),
            "excerpt": row.get("excerpt"),
        }
        for row in citations[:5]
    ]
    prompt = (
        "You are the observer for a completed network simulation run.\n"
        "Answer in plain business language for non-technical users.\n"
        "Rules:\n"
        "- Be concise and directly answer the user question.\n"
        "- Use evidence from provided citations/highlights only.\n"
        "- If user input is a greeting, acknowledge briefly and offer 3 useful follow-up questions.\n"
        "- Use markdown bullets when listing points.\n"
        "- Do not mention internal API/events/schema.\n\n"
        f"User question:\n{question}\n\n"
        "Run summary:\n"
        f"- Observer summary: {summary_text}\n"
        f"- Revenue delta: {revenue:+.2%}\n"
        f"- Cost delta: {cost:+.2%}\n"
        f"- Risk delta: {risk:+.2%}\n\n"
        f"Recent node highlights:\n{json.dumps(recent_narratives, ensure_ascii=True)}\n\n"
        f"Grounding citations:\n{json.dumps(citations_pack, ensure_ascii=True)}"
    )
    try:
        response = model.invoke(prompt)
    except Exception:
        return None

    content = getattr(response, "content", response)
    if isinstance(content, list):
        content = "".join(
            str(item.get("text", "")) if isinstance(item, dict) else str(item)
            for item in content
        )
    text = str(content).strip()
    return text[:2200] if text else None
