from __future__ import annotations

import random
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import AsyncIterator

import yaml

from .observer import build_final_report
from .observer import build_periodic_summary
from .orchestrator import DeepOrchestrator
from .rules import apply_intents_to_kpis
from .rules import resolve_conflicts
from .rules import validate_intent
from .schema import ActionRecord
from .schema import ActionIntent
from .schema import ActiveEventCard
from .schema import AgentObservation
from .schema import AgentSnapshot
from .schema import DeepSimulationRequest
from .schema import DeepSimulationState
from .schema import GamePhase
from .schema import KPIState
from .schema import SocialLink
from .schema import TickEvent
from .schema import TimelineEvent
from .schema import WorldMap
from .schema import WorldZone
from .scoring import score_tick
from .stream_adapter import progress_event
from .stream_adapter import tick_event_to_stream
from .stream_adapter import timeline_event
from .stream_adapter import world_event

WORLD_MIN = 4.0
WORLD_MAX = 96.0
SPAWN_X = 50.0
SPAWN_Y = 50.0


def _docs_root() -> Path:
    return Path(__file__).resolve().parents[2] / "agent_docs" / "simulator"


def _scenario_path(scenario_id: str) -> Path:
    return Path(__file__).resolve().parent / "scenarios" / f"{scenario_id}.yaml"


def _load_scenario(scenario_id: str) -> dict[str, Any]:
    path = _scenario_path(scenario_id)
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict):
            return data
    return {
        "id": scenario_id,
        "name": "Tycoon Crisis Sprint",
        "map": {
            "width": 100,
            "height": 100,
            "zones": [
                {"id": "demand_hub", "name": "Demand Hub", "x": 28, "y": 44, "radius": 14, "effects": {"revenue": 0.2}},
                {
                    "id": "supply_yard",
                    "name": "Supply Yard",
                    "x": 72,
                    "y": 35,
                    "radius": 11,
                    "effects": {"margin": 0.2},
                },
                {
                    "id": "brand_garden",
                    "name": "Brand Garden",
                    "x": 58,
                    "y": 74,
                    "radius": 13,
                    "effects": {"sentiment": 0.2},
                },
            ],
        },
        "game_rules": {
            "crisis_trigger_chance": 0.24,
            "daily_base_points": 0.9,
            "move_points_per_step": 0.08,
            "intent_points_multiplier": 1.8,
            "kpi_points_multiplier": 0.75,
        },
        "crisis_cards": [],
    }


def _clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def _move(rng: random.Random) -> float:
    return (rng.random() - 0.5) * 7.5


def _as_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


class DeepSimulationEngine:
    def __init__(self, request: DeepSimulationRequest):
        self.request = request
        self.seed = request.seed if request.seed is not None else random.SystemRandom().randint(1, 2_147_483_647)
        self.rng = random.Random(self.seed)
        self.scenario = _load_scenario(request.scenario_id)
        self.orchestrator = DeepOrchestrator(
            query=request.query,
            scenario=self.scenario,
            min_personas=request.min_personas,
            max_personas=request.max_personas,
            rng=self.rng,
            docs_root=_docs_root(),
        )
        self.state = self._build_initial_state()

    def _build_initial_state(self) -> DeepSimulationState:
        map_payload = self.scenario.get("map", {})
        zones = [
            WorldZone(
                id=str(item.get("id") or f"zone_{idx}"),
                name=str(item.get("name") or f"Zone {idx+1}"),
                x=float(item.get("x", 50.0)),
                y=float(item.get("y", 50.0)),
                radius=float(item.get("radius", 10.0)),
            )
            for idx, item in enumerate(map_payload.get("zones", []))
            if isinstance(item, dict)
        ]
        world_map = WorldMap(
            width=int(map_payload.get("width", 100)),
            height=int(map_payload.get("height", 100)),
            zones=zones,
        )
        agents: list[AgentSnapshot] = []
        scores: dict[str, float] = {}
        positions: dict[str, int] = {}
        for persona in self.orchestrator.personas:
            agents.append(
                AgentSnapshot(
                    id=persona.id,
                    name=persona.name,
                    role=persona.role,
                    x=SPAWN_X,
                    y=SPAWN_Y,
                    status="idle",
                    tool_calls=[],
                    transcript="",
                    confidence=0.5,
                )
            )
            scores[persona.id] = 0.0
            positions[persona.id] = 0
        social_links: list[SocialLink] = []
        persona_ids = [persona.id for persona in self.orchestrator.personas]
        for source_id in persona_ids:
            for target_id in persona_ids:
                if source_id == target_id:
                    continue
                social_links.append(
                    SocialLink(
                        source_persona_id=source_id,
                        target_persona_id=target_id,
                    )
                )
        return DeepSimulationState(
            query=self.request.query,
            scenario_id=self.request.scenario_id,
            seed=self.seed,
            tick=0,
            max_ticks=self.request.max_ticks,
            tick_duration_days=1,
            map=world_map,
            agents=agents,
            personas=self.orchestrator.personas,
            global_kpis=KPIState(),
            agent_scores=scores,
            agent_positions=positions,
            current_phase="setup",
            pending_actions=[],
            resolved_actions=[],
            active_event=None,
            social_links=social_links,
            latest_score_breakdown=None,
            score_breakdown_history=[],
            timeline=[],
            tick_events=[],
            observer_summaries=[],
            done=False,
        )

    def _agent_by_id(self, persona_id: str) -> AgentSnapshot | None:
        return next((agent for agent in self.state.agents if agent.id == persona_id), None)

    def _record_timeline(self, tick: int, message: str, source: str = "engine") -> None:
        event = TimelineEvent(
            id=f"{tick}-{len(self.state.timeline)+1}",
            tick=tick,
            message=message,
            source=source,
            ts=datetime.now(UTC),
        )
        self.state.timeline.insert(0, event)
        self.state.timeline = self.state.timeline[:180]

    def _record_tick_event(self, tick: int, event_type: str, source: str, payload: dict[str, Any]) -> TickEvent:
        event = TickEvent(tick=tick, type=event_type, source=source, payload=payload)
        self.state.tick_events.append(event)
        self.state.tick_events = self.state.tick_events[-400:]
        return event

    def _set_phase(self, phase: GamePhase) -> None:
        self.state.current_phase = phase

    def _zone_id_for_persona(self, persona_id: str) -> str | None:
        zones = self.state.map.zones
        if not zones:
            return None
        idx = self.state.agent_positions.get(persona_id, 0) % len(zones)
        return zones[idx].id

    def _persona_name(self, persona_id: str) -> str:
        agent = self._agent_by_id(persona_id)
        return agent.name if agent is not None else persona_id

    def _social_link(self, source_id: str, target_id: str) -> SocialLink | None:
        return next(
            (
                item
                for item in self.state.social_links
                if item.source_persona_id == source_id and item.target_persona_id == target_id
            ),
            None,
        )

    def _update_social_link(
        self,
        *,
        source_id: str,
        target_id: str,
        tick: int,
        interaction: str,
        trust_delta: float,
        talk_delta: int = 0,
        support_delta: int = 0,
        oppose_delta: int = 0,
    ) -> None:
        if source_id == target_id:
            return
        link = self._social_link(source_id, target_id)
        if link is None:
            return
        link.trust = round(_clamp(link.trust + trust_delta, -1.0, 1.0), 3)
        link.talk_count = max(0, link.talk_count + talk_delta)
        link.support_count = max(0, link.support_count + support_delta)
        link.oppose_count = max(0, link.oppose_count + oppose_delta)
        link.last_interaction = interaction
        link.updated_tick = tick

    def _social_context_for(self, persona_id: str) -> list[dict[str, Any]]:
        related = [item for item in self.state.social_links if item.source_persona_id == persona_id]
        related.sort(key=lambda row: abs(row.trust), reverse=True)
        return [
            {
                "target_persona_id": item.target_persona_id,
                "trust": item.trust,
                "talk_count": item.talk_count,
                "support_count": item.support_count,
                "oppose_count": item.oppose_count,
                "last_interaction": item.last_interaction,
                "updated_tick": item.updated_tick,
            }
            for item in related[:8]
        ]

    def _action_record_from_intent(
        self,
        intent: ActionIntent,
        *,
        status: str,
        phase: GamePhase,
        outcome: str = "",
    ) -> ActionRecord:
        args = dict(intent.args)
        zone_id = str(args.get("zone_id")).strip() if isinstance(args.get("zone_id"), str) else self._zone_id_for_persona(intent.persona_id)
        summary = str(
            args.get("summary")
            or args.get("message")
            or args.get("reason")
            or args.get("strategy_type")
            or intent.action_type.replace("_", " ")
        )
        return ActionRecord(
            tick=intent.tick,
            phase=phase,
            persona_id=intent.persona_id,
            persona_name=self._persona_name(intent.persona_id),
            action_type=intent.action_type,
            status=status,
            summary=summary,
            target_zone_id=zone_id,
            confidence=intent.confidence,
            args=args,
            rationale_md=intent.rationale_md,
            outcome=outcome,
            requested_via_tool=intent.requested_via_tool,
            requested_tool=intent.requested_tool,
        )

    def _observation_for(self, persona_id: str, tick: int) -> AgentObservation:
        agent = self._agent_by_id(persona_id)
        return AgentObservation(
            persona_id=persona_id,
            tick=tick,
            local_view={
                "x": agent.x if agent else 50.0,
                "y": agent.y if agent else 50.0,
                "global_kpis": self.state.global_kpis.model_dump(),
                "recent_timeline": [item.model_dump(mode="json") for item in self.state.timeline[:6]],
                "map_zones": [zone.model_dump() for zone in self.state.map.zones],
                "social_context": self._social_context_for(persona_id),
            },
            goals=["simulate 1 day and update strategic posture"],
            constraints={
                "tick_equals_days": 1,
                "max_ticks": self.state.max_ticks,
                "allowed_actions": [
                    "move",
                    "talk",
                    "propose",
                    "support",
                    "oppose",
                    "price_adjust",
                    "spend_shift",
                    "campaign",
                    "procurement",
                    "wait",
                ],
            },
        )

    def _zone_effects_by_id(self) -> dict[str, dict[str, float]]:
        effects: dict[str, dict[str, float]] = {}
        map_payload = self.scenario.get("map", {})
        for item in map_payload.get("zones", []):
            if not isinstance(item, dict):
                continue
            zone_id = str(item.get("id") or "").strip()
            if not zone_id:
                continue
            raw = item.get("effects")
            if not isinstance(raw, dict):
                effects[zone_id] = {}
                continue
            effects[zone_id] = {
                "revenue": _as_float(raw.get("revenue")),
                "margin": _as_float(raw.get("margin")),
                "sentiment": _as_float(raw.get("sentiment")),
                "churn_risk": _as_float(raw.get("churn_risk")),
            }
        return effects

    def _game_rules(self) -> dict[str, float]:
        raw = self.scenario.get("game_rules")
        if not isinstance(raw, dict):
            return {
                "crisis_trigger_chance": 0.24,
                "daily_base_points": 0.9,
                "move_points_per_step": 0.08,
                "intent_points_multiplier": 1.8,
                "kpi_points_multiplier": 0.75,
            }
        return {
            "crisis_trigger_chance": _as_float(raw.get("crisis_trigger_chance"), 0.24),
            "daily_base_points": _as_float(raw.get("daily_base_points"), 0.9),
            "move_points_per_step": _as_float(raw.get("move_points_per_step"), 0.08),
            "intent_points_multiplier": _as_float(raw.get("intent_points_multiplier"), 1.8),
            "kpi_points_multiplier": _as_float(raw.get("kpi_points_multiplier"), 0.75),
        }

    def _move_agents(self, tick: int, active_persona_ids: set[str]) -> dict[str, int]:
        zones = self.state.map.zones
        rolls_by_persona: dict[str, int] = {}
        if zones:
            zone_count = len(zones)
            for agent in self.state.agents:
                if agent.id in active_persona_ids:
                    roll = self.rng.randint(1, 6)
                    rolls_by_persona[agent.id] = roll
                    current = self.state.agent_positions.get(agent.id, 0)
                    new_idx = (current + roll) % zone_count
                    self.state.agent_positions[agent.id] = new_idx
                    target_zone = zones[new_idx]
                    agent.x = target_zone.x
                    agent.y = target_zone.y
                    self._record_timeline(
                        tick,
                        f"{agent.name} rolled {roll} and moved to {target_zone.name}.",
                        source=f"engine:{agent.id}",
                    )
                elif agent.status != "done":
                    idx = self.state.agent_positions.get(agent.id, 0) % zone_count
                    zone = zones[idx]
                    agent.x = zone.x
                    agent.y = zone.y
        else:
            for agent in self.state.agents:
                if agent.id in active_persona_ids:
                    rolls_by_persona[agent.id] = self.rng.randint(1, 6)
                agent.x = _clamp(agent.x + _move(self.rng), WORLD_MIN, WORLD_MAX)
                agent.y = _clamp(agent.y + _move(self.rng), WORLD_MIN, WORLD_MAX)

        for agent in self.state.agents:
            if agent.id in active_persona_ids:
                if agent.status != "done":
                    agent.status = "thinking"
            elif agent.status != "done":
                agent.status = "idle"
        return rolls_by_persona

    def _apply_zone_effects(self, tick: int, active_persona_ids: set[str]) -> None:
        if not self.state.map.zones:
            return
        zone_effects = self._zone_effects_by_id()
        kpi = self.state.global_kpis.model_copy(deep=True)
        for persona_id in active_persona_ids:
            idx = self.state.agent_positions.get(persona_id, 0) % len(self.state.map.zones)
            zone = self.state.map.zones[idx]
            effect = zone_effects.get(zone.id, {})
            if not effect:
                continue
            confidence = self._agent_by_id(persona_id).confidence if self._agent_by_id(persona_id) else 0.5
            scale = 0.45 + (0.6 * confidence)
            kpi.revenue += _as_float(effect.get("revenue")) * scale
            kpi.margin += _as_float(effect.get("margin")) * scale
            kpi.sentiment += _as_float(effect.get("sentiment")) * scale
            kpi.churn_risk += _as_float(effect.get("churn_risk")) * scale
            self._record_tick_event(
                tick=tick,
                event_type="world_delta",
                source=f"engine:zone:{zone.id}",
                payload={"persona_id": persona_id, "zone_id": zone.id, "effect": effect},
            )
        kpi.churn_risk = max(0.0, kpi.churn_risk)
        self.state.global_kpis = KPIState(
            revenue=round(kpi.revenue, 2),
            margin=round(kpi.margin, 2),
            sentiment=round(kpi.sentiment, 2),
            churn_risk=round(kpi.churn_risk, 2),
        )

    def _run_crisis_phase(self, tick: int, resolved: list[ActionIntent]) -> dict[str, Any] | None:
        cards = self.scenario.get("crisis_cards")
        if not isinstance(cards, list) or not cards:
            return None
        rules = self._game_rules()
        if self.rng.random() > max(0.0, min(1.0, rules["crisis_trigger_chance"])):
            return None
        candidates = [item for item in cards if isinstance(item, dict)]
        if not candidates:
            return None
        card = self.rng.choice(candidates)
        card_id = str(card.get("id") or "crisis")
        title = str(card.get("title") or "Market Shock")
        raw_effects = card.get("effects")
        effects = raw_effects if isinstance(raw_effects, dict) else {}
        counter_actions = [
            str(item) for item in card.get("counter_actions", []) if isinstance(item, str)
        ] if isinstance(card.get("counter_actions"), list) else []
        matched = [intent for intent in resolved if intent.action_type in counter_actions]
        mitigation_ratio = min(0.75, 0.2 * len(matched))
        multiplier = 1.0 - mitigation_ratio
        kpi = self.state.global_kpis.model_copy(deep=True)
        kpi.revenue += _as_float(effects.get("revenue")) * multiplier
        kpi.margin += _as_float(effects.get("margin")) * multiplier
        kpi.sentiment += _as_float(effects.get("sentiment")) * multiplier
        kpi.churn_risk += _as_float(effects.get("churn_risk")) * multiplier
        kpi.churn_risk = max(0.0, kpi.churn_risk)
        self.state.global_kpis = KPIState(
            revenue=round(kpi.revenue, 2),
            margin=round(kpi.margin, 2),
            sentiment=round(kpi.sentiment, 2),
            churn_risk=round(kpi.churn_risk, 2),
        )
        self._record_timeline(
            tick=tick,
            message=f"Crisis card: {title} (mitigation {round(mitigation_ratio * 100)}%).",
            source="engine:crisis",
        )
        crisis = {
            "id": card_id,
            "title": title,
            "effects": {
                "revenue": round(_as_float(effects.get("revenue")) * multiplier, 2),
                "margin": round(_as_float(effects.get("margin")) * multiplier, 2),
                "sentiment": round(_as_float(effects.get("sentiment")) * multiplier, 2),
                "churn_risk": round(_as_float(effects.get("churn_risk")) * multiplier, 2),
            },
            "counter_actions": counter_actions,
            "matched_actions": [intent.action_type for intent in matched],
        }
        self.state.active_event = ActiveEventCard(
            id=card_id,
            title=title,
            summary=f"Market shock in play. Mitigation {round(mitigation_ratio * 100)}%.",
            effects=crisis["effects"],
            counter_actions=counter_actions,
            matched_actions=crisis["matched_actions"],
        )
        return crisis

    def _award_points(
        self,
        tick: int,
        active_ids: set[str],
        rolls: dict[str, int],
        resolved: list[ActionIntent],
        kpi_before: KPIState,
        crisis: dict[str, Any] | None,
    ) -> None:
        rules = self._game_rules()
        persona_names = {agent.id: agent.name for agent in self.state.agents}
        next_scores, breakdown = score_tick(
            tick=tick,
            max_ticks=self.state.max_ticks,
            active_ids=active_ids,
            persona_names=persona_names,
            current_scores=self.state.agent_scores,
            rules=rules,
            rolls=rolls,
            resolved=resolved,
            kpi_before=kpi_before,
            kpi_after=self.state.global_kpis,
            crisis=crisis,
            social_links=self.state.social_links,
        )
        self.state.agent_scores = next_scores
        self.state.latest_score_breakdown = breakdown
        self.state.score_breakdown_history.append(breakdown)
        self.state.score_breakdown_history = self.state.score_breakdown_history[-240:]
        self._record_tick_event(
            tick=tick,
            event_type="kpi_delta",
            source="engine:scoring",
            payload={
                "scores": self.state.agent_scores,
                "score_breakdown": breakdown.model_dump(mode="json"),
            },
        )

    def _apply_resolved_intents(self, tick: int, intents: list[ActionIntent]) -> tuple[list[ActionIntent], list[dict[str, Any]]]:
        accepted: list[ActionIntent] = []
        rejections: list[dict[str, Any]] = []
        zone_ids = {zone.id for zone in self.state.map.zones}
        zone_index_by_id = {zone.id: idx for idx, zone in enumerate(self.state.map.zones)}
        persona_ids = {persona.id for persona in self.state.personas}
        for intent in intents:
            valid, reason = validate_intent(intent, self.state.global_kpis)
            if valid and intent.action_type == "move":
                zone_id = str(intent.args.get("zone_id", "")).strip()
                if zone_id and zone_ids and zone_id not in zone_ids:
                    valid = False
                    reason = f"move rejected: unknown zone_id `{zone_id}`."
            if valid and intent.action_type == "talk":
                target_id = str(intent.args.get("target_persona_id", "")).strip()
                if target_id and target_id not in persona_ids:
                    valid = False
                    reason = f"talk rejected: unknown target_persona_id `{target_id}`."
            if valid and intent.action_type in {"support", "oppose"}:
                target_id = str(intent.args.get("target_persona_id", "")).strip()
                if target_id and target_id not in persona_ids:
                    valid = False
                    reason = f"{intent.action_type} rejected: unknown target_persona_id `{target_id}`."
            if valid:
                if intent.action_type == "move":
                    zone_id = str(intent.args.get("zone_id", "")).strip()
                    idx = zone_index_by_id.get(zone_id)
                    if idx is not None:
                        self.state.agent_positions[intent.persona_id] = idx
                        target = self.state.map.zones[idx]
                        agent = self._agent_by_id(intent.persona_id)
                        if agent is not None:
                            agent.x = target.x
                            agent.y = target.y
                if intent.action_type == "talk":
                    target_id = str(intent.args.get("target_persona_id", "")).strip()
                    if target_id:
                        boost = 0.16 * max(0.1, float(intent.confidence))
                        self._update_social_link(
                            source_id=intent.persona_id,
                            target_id=target_id,
                            tick=tick,
                            interaction="talk",
                            trust_delta=boost,
                            talk_delta=1,
                        )
                        self._update_social_link(
                            source_id=target_id,
                            target_id=intent.persona_id,
                            tick=tick,
                            interaction="talk",
                            trust_delta=boost * 0.55,
                            talk_delta=1,
                        )
                if intent.action_type == "support":
                    target_id = str(intent.args.get("target_persona_id", "")).strip()
                    if target_id:
                        boost = 0.22 * max(0.1, float(intent.confidence))
                        self._update_social_link(
                            source_id=intent.persona_id,
                            target_id=target_id,
                            tick=tick,
                            interaction="support",
                            trust_delta=boost,
                            support_delta=1,
                        )
                        self._update_social_link(
                            source_id=target_id,
                            target_id=intent.persona_id,
                            tick=tick,
                            interaction="supported_by_peer",
                            trust_delta=boost * 0.45,
                        )
                if intent.action_type == "oppose":
                    target_id = str(intent.args.get("target_persona_id", "")).strip()
                    if target_id:
                        drop = 0.25 * max(0.1, float(intent.confidence))
                        self._update_social_link(
                            source_id=intent.persona_id,
                            target_id=target_id,
                            tick=tick,
                            interaction="oppose",
                            trust_delta=-drop,
                            oppose_delta=1,
                        )
                        self._update_social_link(
                            source_id=target_id,
                            target_id=intent.persona_id,
                            tick=tick,
                            interaction="opposed_by_peer",
                            trust_delta=-(drop * 0.5),
                        )
                accepted.append(intent)
                self._record_tick_event(
                    tick=tick,
                    event_type="intent_submitted",
                    source=f"subagent:{intent.persona_id}",
                    payload=intent.model_dump(),
                )
            else:
                rejections.append({"persona_id": intent.persona_id, "reason": reason, "intent": intent.model_dump()})
                self._record_tick_event(
                    tick=tick,
                    event_type="intent_rejected",
                    source=f"engine:{intent.persona_id}",
                    payload={
                        "reason": reason,
                        "intent": intent.model_dump(),
                        "tool": intent.requested_tool,
                    },
                )
                self._record_timeline(tick, f"{intent.persona_id} intent rejected: {reason}", source="engine")
        if accepted:
            self.state.global_kpis = apply_intents_to_kpis(self.state.global_kpis, accepted)
        return accepted, rejections

    async def run_stream(self) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "status", "message": "Deep simulation stream started.", "max_ticks": self.state.max_ticks}
        while not self.state.done:
            self.state.tick += 1
            tick = self.state.tick
            self.state.pending_actions = []
            self.state.resolved_actions = []
            self.state.active_event = None
            personas = self.orchestrator.select_active_personas_for_tick(
                tick=tick,
                churn_risk=self.state.global_kpis.churn_risk,
            )
            active_ids = {persona.id for persona in personas}
            kpi_before = self.state.global_kpis.model_copy(deep=True)
            self._set_phase("world")
            rolls = self._move_agents(tick=tick, active_persona_ids=active_ids)
            yield progress_event(
                self.state,
                f"Day {tick}: strategists rolled, moved districts, and are planning actions.",
            )
            self._set_phase("observe")
            self._set_phase("action")

            candidate_intents: list[ActionIntent] = []
            for persona in personas:
                agent = self._agent_by_id(persona.id)
                if agent is not None:
                    agent.status = "acting"
                observation = self._observation_for(persona.id, tick)
                async for event in self.orchestrator.stream_persona(persona, observation):
                    if event.get("type") == "agent_chunk":
                        chunk = str(event.get("chunk") or "")
                        if chunk and agent is not None:
                            agent.transcript = f"{agent.transcript}{chunk}"
                        self._record_tick_event(
                            tick=tick,
                            event_type="agent_thought",
                            source=f"subagent:{persona.id}",
                            payload={"chunk": chunk[:280]},
                        )
                    elif event.get("type") == "agent_tool_call":
                        call = str(event.get("tool_call") or "tool(...)")
                        if agent is not None:
                            agent.tool_calls.append(call)
                            agent.tool_calls = agent.tool_calls[-12:]
                        self._record_tick_event(
                            tick=tick,
                            event_type="tool_call",
                            source=f"subagent:{persona.id}",
                            payload={"tool_call": call},
                        )
                    elif event.get("type") == "persona_complete":
                        transcript = str(event.get("transcript") or "")
                        if transcript and agent is not None and not agent.transcript:
                            agent.transcript = transcript
                        intent_payload = event.get("intent")
                        if isinstance(intent_payload, dict):
                            intent = ActionIntent.model_validate(intent_payload)
                            candidate_intents.append(intent)
                            self.state.pending_actions.append(
                                self._action_record_from_intent(
                                    intent,
                                    status="pending",
                                    phase="action",
                                    outcome="Queued for resolution.",
                                )
                            )
                            self.state.pending_actions = self.state.pending_actions[-24:]
                            if agent is not None:
                                agent.confidence = intent.confidence
                        if agent is not None and agent.status != "done":
                            agent.status = "idle"
                        message = f"{persona.name} completed day-{tick} reaction."
                        self._record_timeline(tick, message, source=f"subagent:{persona.id}")
                        yield timeline_event(tick, message)

            self._set_phase("resolution")
            resolved = resolve_conflicts(candidate_intents, self.state.personas)
            accepted, rejections = self._apply_resolved_intents(tick, resolved)
            self.state.resolved_actions = [
                self._action_record_from_intent(
                    intent,
                    status="resolved",
                    phase="resolution",
                    outcome="Applied to world state.",
                )
                for intent in accepted
            ]
            for rejection in rejections:
                intent_payload = rejection.get("intent")
                if isinstance(intent_payload, dict):
                    intent = ActionIntent.model_validate(intent_payload)
                    self.state.resolved_actions.append(
                        self._action_record_from_intent(
                            intent,
                            status="rejected",
                            phase="resolution",
                            outcome=str(rejection.get("reason") or "Rejected by validator."),
                        )
                    )
            self.state.pending_actions = []
            self._apply_zone_effects(tick, active_ids)
            crisis = self._run_crisis_phase(tick, resolved)
            self._set_phase("scoring")
            self._award_points(tick, active_ids, rolls, resolved, kpi_before, crisis)
            if resolved:
                self._record_timeline(tick, f"Applied {len(resolved)} resolved intent(s).", source="engine")
            if rejections:
                self._record_timeline(tick, f"Rejected {len(rejections)} intent(s) this tick.", source="engine")
            if crisis is not None:
                self._record_timeline(
                    tick,
                    f"{crisis.get('title', 'Crisis')} changed market conditions this day.",
                    source="engine:crisis",
                )
            self._set_phase("summary")

            world_delta_event = self._record_tick_event(
                tick=tick,
                event_type="world_delta",
                source="engine",
                payload={
                    "resolved_intents": [intent.model_dump() for intent in resolved],
                    "rejections": rejections,
                    "crisis": crisis,
                    "scores": self.state.agent_scores,
                },
            )
            yield tick_event_to_stream(world_delta_event)

            kpi_event = self._record_tick_event(
                tick=tick,
                event_type="kpi_delta",
                source="engine",
                payload=self.state.global_kpis.model_dump(),
            )
            yield tick_event_to_stream(kpi_event)
            yield world_event(self.state)

            if tick % self.request.summary_cadence_ticks == 0:
                periodic = build_periodic_summary(self.state, self.orchestrator.observer_model)
                self.state.observer_summaries.append(periodic)
                self.state.observer_summaries = self.state.observer_summaries[-30:]
                summary_event = self._record_tick_event(
                    tick=tick,
                    event_type="observer_summary",
                    source="observer",
                    payload=periodic.model_dump(),
                )
                yield {"type": "observer_summary", "tick": tick, "markdown": periodic.markdown}
                yield tick_event_to_stream(summary_event)

            if tick >= self.state.max_ticks:
                self.state.done = True
                self._set_phase("complete")
                for agent in self.state.agents:
                    agent.status = "done"

        report = build_final_report(self.state, self.orchestrator.observer_model)
        result = {
            "response": report.model_dump(mode="json"),
            "seed": self.seed,
            "state": self.state.model_dump(mode="json"),
        }
        yield {"type": "final", **result}
        yield {"type": "done"}

    async def run_to_completion(self) -> dict[str, Any]:
        final_result: dict[str, Any] | None = None
        async for event in self.run_stream():
            if event.get("type") == "final":
                final_result = event
        if final_result is None:
            report = build_final_report(self.state, self.orchestrator.observer_model)
            final_result = {
                "type": "final",
                "response": report.model_dump(mode="json"),
                "seed": self.seed,
                "state": self.state.model_dump(mode="json"),
            }
        return {
            "response": final_result.get("response", {}),
            "seed": final_result.get("seed", self.seed),
            "state": final_result.get("state", self.state.model_dump(mode="json")),
        }
