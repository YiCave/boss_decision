# System Analysis Document

## 1. Purpose and Scope

This document provides a system-level analysis of the AI Boss Decision Engine monorepo. It covers logical architecture, major components, data flows, integration points, and operational characteristics as implemented in the backend (`FastAPI`), frontend (`React`/`Vite`), and supporting packages. It is intended for engineers maintaining, extending, or operating the system.

The companion `Product_Requirement_Document.md` describes product-facing requirements; this document explains how the system is structured to satisfy them.

## 2. System Context

### 2.1 External Actors and Systems

| Actor or system | Relationship |
| --- | --- |
| Web browser | Runs the single-page application; calls REST and multipart APIs on the backend. |
| End user | Poses questions, uploads files, navigates to standalone tool pages. |
| Google AI (Gemini) | Invoked for manager routing, sub-agent fallbacks, document extraction, and `UnifiedLLMClient` text or JSON completion. |
| Zhipu / Ilmu (OpenAI-compatible) | Invoked for specialist JSON analysis in HR, legal, finance paths and for data writer and debate models when configured. |
| Tavily | External search API for market signals in sales campaign and sales side of the debate. |
| Supabase (PostgreSQL) | Authoritative company tables and `source_document` when credentials are set. |
| Cloudinary | Object storage and CDN URLs for the corporate document upload pipeline. |
| Optional OpenAI or model strings | Simulators and network or deep paths may use OpenAI-style env-driven model names. |

### 2.2 Containment Boundary

The application boundary is the FastAPI process plus the static or dev-served frontend. Third-party services are always reached over HTTPS. The backend does not embed a separate message queue; long work is handled with `asyncio`, thread pools for blocking simulator code, and streaming HTTP responses for NDJSON simulators.

## 3. High-Level Architecture

The system follows a three-tier pattern.

#### Presentation tier

The React client handles routing, form state, and visualization. It does not own business rules for routing or evidence retrieval; it forwards user intent to the API and renders results. The `decision-engine` module maps API responses into view models and can fall back to local mock data when the API is unreachable and the user allows it.

#### Application tier (API and orchestration)

`main.py` defines HTTP routes, request models, and wiring. Singleton agents and services are created at import time: `LocalKnowledgeService`, `DatabaseService`, one instance per domain agent, and `ManagerAgent` holding references to all specialist agents. Request handlers are thin: they validate input, call services or `await` orchestration, and map exceptions to HTTP status codes.

#### Domain and integration tier

This tier includes the manager and specialist agents (`agents/`), local knowledge and Supabase access (`services/local_knowledge_service.py`, `db.py`), LLM abstractions (`services/llm_client.py`, `services/document_service.py`, `services/manager_document_ingestor.py`), and optional features such as `SalesCampaignService`, `SalesSupplyDebateService`, and Cloudinary. Simulator subsystems live under `simulator_agent/`, `deep_simulation_agent/`, and `network_simulation_agent/`, with dynamic `sys.path` injection before import.

#### Data tier

- File-backed knowledge under `backend/workplaces/` (cases, decisions, scanned documents) managed by `LocalKnowledgeService`.
- Relational data in Supabase when configured.
- Optional Chroma path for vector use per `config` (not exhaustively described here; see `config.py` and usage sites).

A simplified dependency direction: Browser to API; API to agents and services; agents to knowledge, database, and LLM clients; document flows to Cloudinary, Gemini, and data writer; simulators to local `agent_docs` and LLM.

## 4. Subsystem Decomposition

### 4.1 Manager Agent and Dynamic Orchestration

The `ManagerAgent` is the central coordinator for `POST /api/analyze` and `POST /api/analyze/upload`.

#### Routing (hybrid mode)

When the client does not send `forced_agents`, `route_agents` uses `UnifiedLLMClient` to obtain strict JSON with `selected_agents`, `reasoning`, and `confidence`. If JSON parsing or empty selection fails, a text completion path and structural fallbacks are used: document department hint, `target_type` such as `employee` mapping to HR and legal, and finally a default of HR and sales with a warning log if the router is fully degraded. This design prefers minimal department sets to reduce cost and latency at the cost of occasionally misrouting if the model output is wrong.

#### Manual mode

The client supplies `forced_agents`. Routing metadata is set to a manual `route_source` with full confidence, and only those named agents are executed. Names are canonicalized to match the internal registry (for example `supply_chain`).

#### Execution

For each selected agent, either a registered specialist `run(query, context)` is awaited or, if the agent is missing or `force_simple_llm_subagents` is set, a lightweight LLM sub-agent reply is synthesized via `_llm_subagent_reply`. Specialist failures are converted into low-confidence `AgentInsight` with error evidence.

#### Synthesis

The manager generates conservative and aggressive narrative views, then calls `_synthesize_decision` to build the final recommendation, risk, and confidence, optionally a TLDR when multiple insights exist. All of this reuses the same Gemini client with structured prompts.

### 4.2 Specialist Domain Agents

All specialists inherit `BaseAgent` and expose `run` which typically chains `retrieve_evidence` and `analyze`. The common constructor accepts a primary store (named `db_service` in the base class but in practice the `LocalKnowledgeService` instance) and optional `company_db` for `DatabaseService` when Supabase reads are required.

#### Behavioral split

- With Supabase: agents such as HR, legal, and finance can pull real rows and use Zhipu JSON helpers in `agents/llm_client.py` for structured output.
- Without Supabase: agents fall back to scanning local files under `workplaces`, regex or heuristic extraction, and Gemini through `BaseAgent` helpers.

This dual path creates two operational profiles: file-only local demos versus connected enterprise data.

#### Supply chain agent

Exposes a constant low-inventory threshold used both by REST aggregations in `main.py` and by debate and availability responses. The agent can use database rows when `supply_id` appears in context or otherwise uses local or LLM paths per implementation.

#### Marketing agent

Exists in the global agent list for orchestration; behavior follows the same BaseAgent contract.

### 4.3 Local Knowledge Service

`LocalKnowledgeService` provides a filesystem mirror of a subset of database operations. It creates directory trees for documents, raw files, entities, relationships, and cases. It can:

- List and parse knowledge files to synthesize employee HR or sales record fragments.
- Create decision cases and write JSON decisions and evidence with stable identifiers.

The analyze pipeline in `main._run_analysis` persists case evidence for each `evidence_used` item from agent insights, using `record_id` or `path` as a string. This provides traceability in the local file store even when the UI does not show full provenance.

### 4.4 Database Service (Supabase)

`DatabaseService` wraps the Supabase Python client with a service role key. It is used for employees, legal policies, supply records, document listing, and debate row retrieval. It is a hard dependency at import: missing or invalid configuration will fail client creation. Operationally, the health endpoint probes a lightweight query to mark Supabase as available or not.

### 4.5 Two Document Pipelines (Important Distinction)

#### Corporate ingest (`POST /api/documents/upload`)

Intended for governance-style ingestion: upload bytes to Cloudinary, insert `source_document`, run `DocumentIngestor` in `document_service.py` (Google `genai` client, Gemini model from settings), then optionally `data_writer_agent` to emit SQL to domain tables. Failure of extraction still allows upload success with a warning path.

#### Manager chat context (`POST /api/analyze/upload` with file)

Uses `ManagerDocumentIngestor` to produce a compact structured summary, department, entities, and tags to steer routing and agent context. It can use the same Google client for vision or text paths depending on file type. This pipeline does not replace the corporate ingest pipeline; it is optimized for one-off decision support.

### 4.6 Unified LLM Client

`UnifiedLLMClient` centralizes HTTP calls to the Gemini API with:

- A process-wide async lock to serialize calls and avoid concurrent bursts against provider rate limits.
- Retry with exponential backoff and optional `Retry-After` honoring for 429 responses.
- Helpers for JSON completion and raw text.

This is the primary throttle for the manager and sub-agent LLM work.

### 4.7 Sales, Supply, and Debate (Feature-Parallel APIs)

#### Sales campaign

`SalesCampaignService` requires `TAVILY_API_KEY`. It is stateless with respect to user sessions; each request is an independent product and region call.

#### Supply

List and by-id routes aggregate directly from `DatabaseService` and mirror notification text consistent with the supply agent threshold. The by-id path also calls `SupplyChainAgent.run` to attach an agent-style insight for parity with deeper analysis.

#### Sales versus supply debate

`SalesSupplyDebateService` composes:

- One or more `supply_record` rows from `get_supply_records_for_debate` with optional `item_name` filter.
- Tavily-driven market context when keys exist.
- Separate chat completion models for sales, supply, and judge roles (env-overridable), with a fixed round count for simulation stability.

The implementation is self-contained in the service module and does not go through `ManagerAgent`.

### 4.8 Simulators

#### Classic

Loads `simulator_agent` on demand. Supports synchronous `invoke` and `astream` with LangGraph-style stream modes, emitting NDJSON for the client.

#### Deep 2D

`deep_simulation_agent` with tick-based state and scenario identifiers; streams events as JSON lines.

#### Network

`network_simulation_agent` with larger graphs, session store for shocks and observer data, and file artifacts such as storylines. Shock events are queued in `SESSION_STORE`; observer chat reads persisted summaries; storyline download returns a markdown file if present on disk.

All three are imported only when routes run, reducing cold start of unrelated code paths.

### 4.9 Frontend Application Structure

React Router maps paths to page components. The home page composes `InputPanel`, result panels, and a staged chat display. Standalone product pages (sales, supply, debate, simulators) call their respective APIs directly through small client modules under `lib/`. Styling is Tailwind-based with a duplicate Tailwind config note: both `tailwind.config.ts` and `tailwind.config.cjs` exist; the CJS file should keep `container.center` aligned to avoid off-center layouts.

## 5. Data Flow: Primary Request Lifecycles

### 5.1 Analyze (JSON, no file)

1. Client posts `AnalyzeRequest` to `/api/analyze`.
2. `LocalKnowledgeService.create_decision_case` writes a new case.
3. `ManagerAgent.orchestrate_dynamic` runs routing, agents, and synthesis.
4. Evidence and decision output are saved to local knowledge.
5. Response JSON returns status, `case_id`, routing, `final_decision`, insights, and views.

### 5.2 Analyze (multipart with file)

1. File is spooled to a temp path.
2. `ManagerDocumentIngestor.aprocess` returns structured context.
3. Temp file is deleted.
4. Same orchestration and persistence as 5.1, with `document_analysis` attached to the response for debugging and UI.

### 5.3 Document upload (corporate)

1. Validate extension.
2. Cloudinary upload.
3. Generate `source_id` and insert `source_document`.
4. Temp file to `DocumentIngestor.process` for JSON extraction.
5. On success, update `doc_type` and optional data writer. On extraction failure, return success with `extraction_status` skipped.

## 6. Control and Concurrency

- FastAPI `async` handlers; blocking simulator `invoke` uses `asyncio.to_thread`.
- `UnifiedLLMClient` uses a single async lock for Gemini calls to cap concurrency.
- Document service and other modules may still hit provider 429; retries exist in `llm_client` but not everywhere uniformly for every HTTP client in the tree.

## 7. Error Handling and Degradation

- Router failures fall back to document hints, `target_type`, and finally default agents.
- Agent exceptions become degraded insights with low confidence.
- LLM health endpoint returns 503 on failure; analyze may still run with fallback routing and degraded sub-agents.
- Simulators return 500 with message body on unhandled errors; stream endpoints may emit an NDJSON `error` line.
- CORS is restricted to known localhost dev origins; production deployments must update `allow_origins`.

## 8. Security and Privacy Considerations

- API keys are environment-only; the repository ships `.env.example` without secrets.
- Supabase is accessed with a service key on the server; the browser should never receive it.
- User uploads for analyze are written to temp files and deleted; corporate uploads are stored in Cloudinary and referenced by URL in the database.
- No built-in authn or authz on API routes; any network that can reach the port can call the API. Production requires a gateway, VPN, or added middleware.
- Data in `workplaces` and `agent_docs` may contain synthetic PII; treat disk backups accordingly.

## 9. Deployment and Configuration

#### Backend

Run `uvicorn` via `run.py` with reload in development. Port from `config.Settings.port` (default 8000). Python 3.9+ required for the codebase.

#### Frontend

Vite dev server (typical port 8080 in this project). `VITE_API_BASE_URL` should point to the API origin. Production build is static files suitable for any static host, subject to CORS configuration.

#### Environment

`pydantic-settings` loads `backend/.env` with `extra=ignore` so unknown keys from merged branches do not crash startup. Missing Supabase in local-only mode still requires valid placeholder handling in practice because `DatabaseService` currently constructs the client at init; operators must supply working Supabase settings or refactor for lazy init if true offline use is required.

## 10. Observing and Operating the System

- Standard Python logging in agents and the API logger for analyze flows.
- Verbose `print` tracing in the document upload route for step-by-step pipeline visibility.
- OpenAPI at `/docs` for contract inspection and manual testing.
- Health endpoints for process plus optional LLM and Supabase probe.

## 11. Design Tradeoffs and Technical Debt (Observed)

- Dual Tailwind config files risk divergent `container` behavior; the project aligned CJS with TS for centering in a prior fix.
- `BaseAgent` names the first dependency `db_service` but receives `LocalKnowledgeService`; this naming mismatch can confuse new contributors.
- Manual agent UI on the home page omits Finance while the manager still registers the Finance agent; hybrid routing can still select Finance.
- `DatabaseService` is eager at import; stricter split between optional Supabase and pure local would improve offline dev ergonomics.
- Simulator and debate stacks duplicate LLM call patterns in places rather than a single policy engine.

## 12. File and Module Map (Indicative)

| Path | Role |
| --- | --- |
| `backend/main.py` | Application entry, routes, agent wiring |
| `backend/config.py` | Settings and env schema |
| `backend/db.py` | Supabase access |
| `backend/agents/*.py` | Domain agents, manager, and exports |
| `backend/services/local_knowledge_service.py` | Filesystem case and evidence store |
| `backend/services/llm_client.py` | Gemini client, retries, lock |
| `backend/services/document_service.py` | Corporate document extraction |
| `backend/services/manager_document_ingestor.py` | Analyze-time upload context |
| `backend/services/sales_*` | Sales campaign and debate |
| `frontend/src/App.tsx` | Routes |
| `frontend/src/lib/decision-engine.ts` | API client and mock |
| `frontend/src/pages/Index.tsx` | Main decision UI |

## 13. Conclusion

The system is a monolithic FastAPI service with a React front end, multiple LLM providers, and optional Supabase and Cloudinary. The most critical architectural seams are: (1) the manager’s routing and execution loop, (2) the split between local filesystem knowledge and Supabase, (3) the two document pipelines, and (4) the isolated simulator and debate stacks. Changes to any of these areas should be reviewed for cross effects on health checks, CORS, and rate limiting.

---

End of system analysis.
