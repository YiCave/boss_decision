# Product Requirements Document

## Document Control

| Field | Value |
| --- | --- |
| Product | AI Boss Decision Engine |
| Document type | Product Requirements (derived from current codebase) |
| Scope | `boss_decision` monorepo: FastAPI backend, React (Vite) frontend |

This document describes **as-implemented and intended behavior** of the system as reflected in `backend/main.py`, `frontend/src/`, agents, and services. It is not a marketing spec.

---

# 1. Product Vision and Purpose

## 1.1 Vision

Provide a **web-based system** for **strategic business decisions** that combines:

- A **manager-orchestrated multi-agent pipeline** (domain specialists plus a final synthesis).
- **Optional file-backed and database-backed** company knowledge.
- **Separate product surfaces** for **sales campaigns**, **supply visibility**, **sales versus supply debate**, and **long-running simulators** that are not the core decision home page.

## 1.2 Problem Being Solved

Executives and operators need a single place to pose **what-if and approval-style questions** (hiring, expansion, policy, supply risk) and receive **traceable** outputs that reference **data and documents**, without replacing ERP or legal workflow tools end-to-end.

## 1.3 Success Criteria (Product)

- User can submit a **natural-language question** and receive a **structured answer** (recommendation, risk, confidence, rationale) plus **per-agent** contributions when services are correctly configured.
- User can **upload a document** (decision path or corporate pipeline) and optionally attach it to an analysis, or use the **document management** page for ingestion to the database.
- **Sales** and **supply** standalone pages remain usable **without** embedding them in the main decision layout.
- **Simulators** (classic, deep, network) can run and stream events for monitoring or demo.

---

# 2. Scope

## 2.1 In Scope

- **Decision engine UI** at route `/` with **hybrid** or **manual** agent selection, optional **target** metadata, **optional file upload** with the analyze request, and **mock fallback** when enabled.
- **Document management** at `/documents`: upload, list, delete, tied to `source_document` and related tables when Supabase is configured.
- **Labs / Simulators** hub at `/simulators` and direct routes: classic (`/simulation-live`), deep (`/simulation-deep`), network (`/simulation-network`).
- **Sales agent** UI at `/agents/sales` (campaign ideas via external news search).
- **Supply chain** UI at `/agents/supply-chain` (inventory and threshold notifications).
- **Sales versus supply debate** at `/simulation-sales-supply-debate`.
- **REST API** for health, analysis, document lifecycle, sales campaign, supply APIs, simulators, and debate, as listed in **Section 6**.

## 2.2 Out of Scope (Current Codebase)

- **Native mobile** applications.
- **SSO / enterprise IdP** integration (not modeled in `main.py` as first-class).
- **Guaranteed** GDPR or industry certification; security requirements are **implementation-dependent**.
- **Single unified UI** that merges simulators, debate, and the manager engine into one canvas (by design they are **separated** in routing).

---

# 3. User Roles

| Role | Description | Primary touchpoints |
| --- | --- | --- |
| **Decision user** | Poses questions, may attach files, reviews agent and manager output. | `/`, optional `/api/analyze` or `/api/analyze/upload` |
| **Document operator** | Uploads and manages corporate documents for extraction and storage. | `/documents`, `/api/documents/*` |
| **Sales or supply user** | Uses standalone tools for campaigns or inventory view. | `/agents/sales`, `/agents/supply-chain` |
| **Analyst or demo** | Runs simulators, debates, exports storyline. | Simulators and debate routes, streaming APIs |
| **System integrator** | Configures **Supabase**, **API keys**, **CORS**, deployment. | Environment, `backend/config.py` |

---

# 4. Functional Requirements

## 4.1 Core Decision Engine (Manager Orchestration)

**FR-DE-1** The system **must** accept a **user query** (string) and optional **context** (string), **target_type**, **target_id** for scoping to an entity, and a **mode**:

- `hybrid`: the manager router **selects** which domain agents to run.
- `manual`: the client **sends** `forced_agents` (list of agent keys such as `hr`, `sales`, `legal`, `finance`, `marketing`, `supply_chain`); at least one agent **must** be selected in the UI before submit when in manual mode.

**FR-DE-2** The system **must** run `ManagerAgent.orchestrate_dynamic` to produce:

- `final_decision` with **recommendation**, **rationale**, **risk_level**, **confidence_score**, and related fields.
- `agent_insights` from selected specialists.
- `conservative_view` and `aggressive_view` strings where the orchestration provides them.
- `routing` metadata (e.g. which agents were selected, model used, errors).

**FR-DE-3** The system **must** **persist** a **decision case** and **evidence** and **decision output** via `LocalKnowledgeService` (file-backed case and evidence) for the analysis path in `_run_analysis`.

**FR-DE-4** The client **may** send a **pre-extracted** document analysis block on JSON `POST /api/analyze` using `document_summary`, `document_department`, `document_entities`, `document_tags`.

**FR-DE-5** The client **may** call `POST /api/analyze/upload` with **multipart** form: `query`, optional context, targets, `mode`, optional `forced_agents` (JSON), optional **file**. The server **must** run `ManagerDocumentIngestor.aprocess` on the file when present and pass the result into the same `_run_analysis` path.

**FR-DE-6** The frontend **should** call the backend `VITE_API_BASE_URL` when set; it **should** support **allowMockFallback** to use local mock content if the API fails (see `decision-engine.ts`).

## 4.2 Domain Agents (Specialists)

**FR-AG-1** The backend **must** register these specialist agents for orchestration: **HR**, **Sales**, **Legal**, **Finance**, **Marketing**, **Supply Chain** (all constructed with `LocalKnowledgeService` and `DatabaseService` where used).

**FR-AG-2** When **Supabase** and keys are valid, agents **may** read **company tables** (e.g. `employee`, `hr_record`, `sales_record`, `finance_record`, `supply_record`, `legal_policy`) per agent implementation. When not available, agents **degrade** to local documents or rules as coded.

**FR-AG-3** **Supply chain** has a **low inventory threshold** (constant on `SupplyChainAgent`) for REST aggregations; **list availability** and **per-id** endpoints compute notifications consistently with that threshold.

## 4.3 Document Ingestion (Corporate Pipeline)

**FR-DOC-1** **POST** `/api/documents/upload` **must** accept a file and optional `custom_extraction` form field.

**FR-DOC-2** The pipeline **should**: upload to **Cloudinary** (when configured), create **`source_document`**, run **DocumentIngestor** (Gemini-based extraction in `document_service.py` using `GOOGLE_API_KEY` and `LLM_MODEL`), then optionally **data writer** to SQL when extraction succeeds. If extraction fails, the system **should** still return **upload success** with extraction skipped (warning path).

**FR-DOC-3** **GET** `/api/documents` **must** support optional `doc_type`, `limit`, `offset` and return total count and rows.

**FR-DOC-4** **GET** `/api/documents/{source_id}` **must** return the source row and **related** rows from `hr_record`, `sales_record`, `finance_record`, `marketing_record`, `supply_record`, `legal_policy` when linked by `source_id`.

**FR-DOC-5** **DELETE** `/api/documents/{source_id}` **must** remove Cloudinary asset when resolvable and delete the `source_document` row (CASCADE behavior depends on database schema).

## 4.4 Sales Campaign (Tavily)

**FR-SAL-1** **POST** `/api/sales/campaign-suggestions` **must** accept `product` (2–120 chars) and optional `region` (default **Malaysia** in request model).

**FR-SAL-2** The server **must** return **503** if `TAVILY_API_KEY` is missing. On success, return structured campaign and news content from `SalesCampaignService`.

## 4.5 Supply Chain APIs

**FR-SC-1** **GET** `/api/supply-chain/availability` **must** return all supply records with **per-row** notification payload and **aggregate** threshold and low-inventory count.

**FR-SC-2** **GET** `/api/supply-chain/{supply_id}/availability` **must** return a single record insight or **404** if not found, including agent insight payload.

## 4.6 Sales versus Supply Debate

**FR-DEB-1** **POST** `/api/simulator/sales-supply-debate` **must** accept optional `item_name` and `max_rounds` (1–10, default 4 in model).

**FR-DEB-2** The server **must** run `SalesSupplyDebateService` to produce **rounds** and **judge** output driven by `supply_record` and configured LLM paths inside the service.

## 4.7 Simulators

**FR-SIM-1** **Classic** simulator: **POST** `/api/simulator/run` and **POST** `/api/simulator/stream` (NDJSON) with `SimulatorRequest` (`query` plus optional `structured_data`, `documents`, `business_context`).

**FR-SIM-2** **Deep** simulator: **POST** `/api/deep-simulator/run` and **POST** `/api/deep-simulator/stream` with ticks, seed, `scenario_id`, persona bounds, and summary cadence per `DeepSimulatorRequest`.

**FR-SIM-3** **Network** simulator: **POST** `/api/network-simulator/run` and **POST** `/api/network-simulator/stream` with node counts, `scenario_id`, `allow_internet`, optional `data_context_path`. **Shocks**: **POST** `/api/network-simulator/{session_id}/shock`. **Observer chat**: **POST** `/api/network-simulator/{session_id}/observer-chat`. **Storyline download**: **GET** `/api/network-simulator/{session_id}/storyline` returns a markdown file when the artifact exists.

**FR-SIM-4** Simulator file knowledge **should** read from `backend/agent_docs/simulator/**` and related paths per agent implementation.

## 4.8 Supporting and Read APIs

**FR-API-1** **GET** `/api/health` **must** report local knowledge roots and **Supabase probe** success or unavailability.

**FR-API-2** **GET** `/api/health/llm` **must** verify `UnifiedLLMClient` and return a short model response or **503** on failure.

**FR-API-3** **GET** `/api/employees/{employee_id}` **must** return employee plus HR and sales record lists from local knowledge when data exists.

**FR-API-4** **GET** `/api/cases/{case_id}` **must** return evidence and decision output for a case id from local knowledge.

## 4.9 Frontend Usability

**FR-UI-1** The **home** page **must** expose navigation to **Documents**, **Simulators**, and **direct links** to **Sales agent**, **Supply chain**, and **Sales versus supply debate** (implemented in `Index.tsx`).

**FR-UI-2** The **input panel** **must** support **hybrid** versus **manual** mode, **optional file** attachment for analyze, **allow mock fallback** toggle, and **target** fields.

**FR-UI-3** The **result** view **should** show **staged** chat messages, **agent insights**, **subagent** conservative or aggressive views, and **final decision** when API returns.

---

# 5. Non-Functional Requirements

**NFR-1 Deployment** The backend should run under Uvicorn; port from environment variables (default 8000). The frontend should be built with Vite and served or previewed on the configured port (e.g. 8080 in `vite.config.ts`).

**NFR-2 CORS** The API **must** allow configured localhost origins for development (`main.py` CORS middleware).

**NFR-3 Configuration** Secrets **must** be provided via `backend/.env` (see `.env.example`). **No** secrets **should** be committed to the repository.

**NFR-4 LLM and quotas** Document extraction and manager routing depend on **Google Gemini** and **Zhipu** or **Ilmu**-compatible APIs; **rate limits and billing** are **provider-side** (429 handling is the caller’s concern).

**NFR-5 Observability** The backend uses **Python logging** and **print**-style trace for the document upload pipeline; **no** required centralized APM is defined in code.

**NFR-6 Data residency** Storing data in **Supabase** and **Cloudinary** implies **region** choices are made in those products, not in this repo.

---

# 6. API Summary (Reference)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | API root message |
| GET | `/api/health` | Liveness and storage paths |
| GET | `/api/health/llm` | LLM connectivity |
| GET | `/api/employees/{employee_id}` | Employee and related records |
| GET | `/api/cases/{case_id}` | Case evidence and output |
| POST | `/api/analyze` | Main decision (JSON body) |
| POST | `/api/analyze/upload` | Decision with file upload |
| POST | `/api/documents/upload` | Corporate document pipeline |
| GET | `/api/documents` | List documents |
| GET | `/api/documents/{source_id}` | Document detail |
| DELETE | `/api/documents/{source_id}` | Delete document |
| POST | `/api/sales/campaign-suggestions` | Tavily sales campaigns |
| GET | `/api/supply-chain/availability` | All supply rows |
| GET | `/api/supply-chain/{supply_id}/availability` | One supply row |
| POST | `/api/simulator/run` | Classic simulator |
| POST | `/api/simulator/stream` | Classic stream NDJSON |
| POST | `/api/deep-simulator/run` | Deep simulator |
| POST | `/api/deep-simulator/stream` | Deep stream |
| POST | `/api/network-simulator/run` | Network simulator |
| POST | `/api/network-simulator/stream` | Network stream |
| POST | `/api/simulator/sales-supply-debate` | Debate |
| POST | `/api/network-simulator/{session_id}/shock` | Network shock |
| POST | `/api/network-simulator/{session_id}/observer-chat` | Observer Q and A |
| GET | `/api/network-simulator/{session_id}/storyline` | Download storyline MD |

**Interactive documentation** is available at `/docs` when the FastAPI app is running.

---

# 7. Data and Integrations

## 7.1 Primary data stores

- **Local filesystem** under configured **workplaces** paths: entities, raw files, and case storage via `LocalKnowledgeService`.
- **Supabase (PostgreSQL)** via `DatabaseService` for **transactional** tables: employees, domain records, `source_document`, and links used by agents and document APIs.

## 7.2 External services

- **Google Generative AI (Gemini)** for manager routing, document vision or text extraction (`document_service`, `UnifiedLLMClient` where applicable).
- **Zhipu or Ilmu OpenAI-compatible API** for specialist JSON analysis and data writer when configured.
- **Tavily** for **news and market** search in sales campaign service.
- **Cloudinary** for **hosted file URLs** in the document upload pipeline.

## 7.3 Content assets

**Markdown and CSV** under `backend/agent_docs/simulator/` are **in-world data** for simulators, not end-user help files.

---

# 8. Route Map (Frontend)

| Path | Page purpose |
| --- | --- |
| `/` | Main decision engine |
| `/documents` | Document upload and list |
| `/simulators` | Simulators hub (tabs) |
| `/simulation-live` | Classic simulation |
| `/simulation-deep` | Deep 2D simulation |
| `/simulation-network` | Network simulation |
| `/agents/sales` | Sales campaign suggestor |
| `/agents/supply-chain` | Supply availability |
| `/simulation-sales-supply-debate` | Debate simulator |
| `*` | Not found |

---

# 9. Assumptions and Dependencies

- **Python 3.9+** and **Node 18+** for local development.
- **Valid API keys** in `.env` for any live LLM, Tavily, Cloudinary, or Supabase feature.
- **Schema** in `backend/database/*.sql` applied to the target project before relying on table shapes in production.
- Manual selection in the UI does not include a Finance button in the same list as other agents in `InputPanel` (the list includes HR, Sales, Legal, Marketing, Supply Chain). The Finance agent remains registered in the backend. This UI versus backend gap is a known implementation detail to reconcile in future UX work if required.

---

# 10. Traceability to Implementation

| Area | Primary code locations |
| --- | --- |
| API and wiring | `backend/main.py` |
| Settings | `backend/config.py`, `backend/.env.example` |
| Manager and agents | `backend/agents/manager_agent.py`, `backend/agents/*.py` |
| DB | `backend/db.py` |
| Local knowledge and cases | `backend/services/local_knowledge_service.py` |
| Document upload for analyze | `backend/services/manager_document_ingestor.py` |
| Corporate document extraction | `backend/services/document_service.py` |
| Sales or debate | `backend/services/sales_campaign_service.py`, `sales_supply_debate_service.py` |
| Frontend routes | `frontend/src/App.tsx` |
| Client analyze | `frontend/src/lib/decision-engine.ts` |
| Home UI | `frontend/src/pages/Index.tsx` |

---

# 11. Revision

Updates to this document should track **material** product or API changes. Feature work **should** update **Section 4** and **Section 6** when behavior diverges from this baseline.

---

End of document.
