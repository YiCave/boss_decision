from __future__ import annotations

import random
from pathlib import Path
from typing import Any
from typing import AsyncIterator

from .memory import SESSION_STATE_SCHEMA_VERSION
from .memory import append_event
from .memory import build_session_id
from .memory import get_run_dir
from .model import get_observer_chat_model
from .observer import persist_run_artifacts
from .orchestrator import NetworkOrchestrator
from .rules import validate_action
from .schema import NetworkSimulatorRequest
from .schema import ShockEvent
from .stream_adapter import make_event
from .stream_adapter import progress_event
from .stream_adapter import status_event

NODE_STATUSES = ["stable", "active", "strained", "watch"]


class SessionStore:
    """In-memory run store for queued shocks and observer reports."""

    def __init__(self) -> None:
        """Initialize per-session containers."""
        self.shocks_by_session: dict[str, list[ShockEvent]] = {}
        self.observer_reports: dict[str, str] = {}

    def queue_shock(self, session_id: str, shock: ShockEvent) -> None:
        """Queue a shock event to be consumed on the next tick."""
        self.shocks_by_session.setdefault(session_id, []).append(shock)

    def pop_shocks(self, session_id: str) -> list[ShockEvent]:
        """Return and clear all queued shocks for one session."""
        queued = self.shocks_by_session.get(session_id, [])
        self.shocks_by_session[session_id] = []
        return queued

    def set_observer_report(self, session_id: str, report: str) -> None:
        """Persist latest observer summary text for post-run chat."""
        self.observer_reports[session_id] = report

    def get_observer_report(self, session_id: str) -> str | None:
        """Fetch observer summary text for one session."""
        return self.observer_reports.get(session_id)


SESSION_STORE = SessionStore()


class NetworkSimulationEngine:
    """Authoritative network engine with LLM-driven world building and node turns."""

    def __init__(self, request: NetworkSimulatorRequest, session_id: str | None = None) -> None:
        """Create simulation session state and bootstrap world graph."""
        self.request = request
        self.session_id = session_id or build_session_id()
        self.rng = random.Random(request.seed or 7)
        self.base_dir = Path(__file__).resolve().parents[2] / "network_simulation_agent"
        get_run_dir(self.base_dir, self.session_id)
        self.event_seq = 0
        self.recent_llm_events: list[dict[str, Any]] = []
        self.orchestrator = NetworkOrchestrator(request=request, rng=self.rng)
        self.nodes, self.edges = self.orchestrator.build_world()
        self.kpis = {
            "revenue_delta": 0.0,
            "cost_delta": 0.0,
            "risk_delta": 0.0,
        }

    def _node_lookup(self) -> dict[str, dict[str, Any]]:
        """Build in-memory lookup table for nodes by id."""
        return {str(node["node_id"]): node for node in self.nodes}

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        """Clamp numeric values to a bounded range."""
        return max(lo, min(hi, value))

    def _action_effects(self, action_type: str) -> dict[str, float]:
        """Return deterministic KPI deltas associated with action types."""
        return {
            "observe": {"revenue_delta": 0.001, "cost_delta": 0.0, "risk_delta": -0.001},
            "message": {"revenue_delta": 0.0015, "cost_delta": 0.0005, "risk_delta": -0.0008},
            "price_adjust": {"revenue_delta": 0.005, "cost_delta": 0.0015, "risk_delta": 0.002},
            "budget_shift": {"revenue_delta": 0.0025, "cost_delta": -0.0015, "risk_delta": 0.001},
            "negotiate_supply": {"revenue_delta": 0.002, "cost_delta": -0.0035, "risk_delta": -0.0005},
            "community_campaign": {"revenue_delta": 0.002, "cost_delta": 0.003, "risk_delta": -0.002},
            "risk_mitigation": {"revenue_delta": 0.001, "cost_delta": 0.001, "risk_delta": -0.004},
            "wait": {"revenue_delta": -0.0008, "cost_delta": 0.0, "risk_delta": 0.0008},
        }.get(action_type, {"revenue_delta": 0.0, "cost_delta": 0.0, "risk_delta": 0.0})

    def _apply_kpi_delta(self, delta: dict[str, float]) -> None:
        """Accumulate KPI deltas and keep values in stable range."""
        self.kpis["revenue_delta"] = round(self._clamp(self.kpis["revenue_delta"] + delta["revenue_delta"], -1.0, 1.0), 4)
        self.kpis["cost_delta"] = round(self._clamp(self.kpis["cost_delta"] + delta["cost_delta"], -1.0, 1.0), 4)
        self.kpis["risk_delta"] = round(self._clamp(self.kpis["risk_delta"] + delta["risk_delta"], -1.0, 1.0), 4)

    def _apply_shock(self, shock: ShockEvent) -> None:
        """Apply queued shock to selected nodes and aggregate KPIs."""
        severity = self._clamp(float(shock.severity), 0.0, 1.0)
        target_ids = set(shock.targets)
        for node in self.nodes:
            if target_ids and str(node.get("node_id")) not in target_ids:
                continue
            node["influence"] = round(self._clamp(float(node["influence"]) - (0.06 * severity), 0.0, 1.0), 3)
            node["status"] = "strained" if severity >= 0.5 else "watch"
        self._apply_kpi_delta(
            {
                "revenue_delta": round(-0.01 * severity, 4),
                "cost_delta": round(0.012 * severity, 4),
                "risk_delta": round(0.018 * severity, 4),
            }
        )

    def _resolve_action(self, action: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """Validate and apply one action, returning action and optional rejection metadata."""
        node_ids = {str(node["node_id"]) for node in self.nodes}
        is_valid, reason = validate_action(action, node_ids=node_ids)
        if not is_valid:
            return action, {"status": "rejected", "reason": reason, "action": action}

        source_id = str(action["source_node_id"])
        source = self._node_lookup().get(source_id)
        if source:
            source["status"] = self.rng.choice(NODE_STATUSES)
            source["influence"] = round(self._clamp(float(source["influence"]) + self.rng.uniform(-0.03, 0.03), 0.0, 1.0), 3)
        self._apply_kpi_delta(self._action_effects(str(action["action_type"])))
        return action, {}

    def _update_edge(self, tick: int, source_id: str | None = None, target_id: str | None = None) -> dict[str, Any]:
        """Apply edge weight drift, prioritizing links touched by current action."""
        candidate_edges = self.edges
        if source_id:
            linked = [edge for edge in self.edges if edge["source"] == source_id or edge["target"] == source_id]
            if linked:
                candidate_edges = linked
        if source_id and target_id:
            direct = [edge for edge in candidate_edges if edge["source"] == source_id and edge["target"] == target_id]
            if direct:
                candidate_edges = direct
        touched = self.rng.choice(candidate_edges)
        touched["weight"] = round(self._clamp(float(touched["weight"]) + self.rng.uniform(-0.08, 0.08), 0.05, 1.0), 3)
        touched["last_tick"] = tick
        return touched

    def _llm_state_digest(self, tick: int) -> dict[str, Any]:
        """Build compact shared context designed for node LLM consumption."""
        node_status_counts: dict[str, int] = {status: 0 for status in NODE_STATUSES}
        for node in self.nodes:
            node_status_counts[str(node["status"])] += 1
        top_edges = sorted(self.edges, key=lambda edge: edge["weight"], reverse=True)[:6]
        dominant_links = [
            f"{edge['source']} -> {edge['target']} ({edge['edge_type']}, w={edge['weight']:.2f})" for edge in top_edges
        ]
        summary = (
            f"Tick {tick}/{self.request.max_ticks}. Revenue {self.kpis['revenue_delta']:+.2%}, "
            f"Cost {self.kpis['cost_delta']:+.2%}, Risk {self.kpis['risk_delta']:+.2%}. "
            f"Status distribution: {node_status_counts}."
        )
        return {
            "summary": summary,
            "node_status_counts": node_status_counts,
            "dominant_links": dominant_links,
            "kpis": self.kpis.copy(),
            "edge_semantics": {
                "transaction": "commercial flow between parties",
                "influence": "behavior or decision pressure signal",
                "trust": "relationship confidence strength",
                "dependency": "operational reliance and bottleneck risk",
                "information": "news or narrative propagation channel",
            },
            "world_assumptions": self.orchestrator.assumptions[:8],
        }

    def _append_event(self, event: dict[str, Any], tick: int | None = None) -> None:
        """Append canonical event record into `session_state.jsonl`."""
        self.event_seq += 1
        payload = dict(event)
        canonical = {
            "schema_version": SESSION_STATE_SCHEMA_VERSION,
            "session_id": self.session_id,
            "seq": self.event_seq,
            "type": payload.get("type", "unknown"),
            "tick": tick,
            "ts": payload.get("ts"),
            "event": payload,
            "shared_state": {
                "query": self.request.query,
                "scenario_id": self.request.scenario_id,
                "seed": self.request.seed,
                "max_ticks": self.request.max_ticks,
                "kpis": self.kpis.copy(),
            },
            "llm_context": self._llm_state_digest(tick=tick or 0),
        }
        append_event(self.base_dir, self.session_id, canonical)
        self.recent_llm_events.append(
            {
                "tick": tick,
                "type": payload.get("type"),
                "summary": payload.get("summary") or payload.get("message"),
            }
        )
        self.recent_llm_events = self.recent_llm_events[-80:]

    def _observer_summary_text(self) -> str:
        """Build scenario-aware observer summary with model synthesis and deterministic fallback."""
        revenue = float(self.kpis.get("revenue_delta", 0.0))
        cost = float(self.kpis.get("cost_delta", 0.0))
        risk = float(self.kpis.get("risk_delta", 0.0))
        scenario = str(self.request.query).strip()
        risk_signal = "contained" if risk < 0.05 else "elevated"

        model = get_observer_chat_model()
        if model is not None:
            prompt = (
                "You are the final observer for a completed business network simulation.\n"
                "Write a concise final summary (2-3 sentences) for non-technical users.\n"
                "Rules:\n"
                "- Directly address the scenario in plain business language.\n"
                "- Include revenue_delta, cost_delta, and risk_delta exactly once each.\n"
                "- Provide one concrete next-step recommendation.\n"
                "- Do not assume this is a pricing scenario unless explicitly stated.\n"
                "- Do not use markdown.\n\n"
                f"Scenario query: {scenario}\n"
                f"Final KPI deltas: revenue_delta={revenue:+.2%}, cost_delta={cost:+.2%}, risk_delta={risk:+.2%}\n"
                f"Recent events snapshot: {self.recent_llm_events[-8:]}"
            )
            try:
                response = model.invoke(prompt)
                content = getattr(response, "content", response)
                if isinstance(content, list):
                    content = "".join(
                        str(item.get("text", "")) if isinstance(item, dict) else str(item) for item in content
                    )
                text = str(content).strip()
                if text:
                    return text[:1600]
            except Exception:
                pass

        trend = "improving" if revenue > 0 and risk <= 0 else "mixed"
        return (
            f"Observer: for scenario \"{scenario}\", the network outcome is {trend}, with "
            f"revenue_delta={revenue:+.2%}, cost_delta={cost:+.2%}, risk_delta={risk:+.2%}. "
            f"Operational risk is {risk_signal}; recommended strategy is a staged rollout with clear guardrails, "
            "tight supplier coordination, and retention-focused communication validated each tick."
        )

    def _day_summary_from_narratives(self, tick: int, tick_narratives: list[dict[str, str]]) -> str:
        """Build a plain-language day summary grounded in node LLM narratives for the current tick."""
        if not tick_narratives:
            return f"Day {tick}: no major agent actions were recorded."

        headline = tick_narratives[0].get("headline", "").strip() or "Agents reacted to market conditions."
        snippets: list[str] = []
        for item in tick_narratives[:3]:
            label = item.get("label", "Node").strip()
            summary = item.get("summary_short", "").strip()
            if summary:
                snippets.append(f"{label}: {summary}")
        if not snippets:
            return f"Day {tick}: {headline}"
        return f"Day {tick}: {headline} Key moves: " + " | ".join(snippets)

    async def run_stream(self) -> AsyncIterator[dict[str, Any]]:
        """Run simulation tick loop and stream lifecycle/action/state events."""
        header = make_event(
            "status",
            session_id=self.session_id,
            message="Network simulation stream started.",
            query=self.request.query,
            scenario_id=self.request.scenario_id,
            seed=self.request.seed,
            run_header={
                "session_id": self.session_id,
                "seed": self.request.seed,
                "model": "phase3-llm-node-orchestrator",
                "prompt_version": "network_v3",
                "start_ts": None,
            },
        )
        if isinstance(header.get("run_header"), dict):
            header["run_header"]["start_ts"] = header.get("ts")
        self._append_event(header, tick=0)
        yield header

        for tick in range(1, self.request.max_ticks + 1):
            progress = progress_event(tick=tick, max_ticks=self.request.max_ticks, summary=f"Tick {tick} executing.")
            progress["session_id"] = self.session_id
            self._append_event(progress, tick=tick)
            yield progress
            tick_narratives: list[dict[str, str]] = []

            for shock in SESSION_STORE.pop_shocks(self.session_id):
                self._apply_shock(shock)
                shock_event = make_event(
                    "shock_event",
                    session_id=self.session_id,
                    tick=tick,
                    shock=shock.model_dump(mode="json"),
                )
                self._append_event(shock_event, tick=tick)
                yield shock_event

            node_lookup = self._node_lookup()
            actor_ids = self.orchestrator.actor_order_for_tick(
                tick=tick,
                node_ids=[str(node["node_id"]) for node in self.nodes],
            )
            for actor_id in actor_ids:
                actor = node_lookup.get(actor_id)
                if actor is None:
                    continue
                action_payload, node_narrative = await self.orchestrator.build_node_turn(
                    tick=tick,
                    node=actor,
                    nodes=self.nodes,
                    edges=self.edges,
                    kpis=self.kpis.copy(),
                    recent_events=self.recent_llm_events,
                )
                resolved_action, rejection = self._resolve_action(action_payload)

                action_event = make_event(
                    "node_action",
                    session_id=self.session_id,
                    tick=tick,
                    action=resolved_action,
                )
                self._append_event(action_event, tick=tick)
                yield action_event

                if rejection:
                    rejection_event = make_event(
                        "node_message",
                        session_id=self.session_id,
                        tick=tick,
                        message={
                            "node_id": str(resolved_action.get("source_node_id", "unknown")),
                            "text": f"Action rejected by rules: {rejection.get('reason', 'unknown reason')}",
                        },
                    )
                    self._append_event(rejection_event, tick=tick)
                    yield rejection_event

                message_event = make_event(
                    "node_message",
                    session_id=self.session_id,
                    tick=tick,
                    message={
                        "node_id": str(resolved_action.get("source_node_id", actor_id)),
                        "text": str(node_narrative.get("summary_short", "")),
                        "narrative": node_narrative,
                    },
                )
                self._append_event(message_event, tick=tick)
                yield message_event
                tick_narratives.append(
                    {
                        "label": str(actor.get("label", actor_id)),
                        "headline": str(node_narrative.get("headline", "")),
                        "summary_short": str(node_narrative.get("summary_short", "")),
                    }
                )

                touched_edge = self._update_edge(
                    tick=tick,
                    source_id=str(resolved_action.get("source_node_id", "")),
                    target_id=str(resolved_action.get("target_node_id", "")) or None,
                )
                edge_event = make_event(
                    "edge_update",
                    session_id=self.session_id,
                    tick=tick,
                    edge=touched_edge,
                )
                self._append_event(edge_event, tick=tick)
                yield edge_event

            network_state = make_event(
                "network_state",
                session_id=self.session_id,
                tick=tick,
                state={
                    "tick": tick,
                    "max_ticks": self.request.max_ticks,
                    "nodes": self.nodes,
                    "edges": self.edges,
                    "kpis": self.kpis.copy(),
                    "llm_context": self._llm_state_digest(tick=tick),
                    "day_summary_ai": self._day_summary_from_narratives(tick=tick, tick_narratives=tick_narratives),
                },
            )
            self._append_event(network_state, tick=tick)
            yield network_state

        summary_text = self._observer_summary_text()
        observer_summary = make_event(
            "observer_summary",
            session_id=self.session_id,
            summary=summary_text,
            confidence=0.74,
        )
        self._append_event(observer_summary, tick=self.request.max_ticks)
        SESSION_STORE.set_observer_report(self.session_id, summary_text)
        yield observer_summary

        final_event = make_event(
            "final",
            session_id=self.session_id,
            result={
                "session_id": self.session_id,
                "query": self.request.query,
                "max_ticks": self.request.max_ticks,
                "summary": summary_text,
                "kpis": self.kpis.copy(),
            },
        )
        self._append_event(final_event, tick=self.request.max_ticks)
        persist_run_artifacts(
            base_dir=self.base_dir,
            session_id=self.session_id,
            query=self.request.query,
            summary=summary_text,
            kpis=self.kpis.copy(),
            nodes=self.nodes,
            edges=self.edges,
        )
        yield final_event

        done = status_event("Network simulation stream completed.")
        done["type"] = "done"
        done["session_id"] = self.session_id
        self._append_event(done, tick=self.request.max_ticks)
        yield done

    async def run_to_completion(self) -> dict[str, Any]:
        """Consume stream to completion and return final result payload."""
        final_payload: dict[str, Any] = {"session_id": self.session_id}
        async for event in self.run_stream():
            if event.get("type") == "final":
                result = event.get("result")
                if isinstance(result, dict):
                    final_payload.update(result)
        return final_payload
