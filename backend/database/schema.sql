-- AI Boss Decision Engine - Database Schema (PostgreSQL / Supabase)
-- Single company focus, agent-aligned departments, rich relational data

-- Drop existing tables if recreating (reverse order for foreign keys)
DROP TABLE IF EXISTS decision_output CASCADE;
DROP TABLE IF EXISTS case_evidence CASCADE;
DROP TABLE IF EXISTS decision_case CASCADE;
DROP TABLE IF EXISTS legal_cases CASCADE;
DROP TABLE IF EXISTS legal_contract CASCADE;
DROP TABLE IF EXISTS legal_policy CASCADE;
DROP TABLE IF EXISTS supply_record CASCADE;
DROP TABLE IF EXISTS marketing_record CASCADE;
DROP TABLE IF EXISTS finance_record CASCADE;
DROP TABLE IF EXISTS sales_record CASCADE;
DROP TABLE IF EXISTS hr_record CASCADE;
DROP TABLE IF EXISTS source_document CASCADE;
DROP TABLE IF EXISTS employee CASCADE;
DROP TABLE IF EXISTS department CASCADE;

-- Departments (aligned with agent structure)
CREATE TABLE department (
    dept_id BIGINT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Employees (central entity for cross-domain linking)
CREATE TABLE employee (
    employee_id BIGINT PRIMARY KEY,
    dept_id BIGINT REFERENCES department(dept_id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    email TEXT UNIQUE,
    hire_date DATE NOT NULL,
    salary NUMERIC(10,2) NOT NULL,
    exit_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Source documents (OCR pipeline tracking + explainability)
CREATE TABLE source_document (
    source_id BIGINT PRIMARY KEY,
    doc_type TEXT NOT NULL,
    title TEXT NOT NULL,
    published_date DATE,
    file_path TEXT,
    extracted_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HR records (performance, attendance, warnings)
CREATE TABLE hr_record (
    hr_id BIGINT PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES employee(employee_id) ON DELETE CASCADE,
    period TEXT NOT NULL,
    attendance_days INTEGER,
    absence_days INTEGER DEFAULT 0,
    performance_score NUMERIC(3,2),
    performance_summary TEXT,
    warning_count INTEGER DEFAULT 0,
    pip_status TEXT,
    review_date DATE,
    reviewer_id BIGINT REFERENCES employee(employee_id) ON DELETE SET NULL,
    ai_justification TEXT,
    source_id BIGINT REFERENCES source_document(source_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, period)  -- Prevent duplicate records for same employee + period
);

-- Sales records (revenue contribution, deals, pipeline)
CREATE TABLE sales_record (
    sales_id BIGINT PRIMARY KEY,
    employee_id BIGINT REFERENCES employee(employee_id) ON DELETE SET NULL,
    dept_id BIGINT REFERENCES department(dept_id) ON DELETE SET NULL,
    period TEXT NOT NULL,
    deal_name TEXT,
    product TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    deal_stage TEXT,
    customer_name TEXT,
    region TEXT,
    close_date DATE,
    ai_justification TEXT,
    source_id BIGINT REFERENCES source_document(source_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Finance records (budgets, expenses, salary costs, KPIs)
CREATE TABLE finance_record (
    finance_id BIGINT PRIMARY KEY,
    dept_id BIGINT REFERENCES department(dept_id) ON DELETE SET NULL,
    employee_id BIGINT REFERENCES employee(employee_id) ON DELETE SET NULL,
    period TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    unit TEXT DEFAULT 'MYR',
    category TEXT,
    ai_justification TEXT,
    source_id BIGINT REFERENCES source_document(source_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Marketing records (campaigns, metrics, ROI)
CREATE TABLE marketing_record (
    marketing_id BIGINT PRIMARY KEY,
    period TEXT NOT NULL,
    campaign_name TEXT NOT NULL,
    channel TEXT,
    metric_name TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    target_audience TEXT,
    ai_justification TEXT,
    source_id BIGINT REFERENCES source_document(source_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Supply chain records (inventory, demand, procurement)
CREATE TABLE supply_record (
    supply_id BIGINT PRIMARY KEY,
    period TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_category TEXT,
    inventory_level INTEGER,
    demand_forecast INTEGER,
    reorder_point INTEGER,
    supplier_name TEXT,
    unit_cost NUMERIC(10,2),
    shortage_flag INTEGER DEFAULT 0,
    ai_justification TEXT,
    source_id BIGINT REFERENCES source_document(source_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(item_name, period)  -- Prevent duplicate records for same item + period
);

-- Legal tables (policies, contracts, cases)

-- Legal policies (company rules and policies)
CREATE TABLE legal_policy (
    legal_id BIGINT PRIMARY KEY,
    policy_category TEXT NOT NULL,
    policy_name TEXT NOT NULL,
    rule_text TEXT NOT NULL,
    effective_date DATE,
    region TEXT DEFAULT 'Malaysia',
    ai_justification TEXT,
    source_id BIGINT REFERENCES source_document(source_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Legal contracts (employee and vendor contracts)
CREATE TABLE legal_contract (
    contract_id BIGINT PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES employee(employee_id) ON DELETE CASCADE,
    is_probation TEXT CHECK(is_probation IN ('Yes', 'No')),
    notice_period INTEGER,
    contract_type TEXT,
    start_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Legal cases (employee legal issues and misconduct)
CREATE TABLE legal_cases (
    case_id BIGINT PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES employee(employee_id) ON DELETE CASCADE,
    issue_type TEXT,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Decision cases (user queries)
CREATE TABLE decision_case (
    case_id BIGINT PRIMARY KEY,
    question TEXT NOT NULL,
    context TEXT,
    target_type TEXT,
    target_id BIGINT,
    status TEXT DEFAULT 'pending',
    submitted_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evidence linking (which records were used for each case)
CREATE TABLE case_evidence (
    evidence_id BIGINT PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES decision_case(case_id) ON DELETE CASCADE,
    source_table TEXT NOT NULL,
    record_id BIGINT NOT NULL,
    relevance_score NUMERIC(4,3),
    retrieval_method TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Decision outputs (final manager verdict)
CREATE TABLE decision_output (
    decision_id BIGINT PRIMARY KEY,
    case_id BIGINT NOT NULL REFERENCES decision_case(case_id) ON DELETE CASCADE,
    recommendation TEXT NOT NULL,
    risk_level TEXT NOT NULL CHECK(risk_level IN ('Low', 'Medium', 'High')),
    confidence_score NUMERIC(5,2),
    rationale TEXT NOT NULL,
    conservative_view TEXT,
    aggressive_view TEXT,
    manager_persona TEXT,
    ai_justification TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(case_id)
);

-- Indexes for common query patterns
CREATE INDEX idx_employee_dept ON employee(dept_id);
CREATE INDEX idx_employee_active ON employee(exit_date) WHERE exit_date IS NULL;
CREATE INDEX idx_hr_employee ON hr_record(employee_id);
CREATE INDEX idx_hr_period ON hr_record(period);
CREATE INDEX idx_sales_employee ON sales_record(employee_id);
CREATE INDEX idx_sales_period ON sales_record(period);
CREATE INDEX idx_sales_stage ON sales_record(deal_stage);
CREATE INDEX idx_finance_employee ON finance_record(employee_id);
CREATE INDEX idx_finance_dept ON finance_record(dept_id);
CREATE INDEX idx_legal_contract_employee ON legal_contract(employee_id);
CREATE INDEX idx_legal_cases_employee ON legal_cases(employee_id);
CREATE INDEX idx_evidence_case ON case_evidence(case_id);
CREATE INDEX idx_evidence_source ON case_evidence(source_table, record_id);

-- Comments for documentation
COMMENT ON TABLE department IS 'Agent-aligned departments: Engineering, Sales, Marketing, HR, Finance, Legal, Supply Chain';
COMMENT ON TABLE employee IS 'Central employee entity - enables cross-domain linking across all records';
COMMENT ON TABLE source_document IS 'Original documents for OCR pipeline tracking and explainability';
COMMENT ON TABLE hr_record IS 'Performance reviews, attendance, warnings, PIP status';
COMMENT ON TABLE sales_record IS 'Revenue contribution, deals closed, pipeline status';
COMMENT ON TABLE finance_record IS 'Salaries, budgets, expenses, departmental KPIs';
COMMENT ON TABLE marketing_record IS 'Campaign metrics, ROI, channel performance';
COMMENT ON TABLE supply_record IS 'Inventory levels, demand forecasts, procurement tracking';
COMMENT ON TABLE legal_policy IS 'Company policies, compliance rules, legal constraints';
COMMENT ON TABLE legal_contract IS 'Employee and vendor contract details';
COMMENT ON TABLE legal_cases IS 'Employee legal issues and misconduct cases';
COMMENT ON TABLE decision_case IS 'User queries submitted to the AI decision engine';
COMMENT ON TABLE case_evidence IS 'Links decision cases to relevant records for explainability';
COMMENT ON TABLE decision_output IS 'Final manager verdicts with multi-agent rationale';
