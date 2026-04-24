# Quality Assurance Testing Document

## 1. Purpose

This document defines scope, prerequisites, test categories, and executable checklists for validating the AI Boss Decision Engine before releases or major merges. It complements `Product_Requirement_Document.md` and `System_Analysis_Document.md` by focusing on **what to verify** and **how**, not on architecture alone.

## 2. Scope

### 2.1 In scope

- Backend API behavior (FastAPI, default port 8000 unless overridden by `PORT` in `.env`).
- Frontend behavior (Vite dev server default port 8080).
- Integration with optional services: Supabase, Google Gemini, Zhipu or Ilmu, Tavily, Cloudinary.
- Simulators and streaming endpoints (smoke level).
- Regression checks for documented user flows.

### 2.2 Out of scope (unless explicitly scheduled)

- Formal penetration testing or load testing to production SLOs.
- Automated E2E suite maintenance in CI (document assumes manual or ad-hoc tooling unless a runner exists).
- Third-party provider SLA validation.

## 3. Test Environment

| Item | Guideline |
| --- | --- |
| Backend root | `boss_decision/backend` |
| Frontend root | `boss_decision/frontend` |
| API base | `http://localhost:8000` (or `VITE_API_BASE_URL` in frontend) |
| UI base | `http://localhost:8080` (Vite default) |
| Configuration | Copy `backend/.env.example` to `backend/.env` and fill keys per test tier below |

### 3.1 Test tiers (recommended)

| Tier | Supabase | Gemini | Tavily | Cloudinary | Use |
| --- | --- | --- | --- | --- | --- |
| A. Minimal | Optional | Optional | No | No | Health routes, static UI, mock decision path on frontend if enabled |
| B. Core LLM | Optional | Yes | No | No | `/api/analyze`, `/api/health/llm`, manager routing |
| C. Full data | Yes | Yes | As needed | As needed | Document upload, supply lists, sales campaign, debate |

Record which tier was used in the test run sign-off (Section 9).

## 4. Entry and Exit Criteria

### 4.1 Entry (before a formal test cycle)

- Application builds: `python -c "import main"` from `backend` with venv active; `npm run build` in `frontend` succeeds.
- No known blocker defects open for the areas under test.
- Test data available: at least one valid query; for Tier C, valid Supabase project and non-production schema if required.

### 4.2 Exit (release or merge candidate)

- All **P0** and **P1** cases in Section 5 pass for the agreed tier, or failures are documented with waivers and follow-up issues.
- Critical paths: health, analyze (or documented degradation), and UI navigation from home to primary routes.
- New defects are logged with steps to reproduce and environment tier.

## 5. Test Cases

Priorities: **P0** (blocker), **P1** (major), **P2** (minor).

### 5.1 Backend smoke and health

| ID | Priority | Precondition | Steps | Expected |
| --- | --- | --- | --- | --- |
| H-01 | P0 | Backend running | GET `/` | JSON with `status` and `version` |
| H-02 | P0 | Backend running | GET `/api/health` | `status` healthy; `workplaces_root` path present; `supabase_probe` reflects DB availability when probed |
| H-03 | P1 | `GOOGLE_API_KEY` set (Tier B+) | GET `/api/health/llm` | 200 and short `llm_response`, or 503 with structured detail if key invalid |
| H-04 | P2 | Optional | GET `/docs` | OpenAPI UI loads |

### 5.2 Decision engine (analyze)

| ID | Priority | Precondition | Steps | Expected |
| --- | --- | --- | --- | --- |
| A-01 | P0 | Tier B+ for full path | POST `/api/analyze` JSON: `query` (string), `mode: hybrid` | 200, `status` completed, `case_id` present, `final_decision` with recommendation, `routing` object |
| A-02 | P1 | Tier B+ | POST `/api/analyze` with `mode: manual`, `forced_agents: ["hr"]` | `routing.route_source` manual; agent insights only for forced set |
| A-03 | P1 | Tier B+ | POST `/api/analyze` with minimal body `{"query": "test"}` | 200; no 500. If LLM down, response should still be structured or return documented error |
| A-04 | P2 | Tier B+ | POST `/api/analyze/upload` multipart: `query` + small `.txt` file | 200; `document_analysis` may appear when extraction works |

### 5.3 Document management API

| ID | Priority | Precondition | Steps | Expected |
| --- | --- | --- | --- | --- |
| D-01 | P1 | Tier C, Supabase | GET `/api/documents?limit=5` | 200; `documents` array, pagination fields |
| D-02 | P1 | Tier C, valid file | POST `/api/documents/upload` with allowed file type | 200; success payload; if extraction fails, `extraction_status` or message indicates skip per implementation |
| D-03 | P2 | Document exists | GET `/api/documents/{source_id}` | 200 with `document` or 404 for invalid id |
| D-04 | P2 | Document exists | DELETE `/api/documents/{source_id}` | 200 success or documented error |

### 5.4 Sales, supply, debate

| ID | Priority | Precondition | Steps | Expected |
| --- | --- | --- | --- | --- |
| S-01 | P1 | `TAVILY_API_KEY` | POST `/api/sales/campaign-suggestions` JSON `{"product": "Test product", "region": "Malaysia"}` | 200 with campaign structure, or 503 if key missing (documented) |
| S-02 | P1 | Tier C, `supply_record` data | GET `/api/supply-chain/availability` | 200; `records` list, `threshold` consistent with product rules |
| S-03 | P1 | Tier C | GET `/api/supply-chain/1/availability` | 200 for existing id, or 404 if id missing |
| S-04 | P1 | Tier C, debate models configured | POST `/api/simulator/sales-supply-debate` JSON `{"max_rounds": 4}` | 200 with `status` ok or `no_data` if no rows; not 500 for empty data |

### 5.5 Simulators (smoke)

| ID | Priority | Precondition | Steps | Expected |
| --- | --- | --- | --- | --- |
| SIM-01 | P2 | Simulator deps installed | POST `/api/simulator/run` minimal `SimulatorRequest` with `query` | 200 `status` ok or documented failure if environment incomplete |
| SIM-02 | P2 | Same | POST `/api/deep-simulator/run` with required fields | 200 or explicit 500 with message |
| SIM-03 | P2 | Same | POST `/api/network-simulator/run` with required fields | 200 or explicit 500 with message |
| SIM-04 | P2 (optional) | After network run | If session id known, GET `/api/network-simulator/{session_id}/storyline` | 200 file download or 404 if artifact not created |

### 5.6 Frontend UI

| ID | Priority | Precondition | Steps | Expected |
| --- | --- | --- | --- | --- |
| U-01 | P0 | Frontend running, API optional | Open `/` | Home loads; decision panel visible; no blank screen |
| U-02 | P0 | Same | From home, follow links to Documents, Simulators, Sales, Supply, Debate (as implemented) | Each route loads without router error; back navigation works |
| U-03 | P1 | Tier B+, `VITE_API_BASE_URL` correct | Submit a query in hybrid mode with mock fallback off | Either real result or clear error; no unhandled client crash |
| U-04 | P1 | Manual mode | Select at least one agent, submit | Request includes forced agents; UI shows result or error |
| U-05 | P2 | Documents page | Upload UI visible; list refresh after upload (Tier C) | No console errors blocking interaction |

### 5.7 Non-functional (lightweight)

| ID | Priority | Precondition | Steps | Expected |
| --- | --- | --- | --- | --- |
| N-01 | P1 | CORS for dev | Call API from browser origin 8080 | No CORS failure on same-machine dev |
| N-02 | P2 | Any | Observe log on failed LLM (429) | No uncaught process crash; user-facing or API error is bounded |

## 6. Test Data Guidelines

- Use **non-production** Supabase and Cloudinary for Tier C.
- **Synthetic** employee or supply ids: use values that exist in seed data or create fixtures in a test project only.
- **Documents**: small `.txt` for analyze-upload; sample PDF or image for corporate upload only in environments with extraction enabled.
- Do not commit real PII or production keys into the repository.

## 7. Defect Reporting (recommended fields)

| Field | Description |
| --- | --- |
| Title | Short summary |
| Environment tier | A, B, or C (Section 3.1) |
| Branch or commit | Git reference |
| Steps | Numbered reproduction |
| Expected / Actual | Clear contrast |
| Severity | P0 to P2 aligned with this document |
| Attachments | Screenshots, response body, log snippets (redact secrets) |

## 8. API Quick Reference (manual testing)

Use OpenAPI at `/docs` for full schemas. Common checks:

- `GET /api/health`
- `GET /api/health/llm` (when Gemini required)
- `POST /api/analyze` (JSON)
- `POST /api/sales/campaign-suggestions` (when Tavily required)

For streaming endpoints, use a client that supports `application/x-ndjson` and read the stream until `done` or `error` line.

## 9. Test Run Sign-Off (template)

| Field | Value |
| --- | --- |
| Date | |
| Tester | |
| Commit or tag | |
| Environment tier (A B C) | |
| Backend port | |
| Frontend port | |
| P0 failures | None / list |
| P1 failures | None / list |
| Waivers | |
| Ready for release | Yes / No |

---

End of quality assurance testing document.
