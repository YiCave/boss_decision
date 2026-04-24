# Backend - AI Boss Decision Engine

Backend API for the multi-agent decision engine. **Python + FastAPI + LangChain** stack for multi-agent orchestration.

## Quick Start

```bash
# 1. Install dependencies
cd backend
# Preferred (uv)
uv sync

# Fallback (pip)
pip install -r requirements.txt

# 2. Setup environment
cp .env.example .env
# Edit .env with your Supabase credentials

# 3. Run server
python run.py

# 4. Test API
# Open http://localhost:8000/docs (FastAPI auto-generated docs)
# Try: GET /api/health
# Try: GET /api/employees/1023 (John Tan - underperformer)
```

## Status

**✅ DONE**: 
- Database schema (PostgreSQL/Supabase)
- Seed data (43 employees, 300+ records)
- FastAPI + LangChain setup
- Base agent architecture
- Example agents (HR, Sales)
- Manager orchestration framework

**🚧 IN PROGRESS**:
- LLM integration for agents (replace rule-based logic)
- Remaining agents (Legal, Finance, Marketing, Supply Chain)
- Vector search for semantic retrieval
- OCR pipeline integration (Kai Haung)

## Database Setup

See [`database/README.md`](database/README.md) for complete database setup instructions.

**Quick start** (Supabase):
1. Create project at [https://supabase.com](https://supabase.com)
2. Run `database/schema.sql` in Supabase SQL Editor
3. Run `database/seed.sql` in Supabase SQL Editor
4. Copy Supabase credentials to `.env` file

## Environment Setup

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your Supabase credentials
# Get these from Supabase Dashboard → Settings → API
```

`.env` structure:
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_KEY=eyJhbGc...
```

## Planned API Structure

### Core Endpoints (to be implemented)

#### 1. Analyze Query (Main Decision Engine)
```
POST /api/analyze
Body: { "query": "Should we fire employee 1023?" }
Response: {
  "case_id": 8001,
  "data": [...],           // Retrieved evidence
  "agents": [...],         // Agent insights
  "subagents": [...],      // Conservative vs aggressive views
  "decision": {...}        // Final verdict
}
```

#### 2. Get Case Details
```
GET /api/cases/:id
Response: {
  "case": {...},
  "evidence": [...],
  "decision": {...}
}
```

#### 3. Get Employee Profile
```
GET /api/employees/:id
Response: {
  "employee": {...},
  "hr_records": [...],
  "sales_records": [...],
  "finance_records": [...]
}
```

#### 4. Evidence Retrieval
```
POST /api/retrieve
Body: {
  "query": "performance records for John Tan",
  "filters": { "dept_id": 102, "period": "2026-Q1" }
}
Response: {
  "results": [...],
  "relevance_scores": [...]
}
```

## Tech Stack Options

### Option A: Node.js + Express

```bash
npm init -y
npm install express @supabase/supabase-js dotenv cors
npm install --save-dev nodemon typescript @types/express
```

**Pros**: 
- Same language as frontend (TypeScript)
- Fast development
- Easy to share types between frontend/backend

**Cons**:
- Less mature ML/NLP libraries compared to Python

### Option B: Python + FastAPI

```bash
uv add fastapi "uvicorn[standard]" supabase python-dotenv
# pip fallback: pip install fastapi uvicorn supabase python-dotenv
```

**Pros**:
- Better ML/NLP ecosystem (for agent logic, vector search)
- Strong typing with Pydantic
- Fast performance

**Cons**:
- Different language from frontend
- Type sharing requires codegen

## Keith's Task Breakdown (Data Agent + Backend)

### Phase 1: Database ✅ DONE
- [x] Schema design
- [x] Seed data (43 employees, 50+ records per table)
- [x] Supabase setup instructions

### Phase 2: API Scaffolding (Current)
1. **Choose framework**: Express or FastAPI
2. **Setup project structure**:
   ```
   backend/
   ├── src/
   │   ├── routes/         # API endpoints
   │   ├── controllers/    # Business logic
   │   ├── services/       # Database queries
   │   └── utils/          # Helpers
   ├── .env
   └── package.json (or pyproject.toml + requirements.txt)
   ```
3. **Implement Supabase connection**:
   - Connection pooling
   - Error handling
   - Query builders

### Phase 3: Evidence Retrieval
1. **SQL query builder** for structured data:
   - Employee lookup by ID
   - Performance records by period
   - Sales records by employee
   - Legal policy search
2. **Vector search** (optional Phase 1):
   - Embed policy text
   - Semantic search for relevant policies

### Phase 4: Agent Orchestration
1. **Agent interface**:
   ```typescript
   interface AgentResult {
     name: string;
     findings: string[];
     risks: string[];
     recommendation: string;
   }
   ```
2. **Manager aggregation logic**:
   - Combine agent outputs
   - Apply persona (conservative/aggressive)
   - Generate final decision

## Supabase Integration Examples

### Node.js (TypeScript)

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
);

// Get employee with related records
async function getEmployeeProfile(employeeId: number) {
  const { data: employee, error } = await supabase
    .from('employee')
    .select(`
      *,
      department:dept_id (*),
      hr_records:hr_record (*),
      sales_records:sales_record (*)
    `)
    .eq('employee_id', employeeId)
    .single();

  return employee;
}

// Evidence retrieval for decision case
async function getEvidence(caseId: number) {
  const { data: evidence } = await supabase
    .from('case_evidence')
    .select('*')
    .eq('case_id', caseId)
    .order('relevance_score', { ascending: false });

  return evidence;
}
```

### Python (FastAPI)

```python
from supabase import create_client, Client
import os

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Get employee profile
def get_employee_profile(employee_id: int):
    response = supabase.table('employee') \
        .select('*, department:dept_id(*), hr_records:hr_record(*), sales_records:sales_record(*)') \
        .eq('employee_id', employee_id) \
        .single() \
        .execute()
    return response.data

# Evidence retrieval
def get_evidence(case_id: int):
    response = supabase.table('case_evidence') \
        .select('*') \
        .eq('case_id', case_id) \
        .order('relevance_score', desc=True) \
        .execute()
    return response.data
```

## Testing the Database

```bash
# Run test queries in Supabase SQL Editor

-- Test 1: Get John Tan's full profile
SELECT 
  e.*,
  d.name as dept_name
FROM employee e
JOIN department d ON e.dept_id = d.dept_id
WHERE e.employee_id = 1023;

-- Test 2: Get evidence for case 8001
SELECT 
  ce.*,
  CASE ce.source_table
    WHEN 'hr_record' THEN (SELECT performance_summary FROM hr_record WHERE hr_id = ce.record_id)
    WHEN 'sales_record' THEN (SELECT deal_name FROM sales_record WHERE sales_id = ce.record_id)
    WHEN 'legal_record' THEN (SELECT policy_name FROM legal_record WHERE legal_id = ce.record_id)
    ELSE NULL
  END as record_summary
FROM case_evidence ce
WHERE ce.case_id = 8001
ORDER BY ce.relevance_score DESC;

-- Test 3: Sales leaderboard Q1 2026
SELECT 
  e.name,
  e.role,
  COUNT(s.sales_id) as deals_closed,
  SUM(s.amount) as total_revenue
FROM employee e
JOIN sales_record s ON e.employee_id = s.employee_id
WHERE s.period = '2026-Q1' AND s.deal_stage = 'closed'
GROUP BY e.employee_id, e.name, e.role
ORDER BY total_revenue DESC;
```

## Next Steps for Keith

1. **Decision**: Choose Node.js or Python
2. **Initialize project**:
   ```bash
   # If Node.js
   npm init -y
   npm install express @supabase/supabase-js dotenv cors
   
   # If Python
   uv add fastapi "uvicorn[standard]" supabase python-dotenv
   # pip fallback: pip install fastapi uvicorn supabase python-dotenv
   ```
3. **Create first endpoint**: `/api/employees/:id`
4. **Test Supabase connection**
5. **Connect frontend**: Update `frontend/src/lib/decision-engine.ts` to call real API

## Coordination with Other Team Members

- **Kai Haung (OCR)**: Will need `/api/upload` endpoint to receive PDFs
- **Marcus (Manager Personas)**: Will need decision aggregation logic in `/api/analyze`
- **Yihao (HR + Legal Agents)**: Will need agent service modules
- **Jialih (Sales + Marketing + Supply Chain Agents)**: Will need agent service modules

## Questions?

See main project [`README.md`](../README.md) for overall architecture and [`database/README.md`](database/README.md) for database details.
