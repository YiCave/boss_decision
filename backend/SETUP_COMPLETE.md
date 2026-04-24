# Backend Setup Complete ✅

## What's Been Created

Your Python + FastAPI + LangChain backend is scaffolded and ready for development!

### Files Created

```
backend/
├── agents/
│   ├── __init__.py               # Agent module exports
│   ├── base_agent.py             # Abstract base class for all agents
│   ├── hr_agent.py               # HR domain agent (Yihao)
│   ├── sales_agent.py            # Sales domain agent (Jialih)
│   └── manager_agent.py          # Orchestrator agent (Marcus)
│
├── database/
│   ├── schema.sql                # PostgreSQL schema (Supabase ready)
│   ├── seed.sql                  # Seed data (43 employees, 300+ records)
│   └── README.md                 # Database documentation
│
├── config.py                     # Environment configuration
├── db.py                         # Supabase client & database service
├── main.py                       # FastAPI application & routes
├── run.py                        # Development server startup script
├── pyproject.toml                # uv project metadata + dependencies
├── uv.lock                       # uv lockfile
├── requirements.txt              # pip-compatible exported dependencies
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore patterns
└── README.md                     # Backend documentation
```

---

## Tech Stack

- **API Framework**: FastAPI (modern, fast, auto-docs)
- **Database**: PostgreSQL via Supabase (cloud)
- **AI Framework**: LangChain (multi-agent orchestration)
- **LLM**: OpenAI GPT-4 (configurable)
- **Vector Store**: ChromaDB (for semantic search)

---

## Next Steps for Keith

### 1. Install Dependencies (5 min)

```bash
cd backend
# Preferred (uv)
uv sync

# Fallback (pip)
pip install -r requirements.txt
```

### 2. Setup Supabase (10 min)

1. Go to [https://supabase.com](https://supabase.com)
2. Create a new project
3. Go to **SQL Editor**
4. Run `database/schema.sql` (creates tables)
5. Run `database/seed.sql` (loads data)
6. Go to **Settings → API** and copy:
   - Project URL
   - `anon` key
   - `service_role` key

### 3. Configure Environment (2 min)

```bash
cp .env.example .env
```

Edit `.env` and add your Supabase credentials:

```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_KEY=eyJhbGc...

# Optional: Add OpenAI key for LLM-powered agents
OPENAI_API_KEY=sk-...
```

### 4. Start Server (1 min)

```bash
python run.py
```

You should see:

```
🚀 Starting AI Boss Decision Engine
📡 API will be available at: http://localhost:8000
📚 API docs at: http://localhost:8000/docs
```

### 5. Test the API (5 min)

#### Option A: Browser (Interactive Docs)

Open: http://localhost:8000/docs

Try these endpoints:
- `GET /` - Health check
- `GET /api/health` - Database connectivity check
- `GET /api/employees/1023` - Get John Tan's profile (underperformer)
- `GET /api/cases/8001` - Get decision case 8001 (fire employee)

#### Option B: Terminal (curl)

```bash
# Health check
curl http://localhost:8000/api/health

# Get employee profile
curl http://localhost:8000/api/employees/1023

# Get decision case
curl http://localhost:8000/api/cases/8001
```

---

## Architecture Overview

### API Routes (in `main.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/health` | GET | Database connectivity check |
| `/api/employees/:id` | GET | Get employee profile + records |
| `/api/cases/:id` | GET | Get decision case + evidence |
| `/api/analyze` | POST | **Main decision engine** (TODO: connect agents) |

### Database Service (in `db.py`)

Pre-built methods for common queries:
- `get_employee(employee_id)` - Employee profile
- `get_employee_hr_records(employee_id)` - Performance reviews
- `get_employee_sales_records(employee_id)` - Sales data
- `get_legal_policies(category)` - Legal policies
- `get_case_evidence(case_id)` - Evidence for a case
- `create_decision_case(...)` - Create new case
- `save_decision_output(...)` - Save final decision

### Agent System (in `agents/`)

#### BaseAgent (Abstract)
All agents inherit from `BaseAgent` and implement:
- `retrieve_evidence(query, context)` - Get relevant data
- `analyze(evidence, query)` - Produce insights

#### Example Agents Implemented
- **HRAgent** (`hr_agent.py`) - Performance, attendance, PIP status
- **SalesAgent** (`sales_agent.py`) - Revenue, deals, pipeline
- **ManagerAgent** (`manager_agent.py`) - Orchestrates all agents, synthesizes decision

#### Agents TODO (for team)
- `legal_agent.py` (Yihao) - Policies, compliance, legal constraints
- `finance_agent.py` (Keith) - Costs, budgets, ROI
- `marketing_agent.py` (Jialih) - Campaigns, ROI, market signals
- `supply_chain_agent.py` (Jialih) - Inventory, procurement, vendors

---

## LangChain Integration (Next Phase)

The current agents use **rule-based logic** (simple if/else). Replace with **LLM-powered analysis**:

### Example: HR Agent with LangChain

```python
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

class HRAgent(BaseAgent):
    def __init__(self, db_service):
        super().__init__(db_service)
        self.llm = ChatOpenAI(model="gpt-4", temperature=0.7)
        self.parser = PydanticOutputParser(pydantic_object=AgentInsight)
    
    async def analyze(self, evidence, query):
        prompt = ChatPromptTemplate.from_template("""
        You are an HR specialist analyzing employee performance data.
        
        Evidence:
        {evidence}
        
        Question: {query}
        
        Provide a structured analysis with:
        - Key findings (performance trends, warnings, attendance)
        - Risks (legal, morale, replacement cost)
        - Recommendation (what action to take)
        
        {format_instructions}
        """)
        
        chain = prompt | self.llm | self.parser
        result = await chain.ainvoke({
            "evidence": str(evidence),
            "query": query,
            "format_instructions": self.parser.get_format_instructions()
        })
        
        return result
```

---

## Team Task Breakdown

### Keith (Data Agent + Backend Infrastructure) ✅ DONE
- [x] Database schema (PostgreSQL/Supabase)
- [x] Seed data (43 employees, 300+ records)
- [x] FastAPI setup
- [x] Supabase integration
- [x] Base agent architecture
- [ ] Finance agent implementation
- [ ] Connect `/api/analyze` to agent pipeline

### Kai Haung (OCR + Data Extraction)
- [ ] OCR pipeline (PDF/image → structured data)
- [ ] GLM-4V integration
- [ ] File upload endpoint (`/api/upload`)
- [ ] Document processing service

### Marcus (Manager Personas)
- [ ] Conservative vs aggressive reasoning (LLM-based)
- [ ] Decision synthesis logic
- [ ] Persona selection UI (optional)
- [ ] Manager agent LangChain implementation

### Yihao (HR + Legal Agents)
- [ ] HR agent LangChain implementation
- [ ] Legal agent implementation
- [ ] Policy retrieval & compliance checking

### Jialih (Sales + Marketing + Supply Chain Agents)
- [ ] Sales agent LangChain implementation
- [ ] Marketing agent implementation
- [ ] Supply Chain agent implementation

---

## Connecting Frontend to Backend

Currently, the frontend (`frontend/src/lib/decision-engine.ts`) uses **mock data**.

To connect to the real backend:

### 1. Update `decision-engine.ts`

```typescript
// Replace the mock analyze() function with API call
export async function analyze(query: string): Promise<AnalysisResult> {
  const response = await fetch('http://localhost:8000/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query })
  });
  
  const data = await response.json();
  return data;
}
```

### 2. Update API Response Format

The backend should return data matching the frontend's `AnalysisResult` interface:

```typescript
interface AnalysisResult {
  data: DataItem[];           // Evidence retrieved
  agents: AgentInsight[];     // Domain agent insights
  subagents: SubagentView[];  // Conservative vs aggressive
  decision: Decision;         // Final verdict
}
```

---

## Testing the Full Pipeline

Once agents are implemented, test the full decision engine:

### Example: Fire Employee Decision

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Should we fire employee John Tan (ID 1023)?",
    "target_type": "employee",
    "target_id": 1023,
    "submitted_by": "Sarah Lim"
  }'
```

Expected flow:
1. Create decision case (case_id returned)
2. Run HR agent → retrieve performance reviews, analyze
3. Run Sales agent → retrieve sales data, analyze
4. Run Legal agent → retrieve termination policies
5. Run Finance agent → calculate costs
6. Manager agent → synthesize all insights
7. Save decision output to database
8. Return structured result to frontend

---

## Common Issues & Solutions

### Issue: ModuleNotFoundError

```bash
# Preferred (uv)
uv sync

# Fallback (pip)
pip install -r requirements.txt
```

Make sure you're in the `backend/` directory.

### Issue: Supabase connection error

Check `.env` has correct credentials:
```bash
# Test connection
python -c "from db import get_supabase_client; print(get_supabase_client().table('employee').select('count').execute())"
```

### Issue: Port 8000 already in use

Change port in `.env`:
```env
PORT=8001
```

### Issue: CORS error from frontend

Add your frontend URL to CORS origins in `main.py`:
```python
allow_origins=["http://localhost:5173", "http://your-frontend-url"]
```

---

## Documentation

- **Backend API**: http://localhost:8000/docs (auto-generated by FastAPI)
- **Database Schema**: `database/README.md`
- **Main README**: `../README.md`
- **Setup Guide**: `../SETUP.md`

---

## Questions?

Reach out to Keith or check:
- FastAPI docs: https://fastapi.tiangolo.com
- LangChain docs: https://python.langchain.com
- Supabase docs: https://supabase.com/docs

---

**Ready to build! 🚀**
