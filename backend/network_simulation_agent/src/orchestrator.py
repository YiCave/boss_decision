from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path
from typing import Any
from typing import Literal

from deepagents import create_deep_agent
from langchain.tools import tool
from pydantic import BaseModel
from pydantic import Field

from .model import get_node_turn_model
from .model import get_world_builder_model
from .rules import normalize_action
from .schema import NetworkSimulatorRequest


NODE_TYPES = ["business", "consumer", "supplier", "competitor", "community", "bank", "regulator", "platform"]
EDGE_TYPES = ["transaction", "influence", "trust", "dependency", "information"]


class WorldNodeSpec(BaseModel):
    """Structured node spec emitted by the world-builder model."""

    node_id: str
    label: str
    node_type: str
    influence: float = Field(ge=0, le=1)
    status: str = "stable"
    x: float = Field(ge=20, le=920)
    y: float = Field(ge=20, le=620)
    persona: str


class WorldEdgeSpec(BaseModel):
    """Structured edge spec emitted by the world-builder model."""

    edge_id: str
    source: str
    target: str
    edge_type: str
    weight: float = Field(ge=0, le=1)


class WorldBuildOutput(BaseModel):
    """Schema for model-generated network graph and personas."""

    nodes: list[WorldNodeSpec]
    edges: list[WorldEdgeSpec]
    assumptions: list[str] = Field(default_factory=list)


class NodeActionOutput(BaseModel):
    """Schema for model-generated node action payload."""

    action_type: str
    target_node_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    rationale: str
    confidence: float = Field(ge=0, le=1)
    message: str


class NodeNarrativeImpact(BaseModel):
    """Simple directional impact signal for non-technical UI communication."""

    direction: str
    note: str


class NodeNarrativeOutput(BaseModel):
    """Structured storytelling + business summary emitted per completed node turn."""

    headline: str
    summary_short: str
    reason: str
    watch_next: str
    confidence_band: str
    sales: NodeNarrativeImpact
    cost: NodeNarrativeImpact
    risk: NodeNarrativeImpact
    full_response_md: str


class NodeTurnOutput(BaseModel):
    """Combined typed output for one node turn."""

    action: NodeActionOutput
    narrative: NodeNarrativeOutput


class NetworkOrchestrator:
    """LLM orchestration for world building and per-node turn decisions."""

    def __init__(self, request: NetworkSimulatorRequest, rng: random.Random) -> None:
        """Store request-scoped dependencies and lazy model handles."""
        self.request = request
        self.rng = rng
        self.world_model = get_world_builder_model()
        self.node_model = get_node_turn_model()
        self._node_agent_cache: dict[str, Any] = {}
        self._context_roots = self._resolve_context_roots()
        self.personas: dict[str, str] = {}
        self.assumptions: list[str] = []

    def _resolve_context_roots(self) -> list[Path]:
        """Resolve absolute roots allowed for node-agent file reads."""
        candidates: list[Path] = []
        if self.request.data_context_path:
            root = Path(self.request.data_context_path)
            if not root.is_absolute():
                root = Path(__file__).resolve().parents[2] / root
            candidates.append(root.resolve())
        else:
            candidates.append((Path(__file__).resolve().parents[2] / "agent_docs" / "simulator").resolve())

        roots: list[Path] = []
        for item in candidates:
            if item.exists() and item.is_dir():
                roots.append(item)
        return roots

    def _extract_text_content(self, content: Any) -> str:
        """Convert model/deep-agent chunk content payloads into plain text."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, str):
                    chunks.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
            return "".join(chunks)
        return str(content) if content is not None else ""

    def _get_node_deep_agent(self, node: dict[str, Any]) -> Any | None:
        """Create/cache a deep agent for one network node persona with bounded tools."""
        if self.node_model is None:
            return None
        node_id = str(node.get("node_id", "")).strip()
        if not node_id:
            return None
        cached = self._node_agent_cache.get(node_id)
        if cached is not None:
            return cached

        persona_prompt = self.personas.get(node_id, "Act according to your role and current network pressures.")
        system_prompt = (
            "You are a node actor in a business-economic network simulation.\n"
            "Always reason in business plain language and keep outputs concise.\n"
            "Use tools when necessary for evidence.\n"
            "Write sections: Situation, Evidence, Action, Why, Watch next.\n\n"
            f"Persona guidance: {persona_prompt}"
        )
        allowed_roots = self._context_roots[:]

        @tool("read_allowed_file")
        def read_allowed_file(path: str, max_chars: int = 2400) -> str:
            """Read files from allowlisted simulation context roots only."""
            target = Path(path).resolve()
            if not any(str(target).startswith(str(root)) for root in allowed_roots):
                return f"Denied: path `{target}` is outside allowed roots."
            if not target.exists() or not target.is_file():
                return f"File not found: `{target}`."
            try:
                text = target.read_text(encoding="utf-8", errors="ignore")
                return text[: max(200, min(max_chars, 12000))]
            except Exception as exc:
                return f"Read failed: {exc}"

        @tool("internet_search")
        def internet_search(query: str, max_results: int = 3, topic: Literal["general", "news", "finance"] = "general") -> str:
            """Search web context using Tavily if enabled for this scenario."""
            if not self.request.allow_internet:
                return "Internet search disabled for this run."
            api_key = os.getenv("TAVILY_API_KEY", "").strip()
            if not api_key:
                return "TAVILY_API_KEY missing."
            try:
                from tavily import TavilyClient

                client = TavilyClient(api_key=api_key)
                result = client.search(query=query, max_results=max(1, min(max_results, 6)), topic=topic)
                rows: list[str] = []
                for item in result.get("results", [])[:6]:
                    title = str(item.get("title", "")).strip()
                    url = str(item.get("url", "")).strip()
                    snippet = str(item.get("content", "")).replace("\n", " ").strip()
                    rows.append(f"- {title} ({url}): {snippet[:180]}")
                return "\n".join(rows) if rows else "No search results."
            except Exception as exc:
                return f"Search failed: {exc}"

        tools: list[Any] = [read_allowed_file]
        if self.request.allow_internet:
            tools.append(internet_search)
        try:
            agent = create_deep_agent(model=self.node_model, system_prompt=system_prompt, tools=tools)
            self._node_agent_cache[node_id] = agent
            return agent
        except Exception:
            return None

    async def _collect_node_deep_agent_text(self, agent: Any, prompt: str) -> str:
        """Collect final textual transcript from deep-agent stream."""
        collected = ""
        latest_values: dict[str, Any] | None = None
        async for part in agent.astream(
            {"messages": [{"role": "user", "content": prompt}]},
            stream_mode=["messages", "values"],
            version="v2",
        ):
            if not isinstance(part, dict):
                continue
            if part.get("type") == "messages":
                data = part.get("data")
                if not isinstance(data, (tuple, list)) or not data:
                    continue
                message_chunk = data[0]
                text = self._extract_text_content(getattr(message_chunk, "content", ""))
                if text:
                    collected += text
            elif part.get("type") == "values":
                values = part.get("data")
                if isinstance(values, dict):
                    latest_values = values

        if not collected and latest_values:
            messages = latest_values.get("messages")
            if isinstance(messages, list):
                for item in reversed(messages):
                    content = getattr(item, "content", item.get("content") if isinstance(item, dict) else "")
                    extracted = self._extract_text_content(content)
                    if extracted.strip():
                        collected = extracted
                        break
        return collected

    def build_world(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Build initial nodes/edges from LLM output, with deterministic fallback."""
        llm_result = self._build_world_with_llm()
        if llm_result:
            nodes, edges = llm_result
            if nodes and edges:
                return nodes, edges
        return self._fallback_world()

    def actor_order_for_tick(self, tick: int, node_ids: list[str]) -> list[str]:
        """Choose deterministic actor subset for one tick to keep latency stable."""
        if not node_ids:
            return []
        window = max(3, min(8, max(1, len(node_ids) // 4)))
        start = (tick * window) % len(node_ids)
        ordered = node_ids[start:] + node_ids[:start]
        return ordered[:window]

    async def build_node_turn(
        self,
        tick: int,
        node: dict[str, Any],
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        kpis: dict[str, float],
        recent_events: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Generate one node action and companion narrative from LLM or fallback."""
        action_output = await self._build_node_turn_with_llm(
            tick=tick,
            node=node,
            nodes=nodes,
            edges=edges,
            kpis=kpis,
            recent_events=recent_events,
        )
        node_ids = {str(item.get("node_id", "")) for item in nodes}
        source_id = str(node.get("node_id", ""))

        if action_output is None:
            fallback = self._fallback_node_turn(node=node, nodes=nodes, tick=tick)
            action = normalize_action(
                {
                    "action_type": fallback["action_type"],
                    "source_node_id": source_id,
                    "target_node_id": fallback["target_node_id"],
                    "payload": fallback["payload"],
                    "rationale": fallback["rationale"],
                    "confidence": fallback["confidence"],
                },
                node_ids=node_ids,
            )
            return action, self._fallback_node_narrative(node=node, fallback=fallback, kpis=kpis, tick=tick)

        action = normalize_action(
            {
                "action_type": action_output.action.action_type,
                "source_node_id": source_id,
                "target_node_id": action_output.action.target_node_id,
                "payload": action_output.action.payload,
                "rationale": action_output.action.rationale,
                "confidence": action_output.action.confidence,
            },
            node_ids=node_ids,
        )
        narrative = self._normalize_narrative(
            node=node,
            tick=tick,
            kpis=kpis,
            action=action,
            narrative=action_output.narrative.model_dump(mode="json"),
            fallback_message=action_output.action.message,
        )
        return action, narrative

    def _build_world_with_llm(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
        """Ask the world-builder LLM to generate nodes, edges, and persona text."""
        if self.world_model is None:
            return None
        node_count = max(self.request.min_nodes, min(self.request.max_nodes, 24))
        context_snippets = self._read_context_snippets(max_chars=6000)
        web_snippets = self._search_snippets(self.request.query) if self.request.allow_internet else []

        prompt = (
            "You are building a business-economic simulation network.\n"
            f"Scenario query: {self.request.query}\n"
            f"Target node count: {node_count}\n"
            "Return realistic roles from business/customer/supplier/community/finance/regulator ecosystems.\n"
            "Constraints:\n"
            "- node_type must be one of: business, consumer, supplier, competitor, community, bank, regulator, platform\n"
            "- edge_type must be one of: transaction, influence, trust, dependency, information\n"
            "- every node must include a short persona instruction in `persona`\n"
            "- use compact ids like node_sme_hq, node_students, edge_1\n"
            "- include at least one business node, one consumer node, one supplier node, and one competitor node\n\n"
            f"Structured context snippets:\n{context_snippets}\n\n"
            f"Web snippets (optional):\n{json.dumps(web_snippets, ensure_ascii=True)}"
        )

        parsed = self._invoke_validated_json(self.world_model, prompt, WorldBuildOutput)
        if parsed is None:
            return None

        self.assumptions = parsed.assumptions[:20]
        nodes = self._sanitize_nodes(parsed.nodes)
        edges = self._sanitize_edges(parsed.edges, nodes)
        if not nodes or not edges:
            return None
        return nodes, edges

    async def _build_node_turn_with_llm(
        self,
        tick: int,
        node: dict[str, Any],
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        kpis: dict[str, float],
        recent_events: list[dict[str, Any]],
    ) -> NodeTurnOutput | None:
        """Ask a deep-agent node actor for analysis, then normalize into typed output."""
        if self.node_model is None:
            return None

        node_id = str(node.get("node_id", ""))
        persona = self.personas.get(node_id, "Act according to your role and current network pressures.")
        nearby_edges = [
            edge for edge in edges if edge.get("source") == node_id or edge.get("target") == node_id
        ][:8]
        deep_agent = self._get_node_deep_agent(node=node)
        transcript = ""
        if deep_agent is not None:
            prompt = (
                "You control one node inside a live economic network simulation.\n"
                f"Scenario query: {self.request.query}\n"
                f"Tick: {tick}/{self.request.max_ticks}\n"
                f"Your node: {json.dumps(node, ensure_ascii=True)}\n"
                f"Persona: {persona}\n"
                f"Current KPI deltas: {json.dumps(kpis, ensure_ascii=True)}\n"
                f"Connected edges: {json.dumps(nearby_edges, ensure_ascii=True)}\n"
                f"Recent events: {json.dumps(recent_events[-12:], ensure_ascii=True)}\n"
                "Use `read_allowed_file` for internal context when useful.\n"
                "Use `internet_search` only if needed and enabled.\n"
                "End with one explicit recommended move in plain language."
            )
            try:
                transcript = await self._collect_node_deep_agent_text(deep_agent, prompt)
            except Exception:
                transcript = ""

        structured_prompt = (
            "Convert the following node analysis into one strict JSON object.\n"
            "Do not output markdown or prose.\n"
            f"JSON schema: {json.dumps(NodeTurnOutput.model_json_schema(), ensure_ascii=True, separators=(',', ':'))}\n"
            "Constraints:\n"
            "- action.action_type must be one of observe, message, price_adjust, budget_shift, negotiate_supply, "
            "community_campaign, risk_mitigation, wait\n"
            "- action.payload should be compact and numeric where possible\n"
            "- action.confidence must be in [0,1]\n"
            "- action.message should be 1 short sentence from this node's perspective\n"
            "- narrative confidence_band must be one of low, medium, high\n"
            "- impact directions must be one of up, down, stable\n\n"
            f"Scenario query: {self.request.query}\n"
            f"Tick: {tick}/{self.request.max_ticks}\n"
            f"Node: {json.dumps(node, ensure_ascii=True)}\n"
            f"KPI deltas: {json.dumps(kpis, ensure_ascii=True)}\n"
            f"Recent events: {json.dumps(recent_events[-12:], ensure_ascii=True)}\n"
            f"Node analysis transcript: {json.dumps(transcript, ensure_ascii=True)}"
        )

        parsed = self._invoke_validated_json(self.node_model, structured_prompt, NodeTurnOutput)
        if parsed is not None:
            return parsed

        if transcript.strip():
            fallback_prompt = (
                "You control one node inside a live economic network simulation.\n"
                "Write a compact action + narrative output as strict JSON only.\n"
                f"JSON schema: {json.dumps(NodeTurnOutput.model_json_schema(), ensure_ascii=True, separators=(',', ':'))}\n"
                f"Node: {json.dumps(node, ensure_ascii=True)}\n"
                f"KPI deltas: {json.dumps(kpis, ensure_ascii=True)}\n"
                f"Transcript: {json.dumps(transcript, ensure_ascii=True)}"
            )
            return self._invoke_validated_json(self.node_model, fallback_prompt, NodeTurnOutput)
        return None

    def _fallback_world(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Generate deterministic non-LLM world so runtime remains functional without model access."""
        count = max(self.request.min_nodes, min(self.request.max_nodes, 18))
        nodes: list[dict[str, Any]] = []
        for idx in range(count):
            ntype = NODE_TYPES[idx % len(NODE_TYPES)]
            node_id = f"node_{idx+1}"
            nodes.append(
                {
                    "node_id": node_id,
                    "label": f"{ntype.title()} {idx+1}",
                    "node_type": ntype,
                    "influence": round(self.rng.uniform(0.3, 0.95), 3),
                    "status": "stable",
                    "x": round(self.rng.uniform(40, 820), 2),
                    "y": round(self.rng.uniform(30, 520), 2),
                }
            )
            self.personas[node_id] = f"You represent a {ntype} actor optimizing outcomes under uncertainty."

        edges: list[dict[str, Any]] = []
        edge_count = max(12, min(len(nodes) * 2, 48))
        for idx in range(edge_count):
            source_idx = idx % len(nodes)
            target_idx = (idx * 3 + 5) % len(nodes)
            if source_idx == target_idx:
                target_idx = (target_idx + 1) % len(nodes)
            edges.append(
                {
                    "edge_id": f"edge_{idx+1}",
                    "source": nodes[source_idx]["node_id"],
                    "target": nodes[target_idx]["node_id"],
                    "edge_type": EDGE_TYPES[idx % len(EDGE_TYPES)],
                    "weight": round(self.rng.uniform(0.25, 0.9), 3),
                }
            )
        return nodes, edges

    def _fallback_node_turn(self, node: dict[str, Any], nodes: list[dict[str, Any]], tick: int) -> dict[str, Any]:
        """Generate deterministic fallback action/message for one node turn."""
        target = self.rng.choice(nodes)
        action_type = self.rng.choice(
            [
                "observe",
                "message",
                "price_adjust",
                "budget_shift",
                "negotiate_supply",
                "community_campaign",
                "risk_mitigation",
                "wait",
            ]
        )
        return {
            "action_type": action_type,
            "target_node_id": target.get("node_id"),
            "payload": {"tick": tick, "delta": round(self.rng.uniform(-0.12, 0.18), 3)},
            "rationale": f"{node.get('label', node.get('node_id', 'Node'))} selected {action_type} under local pressure.",
            "confidence": round(self.rng.uniform(0.45, 0.9), 3),
            "message": f"{node.get('label', 'Node')} is responding to current market pressure with {action_type}.",
        }

    def _fallback_node_narrative(
        self,
        node: dict[str, Any],
        fallback: dict[str, Any],
        kpis: dict[str, float],
        tick: int,
    ) -> dict[str, Any]:
        """Build non-technical narrative fallback when node LLM output is unavailable."""
        label = str(node.get("label", "Node"))
        action_type = str(fallback.get("action_type", "observe"))
        message = str(fallback.get("message", f"{label} is adapting to market changes."))
        return self._normalize_narrative(
            node=node,
            tick=tick,
            kpis=kpis,
            action={
                "action_type": action_type,
                "rationale": str(fallback.get("rationale", "")),
                "confidence": fallback.get("confidence", 0.6),
            },
            narrative={
                "headline": f"{label} made a move",
                "summary_short": message[:160],
                "reason": str(fallback.get("rationale", "Responding to market pressure."))[:180],
                "watch_next": "Watch customer response and supplier stability next turn.",
                "confidence_band": "medium",
                "sales": {"direction": "up" if kpis.get("revenue_delta", 0.0) >= 0 else "down", "note": "Sales momentum is shifting."},
                "cost": {"direction": "stable", "note": "Costs remain manageable for now."},
                "risk": {"direction": "up" if kpis.get("risk_delta", 0.0) > 0 else "stable", "note": "Risk needs active monitoring."},
                "full_response_md": (
                    f"### {label} update (Day {tick})\n"
                    f"I chose **{action_type}**. {message}\n\n"
                    f"**Why now:** {str(fallback.get('rationale', 'Current pressure required action.'))}\n\n"
                    f"**What to watch next:** Customer reaction and supply continuity."
                ),
            },
            fallback_message=message,
        )

    def _normalize_narrative(
        self,
        node: dict[str, Any],
        tick: int,
        kpis: dict[str, float],
        action: dict[str, Any],
        narrative: dict[str, Any],
        fallback_message: str,
    ) -> dict[str, Any]:
        """Normalize LLM narrative fields to a stable UI contract."""
        label = str(node.get("label", "Node"))
        action_type = str(action.get("action_type", "observe"))
        confidence = float(action.get("confidence", 0.6) or 0.6)
        confidence_band = str(narrative.get("confidence_band", "")).strip().lower()
        if confidence_band not in {"low", "medium", "high"}:
            if confidence >= 0.75:
                confidence_band = "high"
            elif confidence >= 0.45:
                confidence_band = "medium"
            else:
                confidence_band = "low"

        def _impact_value(key: str, default_direction: str, default_note: str) -> dict[str, str]:
            raw = narrative.get(key)
            direction = default_direction
            note = default_note
            if isinstance(raw, dict):
                direction = str(raw.get("direction", default_direction)).strip().lower()
                note = str(raw.get("note", default_note)).strip()[:160]
            if direction not in {"up", "down", "stable"}:
                direction = default_direction
            return {"direction": direction, "note": note or default_note}

        return {
            "headline": str(narrative.get("headline", f"{label} reacts to market pressure")).strip()[:120],
            "summary_short": str(narrative.get("summary_short", fallback_message)).strip()[:220],
            "reason": str(narrative.get("reason", action.get("rationale", "Responding to local conditions."))).strip()[:220],
            "watch_next": str(narrative.get("watch_next", "Track sentiment, supplier pressure, and competitor response.")).strip()[:180],
            "confidence_band": confidence_band,
            "sales": _impact_value(
                "sales",
                "up" if float(kpis.get("revenue_delta", 0.0)) >= 0 else "down",
                "Sales direction may shift if this move lands well.",
            ),
            "cost": _impact_value(
                "cost",
                "up" if float(kpis.get("cost_delta", 0.0)) > 0 else "stable",
                "Costs need monitoring during rollout.",
            ),
            "risk": _impact_value(
                "risk",
                "up" if float(kpis.get("risk_delta", 0.0)) > 0 else "stable",
                "Risk remains manageable but should be watched.",
            ),
            "full_response_md": str(
                narrative.get(
                    "full_response_md",
                    f"### {label} update (Day {tick})\nI decided to **{action_type}**.\n\n"
                    f"**Why:** {str(action.get('rationale', 'Current conditions required a measured response.'))}\n\n"
                    f"**What to watch next:** {str(narrative.get('watch_next', 'Customer response and supply continuity.'))}",
                )
            ).strip()[:2400],
        }

    def _sanitize_nodes(self, raw_nodes: list[WorldNodeSpec]) -> list[dict[str, Any]]:
        """Clean model-generated nodes and clip count/ranges to request bounds."""
        cleaned: list[dict[str, Any]] = []
        seen: set[str] = set()
        for idx, node in enumerate(raw_nodes):
            if len(cleaned) >= self.request.max_nodes:
                break
            node_id = self._clean_id(node.node_id, fallback=f"node_{idx+1}")
            if node_id in seen:
                continue
            seen.add(node_id)
            node_type = node.node_type if node.node_type in NODE_TYPES else "business"
            status = node.status if node.status in {"stable", "active", "strained", "watch"} else "stable"
            cleaned.append(
                {
                    "node_id": node_id,
                    "label": str(node.label)[:120],
                    "node_type": node_type,
                    "influence": round(max(0.0, min(1.0, float(node.influence))), 3),
                    "status": status,
                    "x": round(max(20.0, min(920.0, float(node.x))), 2),
                    "y": round(max(20.0, min(620.0, float(node.y))), 2),
                }
            )
            self.personas[node_id] = str(node.persona)[:800]

        if len(cleaned) < self.request.min_nodes:
            fallback_nodes, _ = self._fallback_world()
            for node in fallback_nodes:
                if len(cleaned) >= self.request.min_nodes:
                    break
                if node["node_id"] in seen:
                    continue
                seen.add(node["node_id"])
                cleaned.append(node)
        return cleaned

    def _sanitize_edges(self, raw_edges: list[WorldEdgeSpec], nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Clean model-generated edges and keep only valid links between known nodes."""
        if not nodes:
            return []
        node_ids = {str(node["node_id"]) for node in nodes}
        cleaned: list[dict[str, Any]] = []
        seen: set[str] = set()
        for idx, edge in enumerate(raw_edges):
            if len(cleaned) >= 120:
                break
            source = str(edge.source).strip()
            target = str(edge.target).strip()
            if source not in node_ids or target not in node_ids or source == target:
                continue
            edge_id = self._clean_id(edge.edge_id, fallback=f"edge_{idx+1}")
            if edge_id in seen:
                continue
            seen.add(edge_id)
            edge_type = edge.edge_type if edge.edge_type in EDGE_TYPES else "information"
            cleaned.append(
                {
                    "edge_id": edge_id,
                    "source": source,
                    "target": target,
                    "edge_type": edge_type,
                    "weight": round(max(0.05, min(1.0, float(edge.weight))), 3),
                }
            )

        if not cleaned:
            _, fallback_edges = self._fallback_world()
            for edge in fallback_edges:
                if edge["source"] in node_ids and edge["target"] in node_ids:
                    cleaned.append(edge)
        return cleaned

    def _clean_id(self, raw_id: str, fallback: str) -> str:
        """Normalize arbitrary model ids to predictable snake_case tokens."""
        token = re.sub(r"[^a-zA-Z0-9_]+", "_", str(raw_id).strip().lower())
        token = re.sub(r"_+", "_", token).strip("_")
        if not token:
            return fallback
        return token

    def _read_context_snippets(self, max_chars: int = 4000) -> str:
        """Read compact local context from the configured folder for world-builder grounding."""
        if not self._context_roots:
            return ""

        snippets: list[str] = []
        remaining = max_chars
        files: list[Path] = []
        for root in self._context_roots:
            files.extend(
                [
                    p
                    for p in root.rglob("*")
                    if p.is_file() and p.suffix.lower() in {".md", ".txt", ".json", ".csv"}
                ]
            )
        files = sorted(files)[:20]
        for path in files:
            if remaining <= 0:
                break
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            text = re.sub(r"\s+", " ", text).strip()
            if not text:
                continue
            chunk = text[: min(len(text), 500)]
            row = f"{path.name}: {chunk}"
            snippets.append(row)
            remaining -= len(row)
        return "\n".join(snippets)

    def _search_snippets(self, query: str) -> list[dict[str, str]]:
        """Fetch bounded web snippets via Tavily when API key is available."""
        api_key = None
        try:
            import os

            api_key = os.getenv("TAVILY_API_KEY")
        except Exception:
            api_key = None
        if not api_key:
            return []

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=api_key)
            response = client.search(query=query, max_results=3, search_depth="basic")
        except Exception:
            return []

        results = response.get("results") if isinstance(response, dict) else None
        if not isinstance(results, list):
            return []
        snippets: list[dict[str, str]] = []
        for item in results[:3]:
            if not isinstance(item, dict):
                continue
            snippets.append(
                {
                    "title": str(item.get("title", ""))[:120],
                    "url": str(item.get("url", ""))[:200],
                    "content": str(item.get("content", ""))[:400],
                }
            )
        return snippets

    def _invoke_validated_json(self, model: Any, prompt: str, schema_type: type[BaseModel]) -> Any | None:
        """Invoke model and parse output using structured mode first, then JSON fallback."""
        if model is None:
            return None
        try:
            if hasattr(model, "with_structured_output"):
                response = model.with_structured_output(schema_type).invoke(prompt)
                if isinstance(response, schema_type):
                    return response
                return schema_type.model_validate(response)
        except Exception:
            pass

        try:
            response = model.invoke(prompt)
            content = getattr(response, "content", response)
            if isinstance(content, list):
                content = "".join(str(item.get("text", "")) if isinstance(item, dict) else str(item) for item in content)
            text = str(content)
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            parsed = json.loads(text[start : end + 1])
            return schema_type.model_validate(parsed)
        except Exception:
            return None
