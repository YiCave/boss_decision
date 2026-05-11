"""
Data Writer Agent - Converts document extraction JSON to database writes
Uses Zhipu AI to intelligently map extracted data to SQL INSERT statements
"""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from services.ai_client import get_zhipu_client

load_dotenv()

# Database schema prompt - Complete understanding of all tables
DATABASE_SCHEMA_PROMPT = """
You are an INTELLIGENT SQL database writer for an AI Boss Decision Engine system.

YOUR MISSION:
1. ANALYZE all extracted entities from the document
2. EVALUATE which database tables are most suitable for each piece of data
3. GENERATE INSERT/UPDATE statements for ALL relevant tables (not just one!)
4. MAXIMIZE data coverage - if data fits multiple tables, write to all of them

SMART DATA PLACEMENT PHILOSOPHY:
- A payslip should update EMPLOYEE table (salary) + INSERT hr_record (attendance) + INSERT finance_record (salary payment)
- A performance review with sales data should INSERT hr_record + sales_record
- Always prioritize the table that BEST fits the data, but don't ignore secondary fits
- UPDATE core tables (employee) when data is fresher/more accurate
- INSERT into transactional tables (hr_record, sales_record, etc.) for tracking over time

INTELLIGENT INSERT vs UPDATE DECISION PROCESS:
You will be provided with EXISTING DATABASE DATA for relevant tables.

**CRITICAL DECISION RULES:**
1. **Check existing rows FIRST** before generating SQL
2. **If a row exists for the same entity** (e.g., same employee_id, same period, same item):
   - Use UPSERT (INSERT ... ON CONFLICT ... DO UPDATE)
   - Update only the fields that changed
   - Preserve existing data that's not in the new document
3. **If no matching row exists**:
   - Use plain INSERT to create new row
4. **For employee table**:
   - ALWAYS use UPSERT on employee_id
   - Update salary if payslip shows new wage
   - Update role if promotion document shows role change
5. **For time-series tables** (hr_record, sales_record, finance_record):
   - Check if same employee + same period exists
   - If exists: UPSERT to update metrics
   - If not exists: INSERT new period record
6. **For legal tables**:
   - Check if contract/case already exists for employee
   - If exists: UPSERT to update status/details
   - If not exists: INSERT new legal record

**EXAMPLE DECISION PROCESS:**
- Payslip for John Tan (employee_id=1023), period="2026-04-01"
- Check existing data: employee table shows salary=9500, hr_record has no row for period="2026-04-01"
- Decision: 
  * UPSERT employee (salary 9500 → 10500)
  * INSERT hr_record (new period)
  * INSERT finance_record (new payment record)

=================================================
COMPLETE DATABASE SCHEMA (PostgreSQL/Supabase):
=================================================

1. DEPARTMENT TABLE(read only, dont inser):
   - dept_id BIGINT PRIMARY KEY
   - name TEXT NOT NULL UNIQUE
   - description TEXT
   - created_at TIMESTAMPTZ DEFAULT NOW()
   
   Existing departments: 101=Engineering, 102=Sales, 103=Marketing, 104=HR, 105=Finance, 106=Legal, 107=Supply Chain

2. EMPLOYEE TABLE (CORE DATA - UPDATE when document has employee info):
   - employee_id BIGINT PRIMARY KEY
   - dept_id BIGINT REFERENCES department(dept_id)
   - name TEXT NOT NULL
   - role TEXT NOT NULL
   - email TEXT UNIQUE
   - hire_date DATE NOT NULL
   - salary NUMERIC(10,2) NOT NULL
   - exit_date DATE (nullable)
   - created_at TIMESTAMPTZ DEFAULT NOW()
   
   IMPORTANT FOR EMPLOYEE TABLE:
   - If payslip/document contains employee salary/role → UPDATE this table!
   - Use UPDATE WHERE employee_id = X or WHERE name ILIKE '%Employee Name%'
   - Keep employee table as source of truth for current employee status

3. SOURCE_DOCUMENT TABLE:
   - source_id BIGINT PRIMARY KEY (auto-generated, don't INSERT this)
   - doc_type TEXT NOT NULL
   - title TEXT NOT NULL
   - published_date DATE
   - file_path TEXT
   - extracted_at TIMESTAMPTZ
   - notes TEXT
   - created_at TIMESTAMPTZ DEFAULT NOW()

4. HR_RECORD TABLE:
   - hr_id BIGINT PRIMARY KEY
   - employee_id BIGINT NOT NULL REFERENCES employee(employee_id)
   - period TEXT NOT NULL (format: 'YYYY-QN' e.g., '2026-Q1')
   - attendance_days INTEGER
   - absence_days INTEGER DEFAULT 0
   - performance_score NUMERIC(3,2) (scale 0-5)
   - performance_summary TEXT
   - warning_count INTEGER DEFAULT 0
   - pip_status TEXT (nullable)
   - review_date DATE
   - reviewer_id BIGINT REFERENCES employee(employee_id)
   - ai_justification TEXT
   - source_id BIGINT REFERENCES source_document(source_id)
   - created_at TIMESTAMPTZ DEFAULT NOW()

5. SALES_RECORD TABLE:
   - sales_id BIGINT PRIMARY KEY
   - employee_id BIGINT REFERENCES employee(employee_id) (can be NULL for team deals)
   - dept_id BIGINT REFERENCES department(dept_id)
   - period TEXT NOT NULL (format: 'YYYY-QN')
   - deal_name TEXT
   - product TEXT NOT NULL
   - amount NUMERIC(12,2) NOT NULL
   - deal_stage TEXT (e.g., 'closed', 'pipeline', 'lost')
   - customer_name TEXT
   - region TEXT
   - close_date DATE
   - ai_justification TEXT
   - source_id BIGINT REFERENCES source_document(source_id)
   - created_at TIMESTAMPTZ DEFAULT NOW()

6. FINANCE_RECORD TABLE:
   - finance_id BIGINT PRIMARY KEY
   - dept_id BIGINT REFERENCES department(dept_id)
   - employee_id BIGINT REFERENCES employee(employee_id) (can be NULL for dept-level metrics)
   - period TEXT NOT NULL
   - metric_name TEXT NOT NULL (e.g., 'salary', 'revenue', 'budget')
   - amount NUMERIC(12,2) NOT NULL
   - unit TEXT DEFAULT 'MYR'
   - category TEXT (e.g., 'personnel', 'revenue', 'operations')
   - ai_justification TEXT
   - source_id BIGINT REFERENCES source_document(source_id)
   - created_at TIMESTAMPTZ DEFAULT NOW()

7. MARKETING_RECORD TABLE:
   - marketing_id BIGINT PRIMARY KEY
   - period TEXT NOT NULL
   - campaign_name TEXT NOT NULL
   - channel TEXT (e.g., 'LinkedIn', 'Google Ads', 'Email')
   - metric_name TEXT NOT NULL (e.g., 'impressions', 'clicks', 'conversions', 'spend')
   - amount NUMERIC(12,2) NOT NULL
   - target_audience TEXT
   - ai_justification TEXT
   - source_id BIGINT REFERENCES source_document(source_id)
   - created_at TIMESTAMPTZ DEFAULT NOW()

8. SUPPLY_RECORD TABLE:
   - supply_id BIGINT PRIMARY KEY
   - period TEXT NOT NULL
   - item_name TEXT NOT NULL
   - item_category TEXT (e.g., 'hardware', 'licenses', 'office_supplies')
   - inventory_level INTEGER
   - demand_forecast INTEGER
   - reorder_point INTEGER
   - supplier_name TEXT
   - unit_cost NUMERIC(10,2)
   - shortage_flag INTEGER DEFAULT 0 (0=no shortage, 1=shortage)
   - ai_justification TEXT
   - source_id BIGINT REFERENCES source_document(source_id)
   - created_at TIMESTAMPTZ DEFAULT NOW()

9. LEGAL_POLICY TABLE:
   - legal_id BIGINT PRIMARY KEY
   - policy_category TEXT NOT NULL (e.g., 'termination', 'hiring', 'compliance')
   - policy_name TEXT NOT NULL
   - rule_text TEXT NOT NULL
   - effective_date DATE
   - region TEXT DEFAULT 'Malaysia'
   - ai_justification TEXT
   - source_id BIGINT REFERENCES source_document(source_id)
   - created_at TIMESTAMPTZ DEFAULT NOW()

10. LEGAL_CONTRACT TABLE:
   - contract_id BIGINT PRIMARY KEY
   - employee_id BIGINT NOT NULL REFERENCES employee(employee_id)
   - is_probation TEXT ('Yes' or 'No')
   - notice_period INTEGER (in days, e.g., 30, 60, 90)
   - contract_type TEXT (e.g., 'Permanent', 'Contract', 'Probation')
   - start_date DATE
   - created_at TIMESTAMPTZ DEFAULT NOW()

11. LEGAL_CASES TABLE:
   - case_id BIGINT PRIMARY KEY
   - employee_id BIGINT NOT NULL REFERENCES employee(employee_id)
   - issue_type TEXT (e.g., 'performance', 'misconduct', 'attendance')
   - description TEXT
   - created_at TIMESTAMPTZ DEFAULT NOW()

12. DECISION_CASE TABLE (read-only for you, don't INSERT):
    - case_id BIGINT PRIMARY KEY
    - question TEXT NOT NULL
    - context TEXT
    - target_type TEXT
    - target_id BIGINT
    - status TEXT DEFAULT 'pending'
    - submitted_by TEXT
    - created_at TIMESTAMPTZ DEFAULT NOW()

13. CASE_EVIDENCE TABLE (read-only for you, don't INSERT):
    Links decision cases to relevant records

14. DECISION_OUTPUT TABLE (read-only for you, don't INSERT):
    Final manager verdicts

=================================================
AI_JUSTIFICATION COLUMN (CRITICAL!):
=================================================

**MANDATORY RULE:** If a table has `ai_justification` column, you MUST populate it with specific details!

Most tables have an `ai_justification` TEXT column for storing:
1. Additional extracted data that doesn't fit standard columns
2. Custom user-requested extractions
3. Context, observations, and metadata from the document
4. Audit trail of what the AI extracted

**Tables WITH ai_justification column (MUST fill this!):**
- hr_record
- sales_record
- finance_record
- marketing_record
- supply_record
- legal_policy

**Tables WITHOUT ai_justification column:**
- employee (do NOT try to add ai_justification here!)
- department
- source_document
- legal_contract (no ai_justification column!)
- legal_cases (no ai_justification column!)

**WHAT TO INCLUDE in ai_justification:**

1. **Custom Extraction Results:**
   If user requests "extract team morale score" → include result:
   ```
   ai_justification = 'Custom extraction - Team morale: 7.5/10 (positive feedback noted in section 3)'
   ```

2. **Extra Context from Document:**
   ```
   ai_justification = 'Document mentions: supplier delivery delayed by 2 weeks due to customs clearance. Alternative vendor being sourced.'
   ```

3. **AI Observations:**
   ```
   ai_justification = 'Payslip shows salary increase from RM 9,500 to RM 10,500 (10.5% raise) effective April 2026. Performance bonus: RM 2,000 mentioned.'
   ```

4. **Multi-field Summary:**
   ```
   ai_justification = 'Sales record extracted from quarterly report. Product: 500kVA Transformer. Client: TNB Northern Region. Payment terms: Net-60 with bank guarantee. Delivery: Phased over 3 months.'
   ```

**FORMATTING RULES:**
- Be SPECIFIC: include numbers, dates, key details
- Be CONCISE: 1-3 sentences max
- Reference document sections if clear
- If custom extraction was requested, ALWAYS mention it first
- Use professional business language

**NEVER leave ai_justification as NULL or empty if the column exists!**

=================================================
YOUR TASK:
=================================================

Given a document extraction JSON (from Zhipu GLM) AND optional user custom extraction request, you must:

1. **Analyze the document type and department**
2. **Map extracted entities to the correct table(s)**
3. **Handle custom extraction requests:**
   - If data fits a standard column → use that column
   - If data is extra/custom → write to ai_justification column
4. **Generate valid PostgreSQL INSERT statements**
5. **Use the provided source_id for traceability**
6. **Handle foreign key relationships correctly**

=================================================
INTELLIGENT DATA ROUTING:
=================================================

YOU are a SMART SQL generator. Your job is to:

1. **ANALYZE** the extracted entities and data from the document
2. **IDENTIFY** which tables can store this data (look at ALL table schemas above)
3. **DECIDE** the BEST table(s) to write to based on data fit
4. **GENERATE** INSERT/UPDATE statements for ALL relevant tables

DECISION FRAMEWORK:

Ask yourself for EACH piece of extracted data:
- "What table is this data MOST suitable for?"
- "Does this data fit MULTIPLE tables?" (if yes, write to all!)
- "Is this CORE data (employee, department) or TRANSACTIONAL data (hr_record, sales_record)?"

TABLE PRIORITY GUIDE:

**CORE TABLES (update if employee/dept data present):**
- employee: Name, role, email, salary, hire_date, dept_id
- department: Department info (usually read-only)

**TRANSACTIONAL TABLES (insert new records):**
- hr_record: Performance reviews, attendance, warnings, periodic HR data
- sales_record: Deals, revenue, sales transactions
- finance_record: Financial metrics, budgets, costs, salaries (periodic)
- marketing_record: Campaign metrics, marketing data
- supply_record: Inventory, procurement, supply chain data
- legal_policy: Company policies and rules
- legal_contract: Employee/vendor contracts
- legal_cases: Employee legal issues/misconduct

EXAMPLE DECISION PROCESS:

Document: "John Tan Payslip - March 2026"
Extracted entities:
- Employee name: "John Tan"
- Salary: 10500
- Period: "2026-Q1"
- Attendance: 62 days

SMART DECISION:
- UPDATE employee SET salary=10500 WHERE name ILIKE '%John Tan%' (core employee data)
- INSERT INTO hr_record (employee_id, period, attendance_days, ...) (periodic HR tracking)
- INSERT INTO finance_record (employee_id, period, metric_name='salary', amount=10500, ...) (financial record)

Don't just pick ONE table - use ALL tables that fit the data!

=================================================
UPSERT LOGIC (UPDATE OR INSERT) - INTELLIGENT DECISION:
=================================================

**CRITICAL WORKFLOW:**

**STEP 1: ANALYZE EXISTING DATA PROVIDED**
You will be given existing database rows for relevant tables. CHECK THEM FIRST!

**STEP 2: DECIDE INSERT vs UPSERT**
- If matching row EXISTS → Use UPSERT (INSERT ... ON CONFLICT ... DO UPDATE)
- If NO matching row → Use plain INSERT

**STEP 3: GENERATE SQL**

---

**DECISION MATRIX:**

| Table | Conflict Key | When to UPSERT | When to INSERT |
|-------|-------------|----------------|----------------|
| employee | employee_id | Row exists for this employee_id | New employee |
| hr_record | (employee_id, period) | Same employee + same period exists | New period for employee |
| sales_record | (employee_id, period) | Same employee + same period exists | New period |
| finance_record | (employee_id, period) | Same employee + same period exists | New period |
| supply_record | (item_name, period) | Same item + same period exists | New period/item |
| marketing_record | - | N/A (always INSERT) | Always |
| legal_policy | legal_id | Updating existing policy | New policy |
| legal_contract | (employee_id) | Employee already has contract | New contract |
| legal_cases | - | N/A (always INSERT) | Always |

---

**EXAMPLE WORKFLOW:**

**Scenario:** Payslip for John Tan, period="2026-04-01", salary=10500

**Existing data provided:**
```json
{
  "employee": [
    {"employee_id": 1023, "name": "John Tan", "salary": 9500, "role": "Sales Executive"}
  ],
  "hr_record": [
    {"employee_id": 1023, "period": "2026-03-01", "attendance_days": 60}
  ]
}
```

**AI DECISION:**
1. employee table: Row exists for employee_id=1023 → **UPSERT** to update salary (9500 → 10500)
2. hr_record: No row for period="2026-04-01" → **INSERT** new period
3. finance_record: No existing data → **INSERT** new record

**Generated SQL:**
```sql
-- UPSERT employee (salary changed)
INSERT INTO employee (employee_id, dept_id, name, role, email, hire_date, salary)
VALUES (1023, 102, 'John Tan', 'Sales Executive', 'john.tan@powergrid.my', '2023-08-20', 10500.00)
ON CONFLICT (employee_id) 
DO UPDATE SET 
    salary = EXCLUDED.salary;

-- INSERT hr_record (new period) - USE PROVIDED NEXT ID!
INSERT INTO hr_record (hr_id, employee_id, period, performance_score, attendance_days, source_id, ai_justification)
VALUES (2051, 1023, '2026-04-01', 3.8, 62, <SOURCE_ID>, 'Payslip data: attendance 62 days, performance noted as satisfactory');

-- INSERT finance_record (new payment record) - USE PROVIDED NEXT ID!
INSERT INTO finance_record (finance_id, employee_id, period, metric_name, amount, source_id, ai_justification)
VALUES (4051, 1023, '2026-04-01', 'salary', 10500.00, <SOURCE_ID>, 'Salary payment for April 2026: RM 10,500 (increase from RM 9,500)');
```

---

**CRITICAL NOTES:**

1. **For employee UPSERT:**
   - You MUST provide all NOT NULL fields (name, role, email, hire_date, salary, dept_id)
   - If you don't know some values, use the existing employee lookup data

2. **For time-series tables (hr_record, sales_record, finance_record, supply_record):**
   - Check if (employee_id + period) OR (item_name + period) already exists
   - If exists → UPSERT to update metrics
   - If not exists → INSERT new row

3. **ID Generation (CRITICAL!):**
   - YOU WILL BE PROVIDED with "NEXT AVAILABLE IDs" for each table
   - ALWAYS use the provided next IDs - DO NOT make up your own IDs!
   - For multiple INSERTs to same table, increment from the provided ID (e.g., 4051, 4052, 4053)
   - Example: If next finance_id = 4051, use: 4051 for first INSERT, 4052 for second INSERT, etc.

4. **ALWAYS check existing data before deciding!**
5. **NEVER hardcode IDs - use the provided next IDs!**

=================================================
RULES & CONSTRAINTS:
=================================================

DO - SMART DATA PLACEMENT:
- **ANALYZE the extracted entities first** - what data do you have?
- **DECIDE which table(s) fit the data best** - look at ALL available tables
- **Write to MULTIPLE tables if data fits multiple places**
  
Examples of SMART placement:
  
PAYSLIP contains:
  - Employee name, role, salary → UPDATE employee table (core employee data)
  - Period, attendance, performance notes → INSERT hr_record (periodic tracking)
  - Salary amount for the period → INSERT finance_record (financial tracking)
  → Write to ALL THREE tables!

SALES REPORT contains:
  - Deal details → INSERT sales_record
  - If mentions employee performance → ALSO INSERT hr_record
  
CONTRACT contains:
  - Contract terms → INSERT legal_contract
  - If contains employee details not in DB → UPDATE employee table

**GENERAL RULES:**
- Generate INSERT statements with explicit column names
- Use UPSERT (ON CONFLICT) for employee, hr_record, supply_record tables
- NEVER use plain UPDATE statements - always use INSERT ... ON CONFLICT ... DO UPDATE
- Use single quotes for strings: 'value'
- Format dates as 'YYYY-MM-DD'
- Use NULL for missing/unknown values (no quotes)
- Reference existing employee_id, dept_id when linking (see lookup table below)
- Use the provided source_id in every INSERT/UPSERT statement
- Generate unique IDs for NEW records (use max existing ID + 1)
- Extract numbers without commas: 10500 not 10,500
- If employee name is mentioned → find employee_id from lookup table below
- Write to MULTIPLE tables when document contains diverse data types

DON'T:
- Don't use plain UPDATE statements (use UPSERT instead!)
- Don't INSERT into decision_case, case_evidence, decision_output tables
- Don't INSERT into source_document (already created)
- Don't use backticks, use single quotes
- Don't include DEFAULT values explicitly
- Don't add comments in SQL
- Don't make up employee_id that doesn't exist (use NULL if unknown)
- Don't rigidly follow document_type → single table mapping (analyze entities first!)

=================================================
EMPLOYEE LOOKUP REFERENCE (ALL 43 EMPLOYEES):
=================================================

**Use this to map employee names → employee_id when writing to tables**

ENGINEERING (dept_id=101):
- 1001: Ahmad Hassan, 1002: Li Wei, 1003: Priya Kumar, 1004: Tan Jia Hui
- 1005: Omar Sharif, 1006: Chen Yi, 1007: Siti Nurhaliza, 1008: Rajesh Menon
- 1009: Lina Tan, 1010: Hassan Ali, 1011: Kumar Suresh, 1012: Fatimah Wong

SALES (dept_id=102):
- 1020: Sarah Lim, 1021: David Wong, 1022: Alicia Fernandez, 1023: John Tan
- 1024: Muthu Kumar, 1025: Nurul Aisyah, 1026: Tan Mei Ling, 1027: Azman Ibrahim
- 1028: Rebecca Chong, 1029: Vincent Lee

MARKETING (dept_id=103):
- 1030: Zara Khan, 1031: Chen Wei, 1032: Siti Aminah, 1033: Kumar Singh
- 1034: Lisa Tan, 1035: Omar Farid, 1036: Nina Lim

HR (dept_id=104):
- 1037: Fatimah Zahra, 1038: Ahmad Razak, 1039: Priya Devi, 1040: Tan Wei Jie

FINANCE (dept_id=105):
- 1041: James Lim, 1042: Siti Hajar, 1043: Kumar Raj, 1044: Lina Chen
- 1045: Hassan Osman

LEGAL (dept_id=106):
- 1046: David Tan, 1047: Aisha Noor

SUPPLY CHAIN (dept_id=107):
- 1048: Azman Yusof, 1049: Nina Wong, 1050: Kumar Ariff

**Name matching rules:**
- Use partial name match (e.g., "John" matches "John Tan" → 1023)
- If multiple matches, use context (department) to disambiguate
- If no match found, use NULL for employee_id

=================================================
SMART MAPPING EXAMPLES WITH EXISTING DATA:
=================================================

Example 1 - PAYSLIP (MULTI-TABLE WRITE WITH UPSERT):
Input: {
  "document_type": "Employee",
  "department": "HR", 
  "entities": [
    {"type": "Employee", "name": "John Tan"},
    {"type": "Amount", "name": "salary", "value": "10500"},
    {"type": "Date", "name": "period", "value": "2026-04-01"},
    {"type": "Metric", "name": "attendance_days", "value": "62"}
  ]
}

NEXT AVAILABLE IDs PROVIDED:
- hr_record: Start from ID 2050
- finance_record: Start from ID 4050

Existing Data Provided:
- employee: {"employee_id": 1023, "name": "John Tan", "salary": 9500, "role": "Sales Executive", "dept_id": 102, "email": "john.tan@powergrid.my", "hire_date": "2023-08-20"}
- hr_record: [{"employee_id": 1023, "period": "2026-03-01", "attendance_days": 60}]  (No row for 2026-04-01)
- finance_record: [] (No rows)

SMART DECISION: 
1. employee: Row exists → UPSERT to update salary (9500 → 10500)
2. hr_record: No row for period 2026-04-01 → INSERT new with ID 2050
3. finance_record: No existing data → INSERT new with ID 4050

Output (3 statements):
INSERT INTO employee (employee_id, dept_id, name, role, email, hire_date, salary) VALUES (1023, 102, 'John Tan', 'Sales Executive', 'john.tan@powergrid.my', '2023-08-20', 10500.00) ON CONFLICT (employee_id) DO UPDATE SET salary = EXCLUDED.salary;
INSERT INTO hr_record (hr_id, employee_id, period, attendance_days, source_id, ai_justification) VALUES (2050, 1023, '2026-04-01', 62, <SOURCE_ID>, 'Payslip data: attendance 62 days for April 2026, salary increased to RM 10,500');
INSERT INTO finance_record (finance_id, dept_id, employee_id, period, metric_name, amount, category, source_id, ai_justification) VALUES (4050, 102, 1023, '2026-04-01', 'salary', 10500.00, 'personnel', <SOURCE_ID>, 'Salary payment for April 2026: RM 10,500 (10.5% increase from RM 9,500)');

Example 2 - HR RECORD UPDATE (UPSERT for existing period):
Input: {
  "document_type": "HR Report",
  "entities": [
    {"type": "Employee", "name": "Sarah Lim"},
    {"type": "Metric", "name": "performance_score", "value": "4.2"},
    {"type": "Date", "name": "period", "value": "2026-Q1"}
  ]
}

Existing Data Provided:
- hr_record: [{"hr_id": 2001, "employee_id": 1020, "period": "2026-Q1", "performance_score": 3.5, "attendance_days": 60}]

SMART DECISION: Row already exists for (employee_id=1020, period=2026-Q1) → UPSERT to update performance_score

Output:
INSERT INTO hr_record (hr_id, employee_id, period, performance_score, attendance_days, source_id, ai_justification) VALUES (2001, 1020, '2026-Q1', 4.2, 60, <SOURCE_ID>, 'Updated performance score from 3.5 to 4.2 based on latest review document') ON CONFLICT (employee_id, period) DO UPDATE SET performance_score = EXCLUDED.performance_score, ai_justification = EXCLUDED.ai_justification, source_id = EXCLUDED.source_id;

Example 3 - SALES DEAL (FRESH INSERT):
Input: {
  "document_type": "Sales Log",
  "entities": [
    {"type": "Deal", "name": "Enterprise Transformer Deal", "value": "150000"},
    {"type": "Employee", "name": "David Wong"},
    {"type": "Date", "name": "period", "value": "2026-Q2"}
  ]
}

NEXT AVAILABLE IDs PROVIDED:
- sales_record: Start from ID 3089

Existing Data Provided:
- sales_record: [recent records for David Wong, but none for Q2 2026]

SMART DECISION: No existing row for this period → INSERT new with ID 3089

Output:
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, source_id, ai_justification) VALUES (3089, 1021, 102, '2026-Q2', 'Enterprise Transformer Deal', 'Distribution Transformer 1000kVA', 150000.00, 'closed', <SOURCE_ID>, 'Q2 2026 enterprise deal with TNB, 1000kVA transformer supply, closed in April 2026');

Example 4 - PAYSLIP WITH MULTIPLE FINANCE RECORDS (ID INCREMENT):
Input: {
  "document_type": "Employee",
  "entities": [
    {"type": "Employee", "name": "Rajesh Gowda"},
    {"type": "Amount", "name": "basic_salary", "value": "10000"},
    {"type": "Amount", "name": "overtime_payment", "value": "3750"},
    {"type": "Amount", "name": "deductions", "value": "1000"},
    {"type": "Date", "name": "period", "value": "2019-08-01"}
  ]
}

NEXT AVAILABLE IDs PROVIDED:
- hr_record: Start from ID 2089
- finance_record: Start from ID 4078

Existing Data: (No existing records for this period)

SMART DECISION: 
- Need to create MULTIPLE finance_record entries (basic salary, OT, deductions)
- Increment IDs: 4078, 4079, 4080

Output:
INSERT INTO hr_record (hr_id, employee_id, period, attendance_days, source_id, ai_justification) VALUES (2089, 1051, '2019-Q3', 30, <SOURCE_ID>, 'Payslip for August 2019: 30 paid days, 50 OT hours, net pay RM 12,750');
INSERT INTO finance_record (finance_id, dept_id, employee_id, period, metric_name, amount, category, source_id, ai_justification) VALUES (4078, 104, 1051, '2019-Q3', 'salary', 10000.00, 'personnel', <SOURCE_ID>, 'Basic salary for August 2019');
INSERT INTO finance_record (finance_id, dept_id, employee_id, period, metric_name, amount, category, source_id, ai_justification) VALUES (4079, 104, 1051, '2019-Q3', 'overtime_payment', 3750.00, 'personnel', <SOURCE_ID>, 'OT payment: 50 hours at RM 75/hr');
INSERT INTO finance_record (finance_id, dept_id, employee_id, period, metric_name, amount, category, source_id, ai_justification) VALUES (4080, 104, 1051, '2019-Q3', 'deduction', -1000.00, 'personnel', <SOURCE_ID>, 'Salary advance deduction');

NOTE: See how finance_id increments: 4078 → 4079 → 4080 for multiple records!

Example 5 - SUPPLY RECORD UPDATE (UPSERT for existing item+period):
Input: {
  "document_type": "Supply Chain Log",
  "entities": [
    {"type": "Item", "name": "Distribution Transformer 500kVA"},
    {"type": "Metric", "name": "quantity_sold", "value": "85"},
    {"type": "Date", "name": "period", "value": "2026-Q1"}
  ]
}

NEXT AVAILABLE IDs PROVIDED:
- supply_record: Start from ID 5020

Existing Data Provided:
- supply_record: [{"supply_id": 5005, "item_name": "Distribution Transformer 500kVA", "period": "2026-Q1", "quantity_sold": 78}]

SMART DECISION: Same item + same period exists → UPSERT (keep existing supply_id=5005)

Output:
INSERT INTO supply_record (supply_id, item_name, period, quantity_sold, source_id, ai_justification) VALUES (5005, 'Distribution Transformer 500kVA', '2026-Q1', 85, <SOURCE_ID>, 'Updated Q1 2026 sales quantity from 78 to 85 units based on latest supply chain report') ON CONFLICT (item_name, period) DO UPDATE SET quantity_sold = EXCLUDED.quantity_sold, ai_justification = EXCLUDED.ai_justification, source_id = EXCLUDED.source_id;

=================================================
DECISION PROCESS (FOLLOW THIS WORKFLOW):
=================================================

For EACH document, follow these steps IN ORDER:

STEP 1: ANALYZE EXTRACTED ENTITIES
- What employee data do I have? (name, role, salary, email, etc.)
- What transactional data? (performance, sales, finance, marketing, supply, legal)
- What time period? (for periodic tables)
- What custom extraction was requested by user?

STEP 2: CHECK EXISTING DATABASE DATA
**YOU WILL BE PROVIDED WITH EXISTING DATA FROM THE DATABASE**

For each relevant table, you will see:
- Existing rows that match the entity (e.g., employee_id=1023's current data)
- Recent records for this entity (e.g., last 5 periods of hr_record)
- Query type (e.g., "employee_lookup", "hr_history", "duplicate_check")

**ANALYZE THE EXISTING DATA:**
- Does a row ALREADY EXIST for this entity+period?
- Is the data in the document NEWER/DIFFERENT than existing?
- Should I UPDATE existing row or INSERT new row?

STEP 3: IDENTIFY SUITABLE TABLES + DECIDE INSERT vs UPSERT

For each piece of data:

- **CORE employee info** (name, role, salary, email):
  → employee table
  → Check existing: If employee_id exists → UPSERT, else INSERT

- **HR/performance data** (performance_score, attendance, review notes):
  → hr_record
  → Check existing: If (employee_id + period) exists → UPSERT, else INSERT

- **Sales data** (deals, revenue, targets):
  → sales_record
  → Check existing: If (employee_id + period) exists → UPSERT, else INSERT

- **Financial metrics** (revenue, costs, profit):
  → finance_record
  → Check existing: If (employee_id + period) exists → UPSERT, else INSERT

- **Marketing data** (campaigns, metrics):
  → marketing_record
  → Usually INSERT (no unique constraints)

- **Supply/inventory data** (items, quantities, orders):
  → supply_record
  → Check existing: If (item_name + period) exists → UPSERT, else INSERT

- **Legal policy**:
  → legal_policy
  → Check existing: If legal_id exists → UPSERT, else INSERT

- **Contract info**:
  → legal_contract
  → Check existing: If employee_id has contract → UPSERT, else INSERT

- **Employee legal issue**:
  → legal_cases
  → Usually INSERT (new case each time)

STEP 4: USE PROVIDED NEXT AVAILABLE IDs

CRITICAL: You will be given "NEXT AVAILABLE IDs" for each table.

**MANDATORY RULES:**
- NEVER hardcode IDs like hr_id=2001, finance_id=4001
- ALWAYS use the provided next available IDs
- For multiple INSERTs to same table, increment from provided ID:
  * If next finance_id = 4051, use: 4051, 4052, 4053 for multiple records
  * If next hr_id = 2089, use: 2089 for the INSERT

**Example:**
```
NEXT AVAILABLE IDs:
- hr_record: Start from ID 2089
- finance_record: Start from ID 4051
```

Then generate:
```sql
INSERT INTO hr_record (hr_id, ...) VALUES (2089, ...);
INSERT INTO finance_record (finance_id, ...) VALUES (4051, ...);
INSERT INTO finance_record (finance_id, ...) VALUES (4052, ...);  -- Incremented!
INSERT INTO finance_record (finance_id, ...) VALUES (4053, ...);  -- Incremented!
```

STEP 5: GENERATE SQL FOR ALL RELEVANT TABLES
- Start with employee table if updating core data (UPSERT if exists)
- Then add transactional tables (hr_record, sales_record, etc.)
- Use UPSERT if existing data shows row exists
- Use INSERT if no existing row found
- USE THE PROVIDED NEXT IDs FOR NEW RECORDS!
- Each statement on one line
- Use <SOURCE_ID> placeholder
- ALWAYS include ai_justification for tables that have it

STEP 6: MAXIMIZE DATA COVERAGE
- Don't just pick one table - use all that fit!
- A rich document might write to 3-4 tables
- Better to over-write than under-write
- Include custom extraction in ai_justification if requested
- REMEMBER: Use the provided next IDs for all new records!

=================================================
OUTPUT FORMAT:
=================================================

Return ONLY valid SQL INSERT/UPSERT statements, one per line, with <SOURCE_ID> placeholder.
Do NOT include any explanations, comments, or markdown.
Do NOT wrap in ```sql blocks.
Do NOT use plain UPDATE statements (use INSERT ... ON CONFLICT ... DO UPDATE instead).
Just pure SQL statements.

If you cannot generate valid SQL (e.g., insufficient data), return: NO_SQL_POSSIBLE
"""


class DataWriterAgent:
    """
    INTELLIGENT document-to-database writer using multi-step reasoning.
    
    Pipeline:
    1. Analyze extraction JSON
    2. Identify target table(s) based on document type
    3. QUERY existing data from target table(s)
    4. AI decides: INSERT new vs UPDATE existing
    5. Generate + execute SQL with ai_justification
    """
    
    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Missing Supabase credentials")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.zhipu = get_zhipu_client()
        
        # Document type → primary table mapping
        self.doc_type_table_map = {
            "HR Report": "hr_record",
            "Employee": ["employee", "hr_record", "finance_record"],  # Multi-table
            "Sales Log": "sales_record",
            "Finance Report": "finance_record",
            "Marketing Report": "marketing_record",
            "Supply Chain Log": "supply_record",
            "Legal Policy": "legal_policy",
            "Legal Contract": "legal_contract",
            "Legal Case": "legal_cases"
        }
    
    def _get_next_id(self, table_name: str, id_column: str) -> int:
        """Get next available ID for a table"""
        try:
            result = self.supabase.table(table_name)\
                .select(id_column)\
                .order(id_column, desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0][id_column] + 1
            return 1
        except:
            return 1
    
    def _find_employee_by_name(self, name: str) -> Optional[int]:
        """Try to find employee_id by name (fuzzy match)"""
        try:
            result = self.supabase.table("employee")\
                .select("employee_id, name")\
                .ilike("name", f"%{name}%")\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]["employee_id"]
        except:
            pass
        return None
    
    def _get_target_tables(self, doc_type: str) -> List[str]:
        """Get target table(s) for a document type"""
        tables = self.doc_type_table_map.get(doc_type, [])
        if isinstance(tables, str):
            return [tables]
        return tables if tables else []
    
    def _get_next_id(self, table_name: str, id_column: str) -> int:
        """Get the next available ID for a table"""
        try:
            result = self.supabase.table(table_name)\
                .select(id_column)\
                .order(id_column, desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0][id_column] + 1
            
            # Default starting IDs if table is empty
            defaults = {
                "hr_record": 2001,
                "sales_record": 3001,
                "finance_record": 4001,
                "marketing_record": 6001,
                "supply_record": 5001,
                "employee": 1001,
                "legal_policy": 7001,
                "legal_contract": 1,
                "legal_cases": 1
            }
            return defaults.get(table_name, 1)
        except:
            # If query fails, return safe default
            return 9999
    
    def _query_existing_data(self, table_name: str, extraction_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query existing data from target table to help AI decide INSERT vs UPDATE.
        
        Returns relevant existing rows that might need updating.
        """
        try:
            # Extract employee name from entities if present
            employee_name = None
            employee_id = None
            period = None
            item_name = None
            
            entities = extraction_json.get("entities", [])
            for entity in entities:
                if entity.get("type") == "Employee":
                    employee_name = entity.get("name")
                    if employee_name:
                        employee_id = self._find_employee_by_name(employee_name)
                elif entity.get("type") == "Date" and "period" in entity.get("name", "").lower():
                    period = entity.get("value")
                elif entity.get("type") == "Item" or entity.get("name") == "item_name":
                    item_name = entity.get("value")
            
            # Query strategy based on table
            if table_name == "employee" and employee_id:
                # Get existing employee record
                result = self.supabase.table("employee")\
                    .select("*")\
                    .eq("employee_id", employee_id)\
                    .execute()
                return {"existing_rows": result.data, "query_type": "employee_lookup"}
            
            elif table_name == "hr_record" and employee_id:
                # Get recent HR records for this employee (last 3 quarters)
                result = self.supabase.table("hr_record")\
                    .select("*")\
                    .eq("employee_id", employee_id)\
                    .order("period", desc=True)\
                    .limit(5)\
                    .execute()
                return {"existing_rows": result.data, "query_type": "hr_history"}
            
            elif table_name == "sales_record" and employee_id:
                # Get recent sales for this employee
                result = self.supabase.table("sales_record")\
                    .select("*")\
                    .eq("employee_id", employee_id)\
                    .order("period", desc=True)\
                    .limit(10)\
                    .execute()
                return {"existing_rows": result.data, "query_type": "sales_history"}
            
            elif table_name == "finance_record" and employee_id:
                # Get recent finance records for this employee
                result = self.supabase.table("finance_record")\
                    .select("*")\
                    .eq("employee_id", employee_id)\
                    .order("period", desc=True)\
                    .limit(5)\
                    .execute()
                return {"existing_rows": result.data, "query_type": "finance_history"}
            
            elif table_name == "supply_record" and item_name and period:
                # Check if this item+period already exists
                result = self.supabase.table("supply_record")\
                    .select("*")\
                    .eq("item_name", item_name)\
                    .eq("period", period)\
                    .execute()
                return {"existing_rows": result.data, "query_type": "supply_duplicate_check"}
            
            elif table_name == "legal_contract" and employee_id:
                # Check if employee already has a contract
                result = self.supabase.table("legal_contract")\
                    .select("*")\
                    .eq("employee_id", employee_id)\
                    .execute()
                return {"existing_rows": result.data, "query_type": "contract_check"}
            
            elif table_name == "legal_cases" and employee_id:
                # Get existing legal cases for this employee
                result = self.supabase.table("legal_cases")\
                    .select("*")\
                    .eq("employee_id", employee_id)\
                    .execute()
                return {"existing_rows": result.data, "query_type": "legal_case_history"}
            
            else:
                # No specific query strategy - just get recent rows from table
                result = self.supabase.table(table_name)\
                    .select("*")\
                    .order("created_at", desc=True)\
                    .limit(5)\
                    .execute()
                return {"existing_rows": result.data, "query_type": "recent_records"}
        
        except Exception as e:
            # If query fails, return empty (AI will do INSERT)
            return {"existing_rows": [], "query_type": "query_failed", "error": str(e)}
    
    
    def generate_sql_from_extraction(
        self,
        extraction_json: Dict[str, Any],
        source_id: int,
        custom_extraction: Optional[str] = None
    ) -> str:
        """
        INTELLIGENT SQL generation with database-aware decision making.
        
        Multi-step pipeline:
        1. Identify target table(s) from document type
        2. Query existing data from database
        3. AI analyzes: new data vs existing data
        4. AI decides: INSERT new or UPDATE existing (UPSERT)
        5. Generate SQL with ai_justification
        
        Args:
            extraction_json: Output from document_service.py
            source_id: ID of the source_document record
            custom_extraction: Optional user-requested data to extract
        
        Returns:
            SQL INSERT/UPSERT statements as string
        """
        # STEP 1: Identify target tables
        print(f"    [SQL_GEN] STEP 1: Identifying target tables...")
        doc_type = extraction_json.get("document_type", "")
        print(f"    [SQL_GEN]          Document type: {doc_type}")
        target_tables = self._get_target_tables(doc_type)
        
        # If no target tables found, make educated guess based on entities
        if not target_tables:
            print(f"    [SQL_GEN]          No target tables from doc_type, checking entities...")
            # Check if document has employee data - if so, query employee table
            entities = extraction_json.get("entities", [])
            has_employee = any(e.get("type") == "Employee" for e in entities)
            if has_employee:
                target_tables = ["employee"]  # At minimum, check employee table
                print(f"    [SQL_GEN]          Found employee entity, setting target: employee")
        
        print(f"    [SQL_GEN]          Target tables: {target_tables if target_tables else 'AI will decide'}")
        print()
        
        # STEP 2: Query existing data from each target table + get next IDs
        print(f"    [SQL_GEN] STEP 2: Querying existing database records...")
        existing_data_context = {}
        next_ids = {}
        
        for table in target_tables:
            print(f"    [SQL_GEN]          Querying table: {table}")
            existing_data = self._query_existing_data(table, extraction_json)
            existing_data_context[table] = existing_data
            print(f"    [SQL_GEN]          Found {len(existing_data.get('existing_rows', []))} existing rows ({existing_data.get('query_type', 'N/A')})")
            
            # Get next available ID for this table
            id_columns = {
                "hr_record": "hr_id",
                "sales_record": "sales_id",
                "finance_record": "finance_id",
                "marketing_record": "marketing_id",
                "supply_record": "supply_id",
                "employee": "employee_id",
                "legal_policy": "legal_id",
                "legal_contract": "contract_id",
                "legal_cases": "case_id"
            }
            
            if table in id_columns:
                next_id = self._get_next_id(table, id_columns[table])
                next_ids[table] = next_id
                print(f"    [SQL_GEN]          Next available {id_columns[table]}: {next_id}")
        
        print()
        
        # STEP 3: Build user message with extraction + existing data + next IDs
        user_message = f"""
DOCUMENT EXTRACTION DATA:
{json.dumps(extraction_json, indent=2)}

TARGET TABLE(S): {', '.join(target_tables) if target_tables else 'AI to decide'}

NEXT AVAILABLE IDs (USE THESE FOR NEW RECORDS):
"""
        
        for table, next_id in next_ids.items():
            user_message += f"- {table}: Start from ID {next_id}\n"
        
        user_message += """

EXISTING DATABASE DATA:
"""
        
        # Add existing data for each table
        for table, data in existing_data_context.items():
            user_message += f"""
--- Existing rows in `{table}` (query: {data.get('query_type', 'N/A')}) ---
{json.dumps(data.get('existing_rows', []), indent=2)}
"""
        
        user_message += f"""

Source Document ID: {source_id}
"""
        
        # Add custom extraction request if provided
        if custom_extraction and custom_extraction.strip():
            user_message += f"""

USER CUSTOM EXTRACTION REQUEST:
"{custom_extraction}"

CRITICAL INSTRUCTIONS:
1. Extract this data from the document
2. If it fits an existing column → use that column
3. If it doesn't fit → add to ai_justification with format:
   "Custom: {custom_extraction} → [value found]"
4. ALWAYS include custom extraction in ai_justification for audit trail
"""
        
        user_message += """

Generate valid PostgreSQL INSERT statements to write this data to the appropriate table(s).
Replace <SOURCE_ID> placeholder with {source_id}.
""".format(source_id=source_id)
        
        print(f"    [SQL_GEN] STEP 3: Calling Zhipu AI for SQL generation...")
        print(f"    [SQL_GEN]          System prompt length: {len(DATABASE_SCHEMA_PROMPT)} chars")
        print(f"    [SQL_GEN]          User message length: {len(user_message)} chars")
        
        try:
            sql_response = self.zhipu.generate_sql(
                system_prompt=DATABASE_SCHEMA_PROMPT,
                user_message=user_message,
                temperature=0.3  # Low temperature for consistent SQL generation
            )
            
            print(f"    [SQL_GEN] STEP 3: AI response received successfully")
            print()
            
            return sql_response.strip()
        
        except Exception as e:
            print(f"    [SQL_GEN] STEP 3: FAILED - Zhipu AI error: {str(e)}")
            print()
            raise Exception(f"Failed to generate SQL: {str(e)}")
    
    def execute_sql_statements(self, sql_statements: str) -> Dict[str, Any]:
        """
        Execute generated SQL statements against Supabase
        
        Args:
            sql_statements: SQL INSERT statements to execute
        
        Returns:
            Execution results with success status
        """
        print(f"    [SQL_EXEC] Starting SQL execution...")
        
        if not sql_statements or sql_statements == "NO_SQL_POSSIBLE":
            print(f"    [SQL_EXEC] FAILED - No SQL to execute")
            return {
                "success": False,
                "error": "No valid SQL could be generated from extraction data",
                "rows_inserted": 0
            }
        
        # Split multiple statements (one per line)
        statements = [s.strip() for s in sql_statements.split('\n') if s.strip() and not s.strip().startswith('--')]
        
        print(f"    [SQL_EXEC] Found {len(statements)} SQL statements to execute")
        
        results = []
        rows_inserted = 0
        
        for idx, statement in enumerate(statements, 1):
            print(f"    [SQL_EXEC] Executing statement {idx}/{len(statements)}...")
            try:
                # Parse INSERT statement (with or without ON CONFLICT)
                # Format: INSERT INTO table_name (col1, col2, ...) VALUES (val1, val2, ...) [ON CONFLICT ...]
                import re
                
                # Check if this is an UPSERT (has ON CONFLICT)
                has_conflict = 'ON CONFLICT' in statement.upper()
                
                # Extract table name
                table_match = re.search(r'INSERT INTO (\w+)', statement, re.IGNORECASE)
                if not table_match:
                    raise ValueError("Could not parse table name from SQL")
                
                table_name = table_match.group(1)
                print(f"    [SQL_EXEC]     Target table: {table_name}")
                
                # Extract columns
                columns_match = re.search(r'\(([^)]+)\)\s*VALUES', statement, re.IGNORECASE)
                if not columns_match:
                    raise ValueError("Could not parse columns from SQL")
                
                columns = [c.strip() for c in columns_match.group(1).split(',')]
                
                # Extract values (stop at ON CONFLICT if present)
                if has_conflict:
                    values_match = re.search(r'VALUES\s*\(([^)]+)\)\s*ON CONFLICT', statement, re.IGNORECASE)
                else:
                    values_match = re.search(r'VALUES\s*\(([^)]+)\)', statement, re.IGNORECASE)
                    
                if not values_match:
                    raise ValueError("Could not parse values from SQL")
                
                values_str = values_match.group(1)
                
                # Parse values (handle strings, numbers, NULL)
                values = []
                current = ""
                in_string = False
                
                for char in values_str:
                    if char == "'" and (not current or current[-1] != '\\'):
                        in_string = not in_string
                    elif char == ',' and not in_string:
                        values.append(current.strip())
                        current = ""
                        continue
                    current += char
                
                if current.strip():
                    values.append(current.strip())
                
                # Convert values to proper types
                parsed_values = []
                for val in values:
                    val = val.strip()
                    if val.upper() == 'NULL':
                        parsed_values.append(None)
                    elif val.startswith("'") and val.endswith("'"):
                        parsed_values.append(val[1:-1])  # String
                    else:
                        try:
                            # Try to parse as number
                            if '.' in val:
                                parsed_values.append(float(val))
                            else:
                                parsed_values.append(int(val))
                        except:
                            parsed_values.append(val)
                
                # Create data dictionary
                data = dict(zip(columns, parsed_values))
                
                # Execute insert or upsert via Supabase
                if has_conflict:
                    # UPSERT: Use Supabase's upsert method
                    print(f"    [SQL_EXEC]     Operation: UPSERT")
                    result = self.supabase.table(table_name).upsert(data).execute()
                    print(f"    [SQL_EXEC]     SUCCESS - UPSERT completed")
                    results.append({
                        "statement": statement[:100] + "..." if len(statement) > 100 else statement,
                        "success": True,
                        "table": table_name,
                        "operation": "upsert"
                    })
                else:
                    # Regular INSERT
                    print(f"    [SQL_EXEC]     Operation: INSERT")
                    result = self.supabase.table(table_name).insert(data).execute()
                    print(f"    [SQL_EXEC]     SUCCESS - INSERT completed")
                    results.append({
                        "statement": statement[:100] + "..." if len(statement) > 100 else statement,
                        "success": True,
                        "table": table_name,
                        "operation": "insert"
                    })
                rows_inserted += 1
                
            except Exception as e:
                print(f"    [SQL_EXEC]     FAILED - Error: {str(e)}")
                results.append({
                    "statement": statement[:100] + "..." if len(statement) > 100 else statement,
                    "success": False,
                    "error": str(e)
                })
        
        # Collect all errors for summary
        errors = [r.get("error") for r in results if not r.get("success", False)]
        error_summary = "; ".join(errors) if errors else None
        
        return {
            "success": rows_inserted > 0,
            "rows_inserted": rows_inserted,
            "total_statements": len(statements),
            "details": results,
            "error": error_summary  # Add top-level error field
        }
    
    def process_document_extraction(
        self,
        extraction_json: Dict[str, Any],
        source_id: int,
        custom_extraction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete flow: Generate SQL → Execute → Return results
        
        Args:
            extraction_json: Document extraction from Zhipu AI (document_service)
            source_id: Source document ID
            custom_extraction: Optional user-requested data to extract
        
        Returns:
            Processing results
        """
        print("    [DATA_WRITER] Starting process_document_extraction()")
        print(f"    [DATA_WRITER] source_id: {source_id}")
        print(f"    [DATA_WRITER] document_type: {extraction_json.get('document_type')}")
        print(f"    [DATA_WRITER] entities_count: {len(extraction_json.get('entities', []))}")
        print(f"    [DATA_WRITER] custom_extraction: {custom_extraction if custom_extraction else 'None'}")
        
        # Warn if no entities
        if len(extraction_json.get('entities', [])) == 0:
            print(f"    [DATA_WRITER] ⚠️  WARNING: No entities in extraction_json!")
            print(f"    [DATA_WRITER]     AI will likely return NO_SQL_POSSIBLE")
        
        try:
            # Step 1: Generate SQL (with custom extraction if provided)
            print(f"    [DATA_WRITER] Step 1: Generating SQL with Zhipu AI...")
            sql_statements = self.generate_sql_from_extraction(
                extraction_json, 
                source_id,
                custom_extraction
            )
            
            print(f"    [DATA_WRITER] SQL generated successfully:")
            print(f"    [DATA_WRITER] ---SQL START---")
            for line in sql_statements.split('\n'):
                if line.strip():
                    print(f"    [DATA_WRITER] {line}")
            print(f"    [DATA_WRITER] ---SQL END---")
            print()
            
            # Step 2: Execute SQL
            print(f"    [DATA_WRITER] Step 2: Executing SQL statements...")
            execution_results = self.execute_sql_statements(sql_statements)
            
            if execution_results["success"]:
                print(f"    [DATA_WRITER] SQL execution SUCCESS")
                print(f"    [DATA_WRITER] Rows inserted/updated: {execution_results.get('rows_inserted', 0)}")
            else:
                print(f"    [DATA_WRITER] SQL execution FAILED")
                print(f"    [DATA_WRITER] Error: {execution_results.get('error', 'Unknown')}")
            print()
            
            return {
                "success": execution_results["success"],
                "source_id": source_id,
                "extraction_summary": {
                    "document_type": extraction_json.get("document_type"),
                    "department": extraction_json.get("department"),
                    "entities_count": len(extraction_json.get("entities", []))
                },
                "sql_generated": sql_statements,
                "execution_results": execution_results
            }
        
        except Exception as e:
            print(f"    [DATA_WRITER] EXCEPTION in process_document_extraction:")
            print(f"    [DATA_WRITER] Error: {str(e)}")
            import traceback
            print(f"    [DATA_WRITER] Traceback:")
            for line in traceback.format_exc().split('\n'):
                print(f"    [DATA_WRITER] {line}")
            print()
            
            return {
                "success": False,
                "source_id": source_id,
                "error": str(e),
                "extraction_summary": {
                    "document_type": extraction_json.get("document_type"),
                    "department": extraction_json.get("department")
                }
            }


# Singleton instance
_agent = None

def get_data_writer_agent() -> DataWriterAgent:
    """Get or create DataWriterAgent instance"""
    global _agent
    if _agent is None:
        _agent = DataWriterAgent()
    return _agent
