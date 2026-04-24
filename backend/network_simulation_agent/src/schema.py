from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel
from pydantic import Field


NETWORK_EVENT_TYPES = {
    "status",
    "progress",
    "network_state",
    "node_action",
    "node_message",
    "edge_update",
    "shock_event",
    "observer_summary",
    "final",
    "error",
    "done",
}


class NetworkSimulatorRequest(BaseModel):
    query: str
    max_ticks: int = Field(default=16, ge=1, le=240)
    seed: int | None = None
    min_nodes: int = Field(default=15, ge=3, le=120)
    max_nodes: int = Field(default=30, ge=3, le=240)
    scenario_id: str = "business_network_v1"
    allow_internet: bool = True
    data_context_path: str | None = None


class ShockRequest(BaseModel):
    shock_type: str
    summary: str
    severity: float = Field(ge=0, le=1)
    targets: list[str] = Field(default_factory=list)


class ObserverChatRequest(BaseModel):
    question: str


class ShockEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"shock_{uuid4().hex[:10]}")
    shock_type: str
    summary: str
    severity: float
    targets: list[str] = Field(default_factory=list)
    ts: datetime = Field(default_factory=datetime.utcnow)


class NodeState(BaseModel):
    node_id: str
    label: str
    node_type: Literal[
        "business",
        "consumer",
        "supplier",
        "competitor",
        "community",
        "bank",
        "regulator",
        "platform",
    ]
    influence: float = Field(ge=0, le=1)
    status: Literal["stable", "active", "strained", "watch"] = "stable"
    x: float
    y: float


class EdgeState(BaseModel):
    edge_id: str
    source: str
    target: str
    edge_type: Literal["transaction", "influence", "trust", "dependency", "information"]
    weight: float = Field(ge=0, le=1)


class NetworkStateSnapshot(BaseModel):
    tick: int
    max_ticks: int
    nodes: list[NodeState]
    edges: list[EdgeState]
    kpis: dict[str, float]

