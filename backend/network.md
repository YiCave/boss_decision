# Network Simulation Backend Implementation Plan (v1)

## Summary

Build a new **network simulation backend** as a parallel feature (do not replace deep 2D yet).  
This backend powers `/simulation-network` with a real tick engine, all-node LLM personas, shared append-only memory (`session_state.jsonl`), observer final recommendation, and shock injection during runtime.

Framework decision (from skills):
- `framework-selection`: use **Deep Agents + deterministic engine loop**.
- `deep-agents-core`: each node uses Deep Agent tools, but world transitions stay engine-authoritative.

Primary demo audience: **SME owner**.  
Required measurable output: `revenue_delta`, `cost_delta`, `risk_delta` + observer narrative.

## Architecture and Interfaces

### 1. New Backend Module

Create a new package:
- `backend/network_simulation_agent/src/`

Core files:
- `schema.py`: request/state/event/action models
- `engine.py`: tick loop, world transitions, edge updates, KPI updates
- `orchestrator.py`: node Deep Agent execution per tick
- `rules.py`: action validation + legal action normalization
- `observer.py`: final report + post-run grounded answer helper
- `stream_adapter.py`: NDJSON event mapping for frontend
- `agent.py`: `invoke()` + `astream()` entrypoints
- `memory.py`: append/read helpers for `session_state.jsonl`

### 2. API Endpoints (new, parallel to existing deep simulator)

Add in `backend/main.py`:
- `POST /api/network-simulator/run`
- `POST /api/network-simulator/stream`
- `POST /api/network-simulator/{session_id}/shock`
- `POST /api/network-simulator/{session_id}/observer-chat`

Keep existing endpoints unchanged:
- `/api/deep-simulator/*`
- `/api/simulator/*`

### 3. Request/Response Contracts

`NetworkSimulatorRequest`:
- `query: str`
- `max_ticks: int` (default 16, range 1..240)
- `seed: Optional[int]`
- `min_nodes: int` (default 15)
- `max_nodes: int` (default 30)
- `scenario_id: str` (default `business_network_v1`)
- `allow_internet: bool` (default true)
- `data_context_path: Optional[str]` (default company docs root)

Stream event types (NDJSON):
- `status`
- `progress`
- `network_state`
- `node_action`
- `node_message`
- `edge_update`
- `shock_event`
- `observer_summary`
- `final`
- `error`
- `done`

Shock payload:
- `shock_type: str`
- `summary: str`
- `severity: float` (0..1)
- `targets: list[str]`

Observer chat payload:
- `question: str`
- response must be grounded to run artifacts with cited tick/event ids.

## Simulation Model (Decision Complete)

### 1. Node and Edge Semantics

Node types (v1 fixed set):
- `business`, `consumer`, `supplier`, `competitor`, `community`, `bank`, `regulator`, `platform`

Edge types (v1 fixed set, directed + weighted):
- `transaction`, `influence`, `trust`, `dependency`, `information`

### 2. Action Model (typed wrapper, LLM freedom inside payload)

Every node action output must validate to:
- `action_type: str`
- `source_node_id: str`
- `target_node_id: Optional[str]`
- `payload: dict`
- `rationale: str`
- `confidence: float`

Initial legal action set:
- `observe`
- `message`
- `price_adjust`
- `budget_shift`
- `negotiate_supply`
- `community_campaign`
- `risk_mitigation`
- `wait`

Invalid actions are rejected and written as rejection events.

### 3. Tick Loop

Per day tick:
1. Load latest canonical state from memory snapshot in runtime.
2. Apply queued shocks for current tick.
3. Run node turns (Deep Agent per node, bounded by tool schema).
4. Validate actions and resolve deterministic state transitions.
5. Update edge weights and node statuses.
6. Compute KPI deltas (`revenue`, `cost`, `risk`).
7. Append all events to `session_state.jsonl`.
8. Emit stream events to frontend.

Completion:
- generate observer final report
- emit `final` with KPI deltas, recommendation, confidence, turning points.

### 4. Session Memory (canonical)

Per run folder:
- `backend/network_simulation_agent/runs/{session_id}/`

Required file:
- `session_state.jsonl` (append-only events only)

Optional derived files:
- `final_report.json`
- `observer_summary.md`
- `graph_snapshot.json`

Header event (first line) includes:
- `session_id`, `seed`, `model`, `prompt_version`, `query`, `start_ts`

## Deep Agents Integration

### 1. Node Agent Runtime

Each node persona is a Deep Agent configured with:
- system persona prompt (role + constraints)
- toolset:
  - `read_allowed_file`
  - `internet_search` (Tavily, bounded max_results)
  - `submit_node_action` (typed action tool)
  - `inspect_local_state`

### 2. Context Ingestion

Before tick loop:
- collect business context from filesystem docs folder (MCP-compatible path usage)
- normalize into scenario context object
- attach relevant context slices to node prompts per role

### 3. Observer Agent

Observer reads only run artifacts for grounded post-run answers:
- `session_state.jsonl`
- `final_report.json`
- scenario context snapshot

No observer chat before completion.

## Implementation Phases

### Phase 1: Backend Skeleton + Contracts
- add `network_simulation_agent` package
- add request schema + stream adapter + stub engine
- add `/api/network-simulator/stream` that emits deterministic mock events
- verify frontend mock can consume real backend event names

### Phase 2: Real Tick Engine + Memory
- implement real `session_state.jsonl` append pipeline
- implement node/edge state transitions and KPI updates
- implement `/shock` endpoint and queueing
- ensure deterministic replay with `seed`

### Phase 3: Deep Agent Node Turns
- integrate Deep Agents per node turn
- enforce typed action validation
- wire context file reading + Tavily search tool usage
- tune node count defaults for latency stability

### Phase 4: Observer + Chat Grounding
- generate final observer recommendation and metric table
- implement `/observer-chat` grounded responses with citations
- persist report artifacts for replay and auditability

### Phase 5: Hardening + Demo Readiness
- performance tuning (15–30 nodes, 14–30 ticks)
- failure handling for tool/model errors
- fallback behavior when external tools fail
- demo scripts and golden scenarios

## Testing and Acceptance

### Unit Tests
- action schema validation and rejection paths
- edge update math by edge type
- KPI update consistency
- shock application order and effect

### Integration Tests
- stream lifecycle: `status -> ... -> final -> done`
- run creates expected artifacts in per-session folder
- same seed + same input yields reproducible event sequence shape
- observer chat answers cite session events

### Demo Acceptance Criteria
- center graph reacts to real streamed network state
- right panel node inspector reflects real node history
- shock injection changes trajectory visibly
- final recommendation includes measurable `revenue/cost/risk` deltas
- removing GLM materially degrades insight quality

## Defaults and Constraints

- keep existing deep 2D arena untouched until explicit approval to replace
- all nodes are LLM-driven in v1
- internet allowed for nodes + observer (bounded by tool params, not central quota service in v1)
- defaults: `min_nodes=15`, `max_nodes=30`, `max_ticks=16`
- preserve backward compatibility with existing frontend routes and APIs
