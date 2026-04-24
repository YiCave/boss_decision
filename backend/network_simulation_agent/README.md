# Network Simulation Agent (Phase 4)

Phase-4 backend implementation for the network simulation feature.

## Implemented now

- Contracts and schemas for request/shock/chat payloads.
- NDJSON tick stream with event types:
  - `status`, `progress`, `network_state`, `node_action`, `node_message`,
    `edge_update`, `shock_event`, `observer_summary`, `final`, `done`
- Session artifacts:
  - `backend/network_simulation_agent/runs/{session_id}/session_state.jsonl`
  - `backend/network_simulation_agent/runs/{session_id}/final_report.json`
  - `backend/network_simulation_agent/runs/{session_id}/observer_summary.md`
  - `backend/network_simulation_agent/runs/{session_id}/graph_snapshot.json`
- API integration points:
  - `POST /api/network-simulator/run`
  - `POST /api/network-simulator/stream`
  - `POST /api/network-simulator/{session_id}/shock`
  - `POST /api/network-simulator/{session_id}/observer-chat`
- Real tick engine with deterministic KPI/edge transitions.
- LLM world builder for dynamic node/persona/edge generation (with deterministic fallback).
- LLM node-turn action generation with strict action normalization and validation.
- Context grounding from local docs (`data_context_path`) and optional Tavily snippets.
- Observer chat grounded to persisted run events with `seq`/`tick` citations.

## Deferred to phase 5+

- Observer LLM synthesis with mandatory citation validation against selected events.
- Full Deep Agents tool runtime per node (current node turns are direct chat-model calls).
