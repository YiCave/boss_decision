from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class DeepSimulationRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    max_ticks: int = Field(default=5, ge=1, le=240)
    seed: Optional[int] = Field(default=None, ge=0, le=2_147_483_647)
    scenario_id: str = Field(default="pricing_war_v1", min_length=1, max_length=120)
    min_personas: int = Field(default=3, ge=1, le=12)
    max_personas: int = Field(default=6, ge=1, le=12)
    summary_cadence_ticks: int = Field(default=7, ge=1, le=30)


class WorldZone(BaseModel):
    id: str
    name: str
    x: float = Field(ge=0.0, le=100.0)
    y: float = Field(ge=0.0, le=100.0)
    radius: float = Field(default=12.0, ge=2.0, le=40.0)


class WorldMap(BaseModel):
    width: int = 100
    height: int = 100
    zones: list[WorldZone] = Field(default_factory=list)


class KPIState(BaseModel):
    revenue: float = 0.0
    margin: float = 0.0
    sentiment: float = 0.0
    churn_risk: float = 0.0


class PersonaProfile(BaseModel):
    id: str
    name: str
    role: str
    objective: str
    system_prompt: str
    allowed_paths: list[str] = Field(default_factory=list)
    weight: float = Field(default=1.0, ge=0.1, le=4.0)


class AgentSnapshot(BaseModel):
    id: str
    name: str
    role: str
    x: float
    y: float
    status: Literal["idle", "thinking", "acting", "done"]
    tool_calls: list[str] = Field(default_factory=list)
    transcript: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class AgentObservation(BaseModel):
    persona_id: str
    tick: int
    local_view: dict[str, Any] = Field(default_factory=dict)
    goals: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class ActionIntent(BaseModel):
    persona_id: str
    tick: int
    action_type: Literal[
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
    ] = "wait"
    args: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale_md: str = ""
    requested_via_tool: bool = False
    requested_tool: str = ""


GamePhase = Literal["setup", "world", "observe", "action", "resolution", "scoring", "summary", "complete"]
ActionStatus = Literal["pending", "resolved", "rejected"]


class ActionRecord(BaseModel):
    tick: int
    phase: GamePhase = "action"
    persona_id: str
    persona_name: str = ""
    action_type: str
    status: ActionStatus = "pending"
    summary: str = ""
    target_zone_id: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    args: dict[str, Any] = Field(default_factory=dict)
    rationale_md: str = ""
    outcome: str = ""
    requested_via_tool: bool = False
    requested_tool: str = ""


class ActiveEventCard(BaseModel):
    id: str
    title: str
    summary: str = ""
    effects: dict[str, float] = Field(default_factory=dict)
    counter_actions: list[str] = Field(default_factory=list)
    matched_actions: list[str] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    id: str
    tick: int
    message: str
    source: str = "engine"
    ts: datetime = Field(default_factory=datetime.utcnow)


class TickEvent(BaseModel):
    tick: int
    ts: datetime = Field(default_factory=datetime.utcnow)
    type: Literal[
        "agent_thought",
        "tool_call",
        "intent_submitted",
        "intent_rejected",
        "world_delta",
        "kpi_delta",
        "observer_summary",
    ]
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SocialLink(BaseModel):
    source_persona_id: str
    target_persona_id: str
    trust: float = Field(default=0.0, ge=-1.0, le=1.0)
    talk_count: int = Field(default=0, ge=0)
    support_count: int = Field(default=0, ge=0)
    oppose_count: int = Field(default=0, ge=0)
    last_interaction: str = "none"
    updated_tick: int = Field(default=0, ge=0)


class PersonaScoreBreakdown(BaseModel):
    persona_id: str
    persona_name: str = ""
    base_points: float = 0.0
    movement_points: float = 0.0
    intent_quality_points: float = 0.0
    kpi_contribution_points: float = 0.0
    crisis_response_points: float = 0.0
    timing_points: float = 0.0
    resource_efficiency_points: float = 0.0
    social_influence_points: float = 0.0
    total_delta: float = 0.0
    total_score: float = 0.0


class TickScoreBreakdown(BaseModel):
    tick: int = Field(ge=0)
    kpi_shift: float = 0.0
    personas: list[PersonaScoreBreakdown] = Field(default_factory=list)


class ObserverSummary(BaseModel):
    tick: int
    markdown: str


class PersonaObservationReport(BaseModel):
    persona_id: str
    name: str
    role: str
    objective: str
    stance: str
    evidence: list[str] = Field(default_factory=list)
    suggested_next_action: str = ""


class DeepSimulationState(BaseModel):
    query: str
    scenario_id: str
    seed: int
    tick: int
    max_ticks: int
    tick_duration_days: int = 1
    map: WorldMap
    agents: list[AgentSnapshot]
    personas: list[PersonaProfile]
    global_kpis: KPIState
    agent_scores: dict[str, float] = Field(default_factory=dict)
    agent_positions: dict[str, int] = Field(default_factory=dict)
    current_phase: GamePhase = "setup"
    pending_actions: list[ActionRecord] = Field(default_factory=list)
    resolved_actions: list[ActionRecord] = Field(default_factory=list)
    active_event: Optional[ActiveEventCard] = None
    social_links: list[SocialLink] = Field(default_factory=list)
    latest_score_breakdown: Optional[TickScoreBreakdown] = None
    score_breakdown_history: list[TickScoreBreakdown] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    tick_events: list[TickEvent] = Field(default_factory=list)
    observer_summaries: list[ObserverSummary] = Field(default_factory=list)
    done: bool = False


class DeepSimulationFinalResponse(BaseModel):
    summary: str
    key_turning_points: list[str] = Field(default_factory=list)
    recommendation: str
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    periodic_summaries: list[ObserverSummary] = Field(default_factory=list)
    persona_observations: list[PersonaObservationReport] = Field(default_factory=list)
    html_slides: str = ""
