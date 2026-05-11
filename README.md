# AI Boss Decision Engine

A full-stack system for **strategic business decisions** and related demos. A FastAPI backend orchestrates domain agents (HR, legal, finance, marketing, sales, supply chain), document ingestion, optional Supabase data, and separate **simulator** and **sales** experiences. A React (Vite + TypeScript) frontend provides the main decision UI, document flows, and standalone pages for simulators, sales campaigns, supply checks, and sales–supply debate.

## What this project does

- **Decision engine (home)**: User submits a question; the backend runs retrieval and specialist agents (via Zhipu/Ilmu and/or Gemini, depending on path), then returns a structured result with agent insights and a final decision narrative.
- **Document pipeline**: Uploads (e.g. via Cloudinary) with optional text/image extraction (Gemini in `document_service.py`) and SQL writes via the data-writer path when configured.
- **Sales and supply (standalone UIs)**: Sales campaign suggestions (Tavily-backed), supply availability views, and a **sales vs supply debate** simulator with judge output.
- **Simulators (Labs)**: Classic, deep 2D, and network simulation experiences with their own agent stacks and local knowledge under `backend/agent_docs/simulator/`.

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, React Router, TanStack Query |
| Backend | Python 3.9+, FastAPI, Uvicorn |
| Data | Supabase (PostgreSQL) when `SUPABASE_*` is set; local/chroma for vectors as configured |
| LLM / search | Google Gemini (API key), Zhipu/Ilmu (OpenAI-compatible), Tavily, optional OpenAI for simulators |

## Repository layout

```text
boss_decision/
├── README.md                 # This file
├── frontend/                 # React app (Vite)
│   ├── src/                  # Pages, components, decision-engine client
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── main.py               # FastAPI app and routes
│   ├── run.py                # Dev server (uvicorn)
│   ├── config.py             # Settings from environment
│   ├── requirements.txt
│   ├── agents/               # HR, legal, finance, sales, marketing, supply, manager, simulators
│   ├── services/             # Document service, data writer, Cloudinary, etc.
│   ├── database/             # SQL schema and seeds (Supabase/Postgres)
│   ├── agent_docs/simulator/ # Markdown/CSV/JSON used as simulator knowledge (do not treat as dev docs)
│   └── test_docs/            # Sample .md test inputs (optional)
└── (feature branches)        # History may include merged feature branches; see git log
```

## Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.9+ (3.10+ recommended)
- **Supabase** project (or compatible Postgres) if you use live database features
- API keys as needed: **Google AI Studio** (Gemini), **Zhipu/Ilmu**, **Tavily** (sales), **Cloudinary** (document uploads), optional **OpenAI** for simulator model strings

## Setup

### 1. Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env` from the template:

```bash
copy .env.example .env    # Windows
# cp .env.example .env      # macOS/Linux
```

Edit `.env` and set at least:

- `GOOGLE_API_KEY` — used for manager/document paths that call Gemini
- `ZHIPU_API_KEY` and `ZHIPU_BASE_URL` — specialist agents and SQL writer, when you use those features
- `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` (or anon + RLS, depending on your setup) if the app should talk to Supabase
- `TAVILY_API_KEY` — sales campaign API
- `CLOUDINARY_URL` — document upload pipeline

Start the API:

```bash
python run.py
```

Default URL: `http://localhost:8000` (see `PORT` in `.env`). Interactive docs: `http://localhost:8000/docs`.

Sanity check:

```bash
python -c "import main; print('ok')"
```

### 2. Frontend

```bash
cd frontend
npm install
```

If the API is not on the same host/port as the Vite default, set the base URL. Create `frontend/.env` or `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Start the dev server:

```bash
npm run dev
```

The dev server port is defined in `vite.config.ts` (commonly `8080`). Open the URL shown in the terminal. The main decision UI is `/`; simulators are under `/simulators`, sales at `/agents/sales`, supply at `/agents/supply-chain`, debate at `/simulation-sales-supply-debate`.

### 3. Database (optional but typical for full features)

- Apply `backend/database/schema.sql` and `backend/database/seed.sql` in your Supabase SQL editor or `psql`, as appropriate for your environment.
- Point `SUPABASE_*` and `DATABASE_URL` in `backend/.env` at your project.

## Environment variables (summary)

Full list and comments live in **`backend/.env.example`**. In short:

- **Core**: `PORT`, `APP_NAME`
- **Supabase/DB**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `DATABASE_URL`
- **LLM**: `GOOGLE_API_KEY`, `LLM_MODEL`, `LLM_TEMPERATURE`, `ZHIPU_*`, optional `OPENAI_*` and `SIMULATOR_*` / `NETWORK_*` model overrides
- **Integrations**: `TAVILY_API_KEY`, `CLOUDINARY_URL`
- **Local knowledge**: `CHROMA_PERSIST_DIRECTORY`, paths under `workplaces/` if your deployment uses them

## Production build (frontend)

```bash
cd frontend
npm run build
npm run preview   # optional local test of the built assets
```

## Content files (Markdown)

The repo may contain many `.md` files under `backend/agent_docs/` and `test_docs/`. Those are **data** for simulators and tests, not duplicate READMEs. Only the **`README.md` in the repository root** is the project documentation file.

## License and contributions

Contribute via pull requests; keep feature branches small and document API or schema changes in the PR description. Add or update `backend/.env.example` when you introduce new required settings.

---

For API exploration, use the running server’s **OpenAPI** UI at `/docs` once Uvicorn is up.
