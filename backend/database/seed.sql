-- AI Boss Decision Engine - Seed Data (Single Company: PowerGrid Solutions)
-- Rich, properly-linked data with realistic IDs and cross-table relationships
-- PostgreSQL / Supabase compatible
-- ELECTRICAL DISTRIBUTION & RESALE COMPANY

-- ============================================
-- CLEAR ALL EXISTING DATA (CASCADE)
-- ============================================
TRUNCATE TABLE decision_output CASCADE;
TRUNCATE TABLE case_evidence CASCADE;
TRUNCATE TABLE decision_case CASCADE;
TRUNCATE TABLE legal_policy CASCADE;
TRUNCATE TABLE legal_contract CASCADE;
TRUNCATE TABLE legal_cases CASCADE;
TRUNCATE TABLE supply_record CASCADE;
TRUNCATE TABLE marketing_record CASCADE;
TRUNCATE TABLE finance_record CASCADE;
TRUNCATE TABLE sales_record CASCADE;
TRUNCATE TABLE hr_record CASCADE;
TRUNCATE TABLE source_document CASCADE;
TRUNCATE TABLE employee CASCADE;
TRUNCATE TABLE department CASCADE;

-- ============================================
-- DEPARTMENTS (aligned with agent structure)
-- ============================================
INSERT INTO department (dept_id, name, description) VALUES
(101, 'Engineering', 'Electrical installation and technical support'),
(102, 'Sales', 'B2B electrical equipment sales and client relations'),
(103, 'Marketing', 'Industrial marketing and brand positioning'),
(104, 'HR', 'Human resources and talent'),
(105, 'Finance', 'Financial planning and accounting'),
(106, 'Legal', 'Legal compliance and contracts'),
(107, 'Supply Chain', 'Electrical equipment procurement and distribution');

-- ============================================
-- EMPLOYEES (40+ employees across departments)
-- ============================================

-- Engineering (dept 101) - 12 employees
INSERT INTO employee (employee_id, dept_id, name, role, email, hire_date, salary) VALUES
(1001, 101, 'Ahmad Hassan', 'Senior Electrical Engineer', 'ahmad.hassan@powergrid.my', '2022-03-15', 12500.00),
(1002, 101, 'Li Wei', 'Installation Engineer', 'li.wei@powergrid.my', '2023-01-10', 9800.00),
(1003, 101, 'Priya Kumar', 'Technical Services Lead', 'priya.kumar@powergrid.my', '2021-06-01', 14200.00),
(1004, 101, 'Tan Jia Hui', 'Electrical Systems Engineer', 'jia.hui@powergrid.my', '2023-08-20', 10500.00),
(1005, 101, 'Omar Sharif', 'Switchgear Specialist', 'omar.sharif@powergrid.my', '2022-11-12', 11000.00),
(1006, 101, 'Chen Yi', 'Quality Assurance Engineer', 'chen.yi@powergrid.my', '2023-02-14', 8500.00),
(1007, 101, 'Siti Nurhaliza', 'Solar Systems Engineer', 'siti.nur@powergrid.my', '2022-09-01', 10800.00),
(1008, 101, 'Rajesh Menon', 'Engineering Manager', 'rajesh.menon@powergrid.my', '2020-05-10', 16500.00),
(1009, 101, 'Lina Tan', 'Junior Installation Engineer', 'lina.tan@powergrid.my', '2024-01-15', 9200.00),
(1010, 101, 'Hassan Ali', 'Power Distribution Specialist', 'hassan.ali@powergrid.my', '2023-06-20', 10200.00),
(1011, 101, 'Kumar Suresh', 'Automation Engineer', 'kumar.suresh@powergrid.my', '2022-07-03', 11800.00),
(1012, 101, 'Fatimah Wong', 'Senior Electrical Engineer', 'fatimah.wong@powergrid.my', '2021-10-18', 13500.00);

-- Sales (dept 102) - 10 employees (includes underperformer John Tan #1023)
INSERT INTO employee (employee_id, dept_id, name, role, email, hire_date, salary) VALUES
(1020, 102, 'Sarah Lim', 'Sales Director', 'sarah.lim@powergrid.my', '2020-11-05', 18000.00),
(1021, 102, 'David Wong', 'Enterprise Sales Executive', 'david.wong@powergrid.my', '2023-02-14', 11500.00),
(1022, 102, 'Alicia Fernandez', 'SMB Sales Executive', 'alicia.f@powergrid.my', '2022-04-10', 10200.00),
(1023, 102, 'John Tan', 'Sales Executive', 'john.tan@powergrid.my', '2023-08-20', 10500.00), -- UNDERPERFORMER (main case)
(1024, 102, 'Muthu Kumar', 'Enterprise Account Manager', 'muthu.kumar@powergrid.my', '2021-07-18', 13800.00),
(1025, 102, 'Nurul Aisyah', 'Sales Manager', 'nurul.aisyah@powergrid.my', '2022-01-12', 15000.00),
(1026, 102, 'Tan Mei Ling', 'SMB Sales Executive', 'mei.ling@powergrid.my', '2023-09-05', 9800.00),
(1027, 102, 'Azman Ibrahim', 'Enterprise Sales Executive', 'azman.ib@powergrid.my', '2022-06-22', 12200.00),
(1028, 102, 'Rebecca Chong', 'Sales Operations Specialist', 'rebecca.chong@powergrid.my', '2023-03-10', 8900.00),
(1029, 102, 'Vincent Lee', 'Sales Development Rep', 'vincent.lee@powergrid.my', '2024-02-01', 7500.00);

-- Marketing (dept 103) - 7 employees
INSERT INTO employee (employee_id, dept_id, name, role, email, hire_date, salary) VALUES
(1030, 103, 'Zara Khan', 'Marketing Director', 'zara.khan@powergrid.my', '2021-03-08', 16500.00),
(1031, 103, 'Chen Wei', 'Industrial Marketing Manager', 'chen.wei@powergrid.my', '2022-05-12', 11000.00),
(1032, 103, 'Siti Aminah', 'Digital Marketing Specialist', 'siti.aminah@powergrid.my', '2023-01-20', 9200.00),
(1033, 103, 'Kumar Singh', 'Trade Show Specialist', 'kumar.singh@powergrid.my', '2022-09-15', 9800.00),
(1034, 103, 'Lisa Tan', 'Graphic Designer', 'lisa.tan@powergrid.my', '2023-07-01', 8500.00),
(1035, 103, 'Omar Farid', 'Marketing Analyst', 'omar.farid@powergrid.my', '2023-11-10', 8900.00),
(1036, 103, 'Nina Lim', 'Social Media Manager', 'nina.lim@powergrid.my', '2024-01-05', 8200.00);

-- HR (dept 104) - 4 employees
INSERT INTO employee (employee_id, dept_id, name, role, email, hire_date, salary) VALUES
(1037, 104, 'Fatimah Zahra', 'HR Director', 'fatimah.zahra@powergrid.my', '2020-03-01', 15500.00),
(1038, 104, 'Ahmad Razak', 'HR Manager', 'ahmad.razak@powergrid.my', '2021-08-15', 12000.00),
(1039, 104, 'Priya Devi', 'Talent Acquisition Specialist', 'priya.devi@powergrid.my', '2022-06-20', 9500.00),
(1040, 104, 'Tan Wei Jie', 'HR Coordinator', 'wei.jie@powergrid.my', '2023-10-01', 7800.00);

-- Finance (dept 105) - 5 employees
INSERT INTO employee (employee_id, dept_id, name, role, email, hire_date, salary) VALUES
(1041, 105, 'James Lim', 'CFO', 'james.lim@powergrid.my', '2019-09-15', 22000.00),
(1042, 105, 'Siti Hajar', 'Finance Manager', 'siti.hajar@powergrid.my', '2021-04-10', 13500.00),
(1043, 105, 'Kumar Raj', 'Senior Accountant', 'kumar.raj@powergrid.my', '2022-02-18', 10500.00),
(1044, 105, 'Lina Chen', 'Financial Analyst', 'lina.chen@powergrid.my', '2023-05-22', 9200.00),
(1045, 105, 'Hassan Osman', 'Accounts Payable Specialist', 'hassan.osman@powergrid.my', '2023-09-12', 7500.00);

-- Legal (dept 106) - 2 employees
INSERT INTO employee (employee_id, dept_id, name, role, email, hire_date, salary) VALUES
(1046, 106, 'David Tan', 'General Counsel', 'david.tan@powergrid.my', '2020-07-01', 18500.00),
(1047, 106, 'Aisha Noor', 'Legal Associate', 'aisha.noor@powergrid.my', '2022-11-15', 10800.00);

-- Supply Chain (dept 107) - 3 employees
INSERT INTO employee (employee_id, dept_id, name, role, email, hire_date, salary) VALUES
(1048, 107, 'Azman Yusof', 'Procurement Manager', 'azman.yusof@powergrid.my', '2021-05-20', 12500.00),
(1049, 107, 'Nina Wong', 'Vendor Relations Specialist', 'nina.wong@powergrid.my', '2022-08-10', 9000.00),
(1050, 107, 'Kumar Ariff', 'Supply Chain Analyst', 'kumar.ariff@powergrid.my', '2023-12-01', 8800.00);

-- ============================================
-- SOURCE DOCUMENTS (~25 documents)
-- ============================================
INSERT INTO source_document (source_id, doc_type, title, published_date, file_path, extracted_at) VALUES
(501, 'HR Report', 'Q4 2025 Performance Reviews', '2025-12-20', '/data/uploads/hr_q4_2025.pdf', '2025-12-21 09:30:00'),
(502, 'HR Report', 'Q1 2026 Performance Reviews', '2026-04-01', '/data/uploads/hr_q1_2026.pdf', '2026-04-02 10:15:00'),
(503, 'Sales Log', 'CRM Export Q4 2025', '2025-12-28', '/data/uploads/crm_q4_2025.csv', '2025-12-29 08:00:00'),
(504, 'Sales Log', 'CRM Export Q1 2026', '2026-04-05', '/data/uploads/crm_q1_2026.csv', '2026-04-06 07:45:00'),
(505, 'Finance Report', 'FY2025 Salary Audit', '2026-01-15', '/data/uploads/salary_audit_2025.xlsx', '2026-01-16 14:20:00'),
(506, 'Finance Report', 'Q1 2026 Department Budgets', '2026-04-10', '/data/uploads/budget_q1_2026.xlsx', '2026-04-11 09:00:00'),
(507, 'Legal Policy', 'Employee Termination Policy v3.1', '2025-06-01', '/data/uploads/termination_policy_v3.pdf', '2025-06-02 10:00:00'),
(508, 'Legal Policy', 'Performance Improvement Plan Guidelines', '2025-07-15', '/data/uploads/pip_guidelines.pdf', '2025-07-16 11:30:00'),
(509, 'Marketing Report', 'Q4 2025 Campaign Performance', '2025-12-31', '/data/uploads/marketing_q4_2025.pdf', '2026-01-02 08:30:00'),
(510, 'Marketing Report', 'Q1 2026 Campaign Performance', '2026-04-08', '/data/uploads/marketing_q1_2026.pdf', '2026-04-09 09:15:00'),
(511, 'Supply Chain Log', 'Q4 2025 Procurement Report', '2025-12-30', '/data/uploads/procurement_q4_2025.csv', '2025-12-31 10:00:00'),
(512, 'Supply Chain Log', 'Q1 2026 Inventory Status', '2026-03-31', '/data/uploads/inventory_q1_2026.csv', '2026-04-01 08:00:00'),
(513, 'HR Report', 'Q3 2025 Performance Reviews', '2025-09-30', '/data/uploads/hr_q3_2025.pdf', '2025-10-01 09:00:00'),
(514, 'Sales Log', 'CRM Export Q3 2025', '2025-09-28', '/data/uploads/crm_q3_2025.csv', '2025-09-29 08:15:00'),
(515, 'Finance Report', 'Q3 2025 Financial Summary', '2025-10-10', '/data/uploads/finance_q3_2025.xlsx', '2025-10-11 10:30:00'),
(516, 'Legal Policy', 'Market Expansion Legal Framework', '2025-11-20', '/data/uploads/expansion_legal.pdf', '2025-11-21 09:45:00'),
(517, 'Legal Policy', 'Severance Calculation Guidelines', '2025-06-15', '/data/uploads/severance_calc.pdf', '2025-06-16 10:00:00'),
(518, 'HR Report', 'Employee Warning Letters 2025', '2025-11-30', '/data/uploads/warnings_2025.pdf', '2025-12-01 08:30:00'),
(519, 'Sales Log', 'Lost Deals Analysis Q4 2025', '2026-01-10', '/data/uploads/lost_deals_q4.csv', '2026-01-11 09:00:00'),
(520, 'Marketing Report', 'Q3 2025 Campaign Performance', '2025-10-05', '/data/uploads/marketing_q3_2025.pdf', '2025-10-06 09:30:00'),
(521, 'Supply Chain Log', 'Vendor Performance Q1 2026', '2026-04-12', '/data/uploads/vendor_q1_2026.csv', '2026-04-13 08:45:00'),
(522, 'Finance Report', 'Replacement Cost Analysis', '2026-02-20', '/data/uploads/replacement_costs.xlsx', '2026-02-21 10:00:00'),
(523, 'HR Report', 'Exit Interview Summary 2025', '2026-01-20', '/data/uploads/exit_interviews_2025.pdf', '2026-01-21 09:15:00'),
(524, 'Sales Log', 'Pipeline Health Report Q1 2026', '2026-04-15', '/data/uploads/pipeline_q1_2026.csv', '2026-04-16 08:00:00'),
(525, 'Legal Policy', 'Data Privacy Compliance Guidelines', '2025-08-01', '/data/uploads/data_privacy.pdf', '2025-08-02 10:30:00');

-- ============================================
-- HR RECORDS (~42 records - performance reviews for active employees)
-- ============================================

-- John Tan (1023) - UNDERPERFORMER (main case target)
INSERT INTO hr_record (hr_id, employee_id, period, attendance_days, absence_days, performance_score, performance_summary, warning_count, pip_status, review_date, reviewer_id, ai_justification, source_id) VALUES
(2001, 1023, '2025-Q3', 62, 3, 2.8, 'Performance below expectations. Missed Q3 sales target by 45%. Limited client engagement.', 0, NULL, '2025-09-25', 1025, 'Performance score 2.8/5 indicates below-standard work quality. Sales targets missed by significant margin (45%) suggesting lack of execution. Limited client engagement shows potential motivation or capability issues.', 513),
(2002, 1023, '2025-Q4', 58, 7, 2.1, 'Performance declining. Zero deals closed in Q4. Multiple customer complaints received. Attendance issues emerging.', 1, NULL, '2025-12-18', 1025, 'Severe performance decline from 2.8 to 2.1. Zero closed deals indicates critical sales capability failure. Customer complaints and attendance issues (7 absence days) show systemic problems requiring immediate intervention.', 501),
(2003, 1023, '2026-Q1', 61, 4, 2.0, 'No improvement observed. Performance review score 2.0/5. Pipeline remains thin. Team morale impact noted. PIP recommended but not yet initiated.', 2, NULL, '2026-03-28', 1020, 'Sustained underperformance across 3 consecutive quarters (2.8→2.1→2.0). Two warnings issued. Thin pipeline indicates ongoing failure to generate opportunities. Team morale impact suggests negative spillover effects. PIP recommendation signals escalation to formal remediation process.', 502);

-- Sarah Lim (1020) - Sales Director - High performer
INSERT INTO hr_record (hr_id, employee_id, period, attendance_days, performance_score, performance_summary, warning_count, review_date, reviewer_id, ai_justification, source_id) VALUES
(2004, 1020, '2025-Q4', 63, 4.8, 'Exceptional leadership. Team exceeded targets by 22%. Strong strategic vision.', 0, '2025-12-19', 1037, 'Exceptional rating (4.8/5) reflects consistent excellence. Team overperformance (122% of target) demonstrates effective leadership. Strategic vision indicates high-level thinking and planning capabilities.', 501),
(2005, 1020, '2026-Q1', 64, 4.9, 'Outstanding quarter. Led enterprise expansion initiative. Promoted to Sales Director.', 0, '2026-03-29', 1037, 'Near-perfect score (4.9/5) shows elite performance tier. Enterprise expansion leadership demonstrates strategic project management. Promotion to Director validates sustained high performance and leadership capability.', 502);

-- David Wong (1021) - Strong performer
INSERT INTO hr_record (hr_id, employee_id, period, attendance_days, performance_score, performance_summary, warning_count, review_date, reviewer_id, ai_justification, source_id) VALUES
(2006, 1021, '2025-Q4', 62, 4.2, 'Exceeds expectations. Closed 2 major enterprise deals. Strong pipeline management.', 0, '2025-12-19', 1025, 'Score 4.2/5 places in "exceeds expectations" category. Two major enterprise deals closed demonstrates strong closing ability. Pipeline management strength indicates sustainable performance.', 501),
(2007, 1021, '2026-Q1', 63, 4.3, 'Consistently strong performer. Enterprise segment specialist.', 0, '2026-03-29', 1020, 'Consistent high performance (4.2→4.3) shows reliability. Enterprise specialization creates strategic value. Stable excellence across quarters indicates mature professional capability.', 502);

-- Other sales team members (varied performance)
INSERT INTO hr_record (hr_id, employee_id, period, attendance_days, performance_score, performance_summary, warning_count, review_date, reviewer_id, ai_justification, source_id) VALUES
(2008, 1022, '2026-Q1', 63, 3.8, 'Meets expectations. SMB focus delivering steady results.', 0, '2026-03-29', 1025, 'Score 3.8/5 is solid "meets expectations" performance. SMB specialization with steady results shows consistency. Reliable contributor to team revenue.', 502),
(2009, 1024, '2026-Q1', 64, 4.1, 'Strong account management. High customer retention.', 0, '2026-03-29', 1020, 'Score 4.1/5 indicates strong performance. Account management excellence creates recurring revenue stability. High retention rates reduce customer acquisition costs.', 502),
(2010, 1025, '2026-Q1', 63, 4.5, 'Excellent management skills. Team hitting targets consistently.', 0, '2026-03-29', 1020, 'High management score (4.5/5) reflects effective team leadership. Consistent target achievement shows predictable execution. Management capability enables team scaling.', 502),
(2011, 1026, '2026-Q1', 62, 3.6, 'Meets expectations. New hire ramping well.', 0, '2026-03-29', 1025, 'Score 3.6/5 is acceptable for new hire (6 months tenure). Positive ramp trajectory suggests successful onboarding. Meets baseline expectations for experience level.', 502),
(2012, 1027, '2026-Q1', 64, 4.0, 'Solid performer. Enterprise deals pipeline healthy.', 0, '2026-03-29', 1020, 'Score 4.0/5 indicates reliable "exceeds expectations" performance. Healthy enterprise pipeline suggests sustained future revenue. Solid contributor without being exceptional.', 502),
(2013, 1028, '2026-Q1', 63, 3.9, 'Reliable ops support. Process improvements implemented.', 0, '2026-03-29', 1020, 'Score 3.9/5 for ops role shows effective operational support. Process improvements add structural value. Reliable execution enables sales team efficiency.', 502),
(2014, 1029, '2026-Q1', 61, 3.2, 'Acceptable for SDR role. Lead gen targets mostly met.', 0, '2026-03-29', 1025, 'Score 3.2/5 is adequate for junior SDR role (3 months tenure). "Mostly met" targets indicates room for improvement. Entry-level performance with growth potential.', 502);

-- Engineering team (select members)
INSERT INTO hr_record (hr_id, employee_id, period, attendance_days, performance_score, performance_summary, warning_count, review_date, reviewer_id, ai_justification, source_id) VALUES
(2015, 1001, '2026-Q1', 62, 4.2, 'Strong technical contributions. Delivered 3 major installation projects on time.', 0, '2026-03-30', 1008, 'Score 4.2/5 reflects strong technical execution. Three on-time major projects demonstrates reliability. Electrical engineering expertise drives installation quality.', 502),
(2016, 1002, '2026-Q1', 63, 3.9, 'Good installation work. Collaborative team player.', 0, '2026-03-30', 1008, 'Score 3.9/5 shows solid performance. Collaboration strength adds team value. Installation quality meets standards consistently.', 502),
(2017, 1003, '2026-Q1', 64, 4.8, 'Outstanding technical services improvements. Reduced downtime by 40%. Promotion recommended.', 0, '2026-03-30', 1008, 'Exceptional score (4.8/5) demonstrates elite technical capability. 40% downtime reduction shows measurable operational impact. Promotion recommendation indicates readiness for leadership role.', 502),
(2018, 1004, '2026-Q1', 61, 3.7, 'Solid contributor. Some mentoring needed on complex systems.', 0, '2026-03-30', 1008, 'Score 3.7/5 shows competent performance with development areas. Mentoring need indicates mid-level capability. Solid contributor with growth trajectory.', 502),
(2019, 1005, '2026-Q1', 63, 4.1, 'Reliable switchgear specialist. Clean installation practices.', 0, '2026-03-30', 1008, 'Score 4.1/5 indicates strong specialized expertise. Switchgear focus creates niche value. Clean practices demonstrate professional standards.', 502),
(2020, 1006, '2026-Q1', 62, 3.8, 'Good QA coverage. Testing processes progressing.', 0, '2026-03-30', 1008, 'Score 3.8/5 shows effective quality assurance work. Testing process development adds systematic value. QA coverage ensures installation reliability.', 502),
(2021, 1007, '2026-Q1', 63, 4.0, 'Solar systems progress on track. Green energy expertise strong.', 0, '2026-03-30', 1008, 'Score 4.0/5 reflects solid solar specialization. Green energy expertise aligns with market trends. Project tracking shows reliable execution.', 502),
(2022, 1008, '2026-Q1', 64, 4.6, 'Excellent engineering leadership. Team productivity improving.', 0, '2026-03-30', 1037, 'High leadership score (4.6/5) demonstrates effective management. Team productivity gains show leadership impact. Engineering excellence enables project delivery.', 502),
(2023, 1009, '2026-Q1', 59, 3.4, 'New hire. Ramping up installation skills. Needs technical guidance.', 0, '2026-03-30', 1008, 'Score 3.4/5 acceptable for new hire (3 months tenure). Technical guidance need indicates learning phase. Ramp trajectory suggests potential.', 502),
(2024, 1010, '2026-Q1', 63, 3.9, 'Good power distribution work. System design solid.', 0, '2026-03-30', 1008, 'Score 3.9/5 shows competent power distribution expertise. System design quality demonstrates technical understanding. Reliable specialist contributor.', 502),
(2025, 1011, '2026-Q1', 62, 4.3, 'Strong automation engineering. System efficiency improved.', 0, '2026-03-30', 1008, 'Score 4.3/5 reflects strong automation capability. Efficiency improvements create operational value. Technical innovation drives competitive advantage.', 502),
(2026, 1012, '2026-Q1', 64, 4.4, 'Senior electrical engineering leadership. Mentoring junior engineers effectively.', 0, '2026-03-30', 1008, 'High senior score (4.4/5) validates technical expertise. Mentoring effectiveness multiplies team capability. Leadership strength enables knowledge transfer.', 502);

-- Marketing team
INSERT INTO hr_record (hr_id, employee_id, period, attendance_days, performance_score, performance_summary, warning_count, review_date, reviewer_id, ai_justification, source_id) VALUES
(2027, 1030, '2026-Q1', 63, 4.5, 'Strong marketing leadership. Campaign ROI improved 18% YoY.', 0, '2026-03-31', 1037, 'High score (4.5/5) reflects exceptional marketing leadership. 18% ROI improvement demonstrates measurable business impact. Strategic marketing drives lead generation.', 502),
(2028, 1031, '2026-Q1', 62, 4.1, 'Excellent industrial marketing strategy. Lead gen up 25%.', 0, '2026-03-31', 1030, 'Score 4.1/5 shows strong industrial marketing expertise. 25% lead gen increase creates sales pipeline value. B2B marketing effectiveness drives revenue growth.', 502),
(2029, 1032, '2026-Q1', 63, 3.8, 'Digital campaigns performing well. Good analytics skills.', 0, '2026-03-31', 1030, 'Score 3.8/5 indicates solid digital marketing execution. Analytics skills enable data-driven optimization. Campaign performance shows effective channel management.', 502),
(2030, 1033, '2026-Q1', 61, 3.9, 'Trade show management improving. Industry presence up 12%.', 0, '2026-03-31', 1030, 'Score 3.9/5 reflects effective trade show execution. 12% industry presence increase builds brand awareness. B2B networking creates partnership opportunities.', 502),
(2031, 1034, '2026-Q1', 62, 3.7, 'Good design work. Brand consistency maintained.', 0, '2026-03-31', 1030, 'Score 3.7/5 shows competent design capability. Brand consistency protects company identity. Visual quality supports professional positioning.', 502),
(2032, 1035, '2026-Q1', 63, 4.0, 'Analytics insights valuable for campaign optimization.', 0, '2026-03-31', 1030, 'Score 4.0/5 indicates strong analytical capability. Insights-driven optimization improves marketing efficiency. Data analysis enables strategic decisions.', 502),
(2033, 1036, '2026-Q1', 60, 3.5, 'New hire. Social media engagement improving.', 0, '2026-03-31', 1030, 'Score 3.5/5 acceptable for new hire (3 months tenure). Engagement improvement shows learning progress. Social media presence builds brand awareness.', 502);

-- HR, Finance, Legal, Supply Chain teams
INSERT INTO hr_record (hr_id, employee_id, period, attendance_days, performance_score, performance_summary, warning_count, review_date, reviewer_id, ai_justification, source_id) VALUES
(2034, 1037, '2026-Q1', 64, 4.7, 'Excellent HR leadership. Talent retention strong.', 0, '2026-04-01', 1041, 'High HR leadership score (4.7/5) reflects organizational excellence. Strong retention rates reduce hiring costs. People management creates cultural stability.', 502),
(2035, 1038, '2026-Q1', 63, 4.2, 'Strong HR management. PIP process improvements implemented.', 0, '2026-04-01', 1037, 'Score 4.2/5 shows effective HR management. PIP process improvements add structural rigor. Performance management systems enable accountability.', 502),
(2036, 1039, '2026-Q1', 62, 3.9, 'Good recruiting outcomes. Time-to-hire reduced.', 0, '2026-04-01', 1037, 'Score 3.9/5 reflects solid recruiting effectiveness. Reduced time-to-hire improves operational efficiency. Talent pipeline management supports growth.', 502),
(2037, 1041, '2026-Q1', 64, 4.8, 'Outstanding financial leadership. Q1 profitability ahead of plan.', 0, '2026-04-01', 1037, 'Exceptional CFO score (4.8/5) demonstrates financial excellence. Ahead-of-plan profitability shows strong fiscal management. Strategic finance enables business growth.', 502),
(2038, 1042, '2026-Q1', 63, 4.3, 'Strong finance management. Budget controls effective.', 0, '2026-04-01', 1041, 'Score 4.3/5 reflects strong financial management. Effective budget controls protect profitability. Financial discipline enables predictable operations.', 502),
(2039, 1046, '2026-Q1', 63, 4.6, 'Excellent legal guidance. Compliance initiatives on track.', 0, '2026-04-01', 1037, 'High legal score (4.6/5) shows exceptional counsel quality. Compliance tracking reduces legal risk. Strategic legal guidance protects company interests.', 502),
(2040, 1048, '2026-Q1', 62, 4.1, 'Good procurement management. Vendor negotiations successful.', 0, '2026-04-01', 1037, 'Score 4.1/5 indicates effective procurement execution. Successful negotiations optimize costs. Vendor management ensures supply continuity.', 502);

-- ============================================
-- SALES RECORDS (~50 records - deals across Q3 2025 - Q1 2026)
-- PRODUCTS LINKED TO SUPPLY CHAIN INVENTORY
-- ============================================

-- John Tan (1023) - UNDERPERFORMER - low sales
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, customer_name, region, close_date, ai_justification, source_id) VALUES
(3001, 1023, 102, '2025-Q3', 'Tech Solutions Switchgear', 'Low Voltage Switchgear', 18500.00, 'closed', 'Tech Solutions Sdn Bhd', 'Kuala Lumpur', '2025-09-15', 'Small switchgear deal (RM 18.5k) below quarterly target. Limited customer engagement. Basic LV switchgear product with thin margin. Below team average performance indicator.', 514),
(3002, 1023, 102, '2025-Q4', 'Retail Co Circuit Breakers', 'Air Circuit Breakers (ACB)', 8500.00, 'closed', 'Retail Co', 'Kuala Lumpur', '2025-12-08', 'Very low deal value (RM 8.5k) places in bottom 10% of team. Standard ACB product requiring minimal technical sale. Indicates difficulty closing larger opportunities.', 503),
(3003, 1023, 102, '2026-Q1', 'Small Business Cable Deal', 'Power Cable XLPE 240mm', 12400.00, 'closed', 'KL Ventures', 'Kuala Lumpur', '2026-03-22', 'Marginal improvement to RM 12.4k but still bottom 8% performer. Commodity power cable sale (low margin). Lack of enterprise-level closing ability evident.', 504),
(3004, 1023, 102, '2026-Q1', 'Enterprise Transformer Lead', 'Distribution Transformer 1000kVA', 0, 'lost', 'Major Corp', 'Kuala Lumpur', NULL, 'Lost major enterprise transformer deal to competitor. High-value opportunity (estimated RM 120k+) mishandled. Reflects inability to manage complex technical sales.', 519),
(3005, 1023, 102, '2026-Q1', 'Mid-Market Solar Opportunity', 'Solar Panel System 100kW', 0, 'pipeline', NULL, 'Penang', NULL, 'Stagnant pipeline opportunity for 5 weeks. Solar system sale requires technical knowledge and urgency lacking. Unlikely to close based on pattern.', 524);

-- Sarah Lim (1020) - Sales Director - high revenue
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, customer_name, region, close_date, ai_justification, source_id) VALUES
(3006, 1020, 102, '2025-Q4', 'Malaysia Bank Substation', 'Medium Voltage Switchgear 11kV', 285000.00, 'closed', 'Malaysia Bank Berhad', 'Kuala Lumpur', '2025-12-15', 'Major enterprise deal (RM 285k) demonstrates elite closing ability. 11kV MV switchgear requires technical expertise and relationship management. Top-tier performance indicator.', 503),
(3007, 1020, 102, '2026-Q1', 'Telecom Giant Power Solution', 'Distribution Transformer 1500kVA', 420000.00, 'closed', 'Telecom Malaysia', 'Kuala Lumpur', '2026-03-10', 'Exceptional deal (RM 420k) places in top 1% of company sales. Large transformer sale requires strategic account management. Revenue impact significant for quarterly results.', 504),
(3008, 1020, 102, '2026-Q1', 'Healthcare Solar Expansion', 'Solar Panel System 500kW', 195000.00, 'closed', 'Healthcare Group', 'Johor', '2026-03-28', 'Large solar installation (RM 195k) shows renewable energy expertise. Healthcare vertical penetration creates reference case. Strong closing quarter demonstrates consistency.', 504);

-- David Wong (1021) - Enterprise focus
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, customer_name, region, close_date, ai_justification, source_id) VALUES
(3009, 1021, 102, '2025-Q4', 'Manufacturing Power Distribution', 'Low Voltage Switchgear', 125000.00, 'closed', 'Manufacturing Corp', 'Penang', '2025-11-20', 'Strong enterprise deal (RM 125k) in manufacturing vertical. Complete LV switchgear solution demonstrates technical sales ability. Penang industrial market penetration.', 503),
(3010, 1021, 102, '2025-Q4', 'Logistics Backup Power', 'Diesel Generator 500kVA', 98000.00, 'closed', 'Logistics Solutions', 'Kuala Lumpur', '2025-12-10', 'Backup power solution (RM 98k) for critical logistics operation. Generator sale shows diverse product expertise. Reliable enterprise closer.', 503),
(3011, 1021, 102, '2026-Q1', 'Tech Startup UPS System', 'UPS System 200kVA', 65000.00, 'closed', 'TechStart Innovations', 'Cyberjaya', '2026-02-15', 'UPS system sale (RM 65k) to growing tech sector. Data center power protection solution. Cyberjaya tech vertical expansion.', 504),
(3012, 1021, 102, '2026-Q1', 'Retail Chain Lighting Project', 'LED Industrial Lighting 500 Units', 155000.00, 'closed', 'Retail Chain MY', 'Kuala Lumpur', '2026-03-18', 'Large lighting retrofit project (RM 155k) across multiple retail locations. Volume LED sale with installation services. Strong Q1 performance.', 504);

-- Alicia Fernandez (1022) - SMB specialist
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, customer_name, region, close_date, ai_justification, source_id) VALUES
(3013, 1022, 102, '2025-Q4', 'SMB Electrical Panel Package', 'Electrical Distribution Panel', 22000.00, 'closed', 'Business Solutions', 'Johor Bahru', '2025-11-15', 'Typical SMB deal (RM 22k) for standard distribution panel. Consistent SMB specialist performance. Johor market presence.', 503),
(3014, 1022, 102, '2025-Q4', 'Multi-site Circuit Protection', 'Miniature Circuit Breakers (MCB)', 35000.00, 'closed', 'Multi-Store Co', 'Penang', '2025-12-05', 'Multi-location MCB deployment (RM 35k) shows project coordination ability. Volume sale across retail stores. Above-average SMB deal.', 503),
(3015, 1022, 102, '2026-Q1', 'SMB Transformer Upgrade', 'Distribution Transformer 500kVA', 42000.00, 'closed', 'Growth Ventures', 'Kuala Lumpur', '2026-02-20', 'Small transformer sale (RM 42k) to growing SMB. Upsell from basic products. Good SMB relationship management.', 504),
(3016, 1022, 102, '2026-Q1', 'Startup Cable Installation', 'Power Cable XLPE 120mm', 18500.00, 'closed', 'StartupHub', 'Cyberjaya', '2026-03-12', 'Standard cable sale (RM 18.5k) to startup facility. Basic product with installation. Consistent pipeline management.', 504),
(3017, 1022, 102, '2026-Q1', 'Regional Business Switchgear', 'Low Voltage Switchgear', 28000.00, 'closed', 'Regional Services', 'Ipoh', '2026-03-25', 'LV switchgear sale (RM 28k) expands regional market. Ipoh penetration valuable. Solid SMB performance quarter.', 504);

-- Muthu Kumar (1024) - Enterprise account manager
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, customer_name, region, close_date, ai_justification, source_id) VALUES
(3018, 1024, 102, '2025-Q4', 'Financial Services MV Upgrade', 'Medium Voltage Switchgear 22kV', 180000.00, 'closed', 'Financial Services Group', 'Kuala Lumpur', '2025-12-20', 'Major MV switchgear renewal (RM 180k) for financial services sector. 22kV system requires technical expertise. Strong account management drives renewal.', 503),
(3019, 1024, 102, '2026-Q1', 'Insurance HQ Power System', 'Distribution Transformer 1000kVA', 210000.00, 'closed', 'Insurance Malaysia', 'Kuala Lumpur', '2026-02-28', 'Large transformer project (RM 210k) for insurance headquarters expansion. Critical power infrastructure sale. Enterprise relationship strength evident.', 504),
(3020, 1024, 102, '2026-Q1', 'Gov Agency Solar Contract', 'Solar Panel System 250kW', 145000.00, 'closed', 'Government Agency', 'Putrajaya', '2026-03-15', 'Government solar installation (RM 145k) aligns with green energy mandate. Putrajaya government sector penetration. Renewal contract demonstrates relationship quality.', 504);

-- Nurul Aisyah (1025) - Sales Manager
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, customer_name, region, close_date, ai_justification, source_id) VALUES
(3021, 1025, 102, '2025-Q4', 'Strategic Partnership Generators', 'Diesel Generator 1000kVA', 320000.00, 'closed', 'Partnership Corp', 'Kuala Lumpur', '2025-11-30', 'Major generator deal (RM 320k) through strategic partnership. Large backup power solution. Sales management expertise closes high-value opportunities.', 503),
(3022, 1025, 102, '2026-Q1', 'Education Sector UPS Fleet', 'UPS System 150kVA', 85000.00, 'closed', 'University Group', 'Kuala Lumpur', '2026-02-10', 'University campus UPS deployment (RM 85k) across multiple buildings. Education sector vertical. Management-level deal influence.', 504);

-- Tan Mei Ling (1026) - SMB sales
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, customer_name, region, close_date, ai_justification, source_id) VALUES
(3023, 1026, 102, '2025-Q4', 'SMB Panel Installation', 'Electrical Distribution Panel', 15500.00, 'closed', 'SMB Solutions', 'Penang', '2025-11-25', 'Standard SMB distribution panel (RM 15.5k). New customer acquisition in Penang market. Baseline SMB performance.', 503),
(3024, 1026, 102, '2026-Q1', 'Business Hub Circuit Breakers', 'Air Circuit Breakers (ACB)', 19500.00, 'closed', 'Business Hub', 'Penang', '2026-02-18', 'ACB sale (RM 19.5k) for business park facility. Repeat Penang customer. Consistent territory management.', 504),
(3025, 1026, 102, '2026-Q1', 'SMB Pro Transformer', 'Distribution Transformer 315kVA', 28000.00, 'closed', 'SMB Pro', 'Penang', '2026-03-20', 'Small transformer upsell (RM 28k) demonstrates account growth. 315kVA suitable for SMB expansion. Good relationship management.', 504),
(3026, 1026, 102, '2026-Q1', 'Regional Business Cables', 'Control Cable 10-Core', 21000.00, 'closed', 'Regional Business', 'Penang', '2026-03-28', 'Control cable project (RM 21k) for automation system. Specialized product knowledge. Strong Q1 SMB performance.', 504);

-- Azman Ibrahim (1027) - Enterprise sales
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, customer_name, region, close_date, ai_justification, source_id) VALUES
(3027, 1027, 102, '2025-Q4', 'Pharma Clean Power System', 'Medium Voltage Switchgear 11kV', 165000.00, 'closed', 'Pharma Solutions', 'Kuala Lumpur', '2025-12-12', 'Pharmaceutical MV switchgear (RM 165k) for clean room power. Specialized industry knowledge. Quality power requirements understood.', 503),
(3028, 1027, 102, '2026-Q1', 'Construction Site Generators', 'Diesel Generator 750kVA', 135000.00, 'closed', 'Construction Group', 'Johor', '2026-03-05', 'Heavy-duty generator (RM 135k) for construction temporary power. Johor construction sector penetration. Project-based selling strength.', 504),
(3029, 1027, 102, '2026-Q1', 'Transport Fleet Charging', 'EV Charging Station 150kW', 98000.00, 'closed', 'Transport Malaysia', 'Kuala Lumpur', '2026-03-22', 'EV charging infrastructure (RM 98k) for transport fleet electrification. Future-focused product positioning. Green transport vertical entry.', 504);

-- Rebecca Chong (1028) - Sales ops (team deals)
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, customer_name, region, close_date, ai_justification, source_id) VALUES
(3030, NULL, 102, '2025-Q4', 'Channel Partner Cable Volume', 'Power Cable XLPE 240mm', 250000.00, 'closed', 'Channel Partner Network', 'Multiple', '2025-12-30', 'Large volume cable order (RM 250k) through distribution channel. No individual sales attribution. Channel partnership drives volume revenue.', 503),
(3031, NULL, 102, '2026-Q1', 'Reseller LED Lighting Package', 'LED Industrial Lighting 1000 Units', 180000.00, 'closed', 'Reseller Group', 'Multiple', '2026-03-31', 'High-volume LED reseller deal (RM 180k) across multiple regions. Reseller network expansion. Scalable volume revenue model.', 504);

-- Vincent Lee (1029) - SDR (pipeline generation)
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, customer_name, region, close_date, ai_justification, source_id) VALUES
(3032, 1029, 102, '2026-Q1', 'Qualified Lead Solar Project', 'Solar Panel System 200kW', 0, 'pipeline', NULL, 'Kuala Lumpur', NULL, 'SDR-generated solar lead (estimated RM 150k). Technical qualification completed. Passed to enterprise sales team for closing.', 524),
(3033, 1029, 102, '2026-Q1', 'Qualified Lead SMB Transformer', 'Distribution Transformer 500kVA', 0, 'pipeline', NULL, 'Penang', NULL, 'SMB transformer opportunity (estimated RM 40k) qualified by SDR. Budget confirmed. Handoff to SMB sales executive.', 524),
(3034, 1029, 102, '2026-Q1', 'Qualified Lead Generator Project', 'Diesel Generator 500kVA', 0, 'pipeline', NULL, 'Johor', NULL, 'Backup power lead (estimated RM 100k) for manufacturing facility. Urgent need identified. Qualified for enterprise team.', 524);

-- Additional Q3 2025 deals for context
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, customer_name, region, close_date, ai_justification, source_id) VALUES
(3035, 1020, 102, '2025-Q3', 'Regional Bank Substation Upgrade', 'Medium Voltage Switchgear 22kV', 195000.00, 'closed', 'Regional Bank', 'Kuala Lumpur', '2025-09-20', 'Major banking sector MV upgrade (RM 195k). 22kV substation modernization. Financial services vertical strength.', 514),
(3036, 1021, 102, '2025-Q3', 'Tech Company UPS Infrastructure', 'UPS System 300kVA', 75000.00, 'closed', 'Tech Innovations', 'Cyberjaya', '2025-09-25', 'Data center UPS system (RM 75k) for tech company. Critical power protection. Cyberjaya tech hub penetration.', 514),
(3037, 1022, 102, '2025-Q3', 'SMB Network Electrical Package', 'Electrical Distribution Panel', 32000.00, 'closed', 'SMB Network', 'Penang', '2025-09-18', 'Multi-site SMB distribution panel deployment (RM 32k). Standardized solution across locations. Penang SMB cluster.', 514),
(3038, 1024, 102, '2025-Q3', 'Insurance Corp Power Renewal', 'Low Voltage Switchgear', 165000.00, 'closed', 'Insurance Corp', 'Kuala Lumpur', '2025-09-30', 'Insurance sector LV switchgear renewal (RM 165k). Long-term account relationship. Annual maintenance contract included.', 514),
(3039, 1025, 102, '2025-Q3', 'Education Campus Lighting', 'LED Industrial Lighting 300 Units', 92000.00, 'closed', 'College Group', 'Kuala Lumpur', '2025-09-22', 'Campus-wide LED lighting upgrade (RM 92k). Energy efficiency project. Education sector vertical penetration.', 514),
(3040, 1027, 102, '2025-Q3', 'Healthcare Power Backup', 'Diesel Generator 650kVA', 125000.00, 'closed', 'Healthcare Provider', 'Johor', '2025-09-28', 'Hospital backup generator (RM 125k) for critical healthcare operations. Emergency power reliability essential. Healthcare vertical expertise.', 514);

-- Lost deals for analysis
INSERT INTO sales_record (sales_id, employee_id, dept_id, period, deal_name, product, amount, deal_stage, customer_name, region, close_date, ai_justification, source_id) VALUES
(3041, 1023, 102, '2025-Q4', 'Enterprise Switchgear Lost', 'Medium Voltage Switchgear 11kV', 0, 'lost', 'Enterprise Target', 'Kuala Lumpur', NULL, 'Lost major MV switchgear deal (estimated RM 180k+) to competitor. Pricing not competitive and technical specifications misunderstood. Reflects sales capability gap.', 519),
(3042, 1023, 102, '2025-Q4', 'Mid-Market Solar Lost', 'Solar Panel System 150kW', 0, 'lost', 'Mid Market Co', 'Penang', NULL, 'Lost mid-market solar opportunity (estimated RM 120k) due to slow response time. Customer purchased from competitor with faster proposal. Urgency lacking.', 519),
(3043, 1026, 102, '2025-Q4', 'SMB Transformer Lost to Price', 'Distribution Transformer 315kVA', 0, 'lost', 'SMB Target', 'Ipoh', NULL, 'Lost SMB transformer deal (estimated RM 28k) on price alone. Could have differentiated on service/warranty. Price competition in commodity segment.', 519);

-- ============================================
-- FINANCE RECORDS (~35 records - salaries, budgets, costs)
-- ============================================

-- Salary records for key employees (Q1 2026)
INSERT INTO finance_record (finance_id, dept_id, employee_id, period, metric_name, amount, unit, category, ai_justification, source_id) VALUES
(4001, 102, 1023, '2026-Q1', 'salary', 31500.00, 'MYR', 'personnel', 'John Tan Q1 salary cost (RM 31.5k total = RM 10.5k × 3 months). Underperformer generating RM 12.4k revenue vs RM 31.5k cost. Negative ROI evident. Salary expense without proportional revenue contribution.', 506),
(4002, 102, 1020, '2026-Q1', 'salary', 54000.00, 'MYR', 'personnel', 'Sarah Lim Q1 base salary (RM 54k). Sales Director compensation. High performer justifying premium salary through RM 900k+ revenue generation. Positive ROI of 16.7x salary.', 506),
(4003, 102, 1020, '2026-Q1', 'bonus', 15000.00, 'MYR', 'personnel', 'Performance bonus (RM 15k) for exceeding Q1 targets. Incentive compensation drives elite performance. Bonus structure aligns individual and company goals effectively.', 506),
(4004, 102, 1021, '2026-Q1', 'salary', 34500.00, 'MYR', 'personnel', 'David Wong Q1 salary (RM 34.5k). Strong enterprise performer with RM 443k revenue generation. ROI of 12.8x demonstrates value. Justified compensation for results.', 506),
(4005, 102, 1021, '2026-Q1', 'commission', 8500.00, 'MYR', 'personnel', 'Sales commission (RM 8.5k) on enterprise deals closed. Commission structure incentivizes large deal focus. Performance-based pay aligns with company revenue goals.', 506),
(4006, 102, 1022, '2026-Q1', 'salary', 30600.00, 'MYR', 'personnel', 'Alicia Fernandez Q1 salary (RM 30.6k). SMB specialist with RM 146k revenue. ROI of 4.8x solid for SMB segment. Cost-effective SMB sales coverage.', 506),
(4007, 102, 1024, '2026-Q1', 'salary', 41400.00, 'MYR', 'personnel', 'Muthu Kumar Q1 salary (RM 41.4k). Enterprise account manager with RM 535k revenue. Exceptional ROI of 12.9x. Key account management justifies compensation.', 506),
(4008, 102, 1025, '2026-Q1', 'salary', 45000.00, 'MYR', 'personnel', 'Nurul Aisyah Q1 salary (RM 45k). Sales Manager with RM 405k personal revenue plus team oversight. Management salary justified by team performance and personal contribution.', 506);

-- Department budget records (Q1 2026)
INSERT INTO finance_record (finance_id, dept_id, employee_id, period, metric_name, amount, unit, category, ai_justification, source_id) VALUES
(4009, 101, NULL, '2026-Q1', 'headcount_cost', 395000.00, 'MYR', 'personnel', 'Engineering total headcount cost (RM 395k) for 12 engineers. Technical expertise enables electrical installations. Cost center necessary for technical service delivery and customer support.', 506),
(4010, 102, NULL, '2026-Q1', 'headcount_cost', 285000.00, 'MYR', 'personnel', 'Sales total headcount cost (RM 285k) for 10 sales staff. Revenue generation (RM 2.68M) yields ROI of 9.4x. Profit center with strong return on personnel investment.', 506),
(4011, 103, NULL, '2026-Q1', 'headcount_cost', 182000.00, 'MYR', 'personnel', 'Marketing total cost (RM 182k) for 7 marketing staff. Lead generation supports sales pipeline. Marketing spend drives brand awareness and customer acquisition.', 506),
(4012, 104, NULL, '2026-Q1', 'headcount_cost', 135000.00, 'MYR', 'personnel', 'HR total cost (RM 135k) for 4 HR staff. Talent management and compliance function. Cost center providing organizational infrastructure and risk management.', 506),
(4013, 105, NULL, '2026-Q1', 'headcount_cost', 186000.00, 'MYR', 'personnel', 'Finance total cost (RM 186k) for 5 finance staff. Financial controls and reporting function. Cost center enabling fiscal discipline and strategic planning.', 506),
(4014, 106, NULL, '2026-Q1', 'headcount_cost', 88000.00, 'MYR', 'personnel', 'Legal total cost (RM 88k) for 2 legal staff. Legal counsel and compliance management. Cost center reducing legal risk and enabling contract management.', 506),
(4015, 107, NULL, '2026-Q1', 'headcount_cost', 91000.00, 'MYR', 'personnel', 'Supply Chain total cost (RM 91k) for 3 procurement staff. Inventory management and vendor relations. Cost center enabling product availability and cost optimization.', 506);

-- Revenue and costs
INSERT INTO finance_record (finance_id, dept_id, employee_id, period, metric_name, amount, unit, category, ai_justification, source_id) VALUES
(4016, 102, NULL, '2026-Q1', 'revenue', 2680000.00, 'MYR', 'revenue', 'Total Q1 2026 sales revenue (RM 2.68M) from electrical equipment sales. YoY growth of 9.4% from Q1 2025. Healthy revenue growth indicates market demand and sales effectiveness.', 506),
(4017, 103, NULL, '2026-Q1', 'marketing_spend', 185000.00, 'MYR', 'operations', 'Q1 marketing campaign spend (RM 185k) on trade shows, digital ads, and content. Lead generation investment supports sales pipeline. Marketing ROI measured through conversion rates.', 506),
(4018, 107, NULL, '2026-Q1', 'procurement_cost', 125000.00, 'MYR', 'operations', 'Q1 procurement operations cost (RM 125k) including logistics and warehousing. Supply chain efficiency enables product availability. Cost necessary for distribution operations.', 506),
(4019, 101, NULL, '2026-Q1', 'infrastructure_cost', 85000.00, 'MYR', 'operations', 'Q1 infrastructure cost (RM 85k) for warehouse, testing facilities, and vehicles. Physical infrastructure enables installation services and inventory management.', 506),
(4020, NULL, NULL, '2026-Q1', 'office_rent', 65000.00, 'MYR', 'operations', 'Q1 office rent (RM 65k) for headquarters and regional offices. Fixed cost necessary for business operations. Commercial real estate expense stable.', 506),
(4021, NULL, NULL, '2026-Q1', 'utilities', 22000.00, 'MYR', 'operations', 'Q1 utilities cost (RM 22k) for electricity, water, and telecom. Fixed operating expense for facility operations. Necessary overhead for business continuity.', 506);

-- Termination and replacement costs (relevant for decision case)
INSERT INTO finance_record (finance_id, dept_id, employee_id, period, metric_name, amount, unit, category, ai_justification, source_id) VALUES
(4022, 104, NULL, '2026-Q1', 'severance_reserve', 150000.00, 'MYR', 'reserves', 'Legal reserve (RM 150k) for potential employee terminations and severance payments. Risk management provision for HR actions. Adequate reserve maintained for compliance.', 506),
(4023, 104, NULL, '2026-Q1', 'replacement_cost_estimate', 45000.00, 'MYR', 'recruiting', 'Average replacement cost (RM 45k) for sales executive position. Includes recruitment fees (RM 15k), onboarding (RM 12k), and 3-month productivity ramp (RM 18k). Total cost to replace underperformer.', 522),
(4024, 104, NULL, '2026-Q1', 'onboarding_cost_estimate', 12000.00, 'MYR', 'recruiting', 'Onboarding cost (RM 12k) for new sales hire including training, product education, and mentoring. 6-week ramp program cost. Investment necessary for new employee productivity.', 522);

-- Q4 2025 financial records for comparison
INSERT INTO finance_record (finance_id, dept_id, employee_id, period, metric_name, amount, unit, category, ai_justification, source_id) VALUES
(4025, 102, NULL, '2025-Q4', 'revenue', 2450000.00, 'MYR', 'revenue', 'Q4 2025 revenue (RM 2.45M) baseline for comparison. Q1 2026 growth of RM 230k (+9.4%) demonstrates business momentum. Seasonal patterns and market trends visible.', 515),
(4026, 102, NULL, '2025-Q4', 'headcount_cost', 278000.00, 'MYR', 'personnel', 'Q4 2025 sales headcount (RM 278k) vs Q1 2026 (RM 285k). Modest increase reflects standard salary adjustments. Personnel cost growth controlled relative to revenue growth.', 515),
(4027, 103, NULL, '2025-Q4', 'marketing_spend', 165000.00, 'MYR', 'operations', 'Q4 2025 marketing spend (RM 165k) vs Q1 2026 (RM 185k). 12% increase in marketing investment supports growth strategy. Campaign expansion drives lead generation.', 515),
(4028, 101, NULL, '2025-Q4', 'infrastructure_cost', 78000.00, 'MYR', 'operations', 'Q4 2025 infrastructure (RM 78k) vs Q1 2026 (RM 85k). Warehouse expansion and vehicle additions. Infrastructure investment supports business scaling.', 515);

-- Individual salary audit records (Q1 2026 - select employees)
INSERT INTO finance_record (finance_id, dept_id, employee_id, period, metric_name, amount, unit, category, ai_justification, source_id) VALUES
(4029, 101, 1003, '2026-Q1', 'salary', 42600.00, 'MYR', 'personnel', 'Priya Kumar Q1 salary (RM 42.6k). Technical Services Lead with 40% downtime reduction. High-impact engineering role. Performance justifies technical specialist compensation.', 506),
(4030, 101, 1008, '2026-Q1', 'salary', 49500.00, 'MYR', 'personnel', 'Rajesh Menon Q1 salary (RM 49.5k). Engineering Manager overseeing 12 engineers. Management premium for team leadership. Critical role for technical service delivery.', 506),
(4031, 103, 1030, '2026-Q1', 'salary', 49500.00, 'MYR', 'personnel', 'Zara Khan Q1 salary (RM 49.5k). Marketing Director with 18% ROI improvement YoY. Leadership role driving brand and demand generation. Performance validates compensation.', 506),
(4032, 104, 1037, '2026-Q1', 'salary', 46500.00, 'MYR', 'personnel', 'Fatimah Zahra Q1 salary (RM 46.5k). HR Director managing talent and compliance. Strong retention rates reduce hiring costs. Strategic HR leadership justifies compensation.', 506),
(4033, 105, 1041, '2026-Q1', 'salary', 66000.00, 'MYR', 'personnel', 'James Lim Q1 salary (RM 66k). CFO driving profitability ahead of plan. Highest compensation reflects C-suite financial leadership. Strategic finance role critical for growth.', 506),
(4034, 106, 1046, '2026-Q1', 'salary', 55500.00, 'MYR', 'personnel', 'David Tan Q1 salary (RM 55.5k). General Counsel managing legal risk and compliance. Legal expertise protects company interests. Counsel compensation reflects specialized expertise.', 506);

-- ============================================
-- MARKETING RECORDS (~30 records - campaigns Q3 2025 - Q1 2026)
-- ============================================

-- Q1 2026 campaigns
INSERT INTO marketing_record (marketing_id, period, campaign_name, channel, metric_name, amount, target_audience, ai_justification, source_id) VALUES
(5001, '2026-Q1', 'Enterprise Electrical Solutions', 'LinkedIn', 'impressions', 1850000, 'Industrial Facility Managers', 'High impression volume (1.85M) targets B2B industrial decision-makers. LinkedIn effective for enterprise electrical sector. Brand awareness campaign reaches facility management professionals.', 510),
(5002, '2026-Q1', 'Enterprise Electrical Solutions', 'LinkedIn', 'clicks', 42500, 'Industrial Facility Managers', 'Click volume (42.5k) indicates 2.3% CTR (above B2B benchmark of 0.5%). Strong engagement from industrial target audience. Ad creative and messaging resonate with facility managers.', 510),
(5003, '2026-Q1', 'Enterprise Electrical Solutions', 'LinkedIn', 'conversions', 420, 'Industrial Facility Managers', 'Lead conversions (420) at 0.99% conversion rate. Strong lead quality from enterprise segment. LinkedIn targeting effective for qualified industrial leads.', 510),
(5004, '2026-Q1', 'Enterprise Electrical Solutions', 'LinkedIn', 'spend', 98000.00, 'Industrial Facility Managers', 'Campaign spend (RM 98k) yields RM 233 per lead cost. Premium pricing justified by enterprise deal size (avg RM 150k). ROI positive if 10%+ conversion to sales.', 510),
(5005, '2026-Q1', 'SMB Electrical Equipment', 'Google Ads', 'impressions', 2200000, 'SMB Owners Malaysia', 'High Google Ads reach (2.2M impressions) targets SMB electrical buyers. Search intent-based targeting. Keyword strategy focuses on equipment purchase intent.', 510),
(5006, '2026-Q1', 'SMB Electrical Equipment', 'Google Ads', 'clicks', 68000, 'SMB Owners Malaysia', 'Click volume (68k) shows 3.1% CTR (strong for Google Ads). Search keywords drive qualified traffic. SMB audience actively searching for electrical equipment.', 510),
(5007, '2026-Q1', 'SMB Electrical Equipment', 'Google Ads', 'conversions', 580, 'SMB Owners Malaysia', 'Lead conversions (580) at 0.85% rate. Volume-driven SMB lead generation. Google Ads effective for transactional intent capture.', 510),
(5008, '2026-Q1', 'SMB Electrical Equipment', 'Google Ads', 'spend', 62000.00, 'SMB Owners Malaysia', 'Campaign spend (RM 62k) yields RM 107 per lead cost. Cost-effective SMB lead generation. Lower cost per lead reflects SMB deal size (avg RM 25k).', 510),
(5009, '2026-Q1', 'Technical Content Marketing', 'Blog/SEO', 'organic_visits', 125000, 'Electrical Engineers', 'Organic traffic (125k visits) from SEO-optimized electrical technical content. Educational content builds thought leadership. Technical audience research drives organic discovery.', 510),
(5010, '2026-Q1', 'Technical Content Marketing', 'Blog/SEO', 'leads', 285, 'Electrical Engineers', 'Organic leads (285) from content marketing efforts. Technical content attracts engineering audience. Educational approach builds trust and authority.', 510),
(5011, '2026-Q1', 'Email Nurture Campaign', 'Email', 'emails_sent', 45000, 'Existing Leads', 'Email volume (45k) nurtures existing lead database. Drip campaigns educate prospects on products. Relationship marketing maintains engagement.', 510),
(5012, '2026-Q1', 'Email Nurture Campaign', 'Email', 'conversions', 120, 'Existing Leads', 'Email conversions (120) from nurture sequences. Conversion rate of 0.27% typical for B2B. Email marketing drives pipeline progression.', 510),
(5013, '2026-Q1', 'Industrial Trade Shows', 'Events', 'attendees', 850, 'Enterprise Prospects', 'Trade show attendance (850 booth visitors) at electrical industry events. Face-to-face engagement crucial for B2B electrical sector. Relationship building through in-person interaction.', 510),
(5014, '2026-Q1', 'Industrial Trade Shows', 'Events', 'qualified_leads', 85, 'Enterprise Prospects', 'Qualified leads (85) from trade show events. 10% qualification rate indicates strong booth engagement. Enterprise decision-makers attend industry trade shows.', 510),
(5015, '2026-Q1', 'Industrial Trade Shows', 'Events', 'spend', 18000.00, 'Enterprise Prospects', 'Trade show spend (RM 18k) including booth, travel, and materials. RM 212 per qualified lead cost. Premium cost justified by relationship quality and deal size.', 510);

-- Q4 2025 campaigns
INSERT INTO marketing_record (marketing_id, period, campaign_name, channel, metric_name, amount, target_audience, ai_justification, source_id) VALUES
(5016, '2025-Q4', 'Year-End Industrial Push', 'LinkedIn', 'impressions', 1650000, 'Industrial Decision Makers', 'Year-end campaign (1.65M impressions) targets budget utilization period. Q4 timing captures end-of-year capital expenditure decisions. Industrial purchasing cycles align with fiscal year-end.', 509),
(5017, '2025-Q4', 'Year-End Industrial Push', 'LinkedIn', 'clicks', 38000, 'Industrial Decision Makers', 'Click volume (38k) shows 2.3% CTR consistent with B2B norms. Year-end messaging resonates with procurement urgency. Budget deadline pressure drives engagement.', 509),
(5018, '2025-Q4', 'Year-End Industrial Push', 'LinkedIn', 'conversions', 380, 'Industrial Decision Makers', 'Q4 conversions (380) capture year-end procurement activity. "Use it or lose it" budget dynamics. Conversion spike typical for fiscal year-end.', 509),
(5019, '2025-Q4', 'Year-End Industrial Push', 'LinkedIn', 'spend', 85000.00, 'Industrial Decision Makers', 'Q4 campaign spend (RM 85k) at RM 224 per lead. Year-end budget push justifies higher spend. Strategic timing for capital equipment purchases.', 509),
(5020, '2025-Q4', 'Holiday SMB Campaign', 'Google Ads', 'impressions', 1850000, 'SMB Malaysia', 'Holiday season SMB targeting (1.85M impressions). Year-end maintenance and upgrade projects. Seasonal buying patterns for electrical equipment.', 509),
(5021, '2025-Q4', 'Holiday SMB Campaign', 'Google Ads', 'clicks', 52000, 'SMB Malaysia', 'Q4 clicks (52k) at 2.8% CTR. Holiday season purchase intent. SMB year-end project completions drive traffic.', 509),
(5022, '2025-Q4', 'Holiday SMB Campaign', 'Google Ads', 'conversions', 450, 'SMB Malaysia', 'Q4 SMB conversions (450) from holiday campaign. Year-end project deadlines accelerate decisions. Seasonal conversion rate spike.', 509),
(5023, '2025-Q4', 'Holiday SMB Campaign', 'Google Ads', 'spend', 55000.00, 'SMB Malaysia', 'Holiday campaign spend (RM 55k) at RM 122 per lead. Competitive bidding during peak season. Cost-per-lead elevated but conversion quality higher.', 509),
(5024, '2025-Q4', 'Brand Awareness', 'Social Media', 'impressions', 3200000, 'General Audience', 'Social media brand campaign (3.2M impressions) builds general awareness. Broader audience targeting than direct response. Brand building supports long-term demand generation.', 509),
(5025, '2025-Q4', 'Brand Awareness', 'Social Media', 'engagement', 45000, 'General Audience', 'Social engagement (45k interactions) at 1.4% rate. Brand content resonates with industrial audience. Social proof and community building.', 509),
(5026, '2025-Q4', 'Brand Awareness', 'Social Media', 'spend', 25000.00, 'General Audience', 'Social media spend (RM 25k) for brand awareness objectives. Lower cost-per-impression than direct response. Long-term brand equity investment.', 509);

-- Q3 2025 campaigns
INSERT INTO marketing_record (marketing_id, period, campaign_name, channel, metric_name, amount, target_audience, ai_justification, source_id) VALUES
(5027, '2025-Q3', 'Lead Gen Campaign', 'LinkedIn', 'impressions', 1450000, 'Enterprise Industrial', 'Q3 lead generation (1.45M impressions) establishes baseline campaign performance. Summer period typically slower for industrial B2B. Consistent presence maintains brand visibility.', 520),
(5028, '2025-Q3', 'Lead Gen Campaign', 'LinkedIn', 'conversions', 320, 'Enterprise Industrial', 'Q3 conversions (320) lower than Q4 (380) due to seasonality. Summer procurement slowdown typical. Pipeline building for Q4 sales closing.', 520),
(5029, '2025-Q3', 'Lead Gen Campaign', 'LinkedIn', 'spend', 75000.00, 'Enterprise Industrial', 'Q3 spend (RM 75k) maintains marketing presence during slower season. Lead nurturing focus for future conversion. Investment in pipeline development.', 520),
(5030, '2025-Q3', 'SMB Awareness', 'Google Ads', 'impressions', 1650000, 'SMB Owners', 'Q3 SMB campaign (1.65M impressions) builds awareness during maintenance season. Summer electrical upgrades typical. Seasonal targeting strategy.', 520),
(5031, '2025-Q3', 'SMB Awareness', 'Google Ads', 'conversions', 380, 'SMB Owners', 'Q3 SMB conversions (380) from summer projects. Maintenance and upgrade seasonality. Steady SMB demand throughout year.', 520),
(5032, '2025-Q3', 'SMB Awareness', 'Google Ads', 'spend', 48000.00, 'SMB Owners', 'Q3 Google Ads spend (RM 48k) at RM 126 per lead. Cost-efficient SMB acquisition. Summer bidding less competitive than year-end.', 520);

-- ============================================
-- SUPPLY CHAIN RECORDS (~30 records - inventory and procurement)
-- PRODUCTS MATCH SALES RECORDS FOR LINKING
-- ============================================

-- Q1 2026 inventory status
INSERT INTO supply_record (supply_id, period, item_name, item_category, inventory_level, demand_forecast, reorder_point, supplier_name, unit_cost, shortage_flag, ai_justification, source_id) VALUES
(6001, '2026-Q1', 'Low Voltage Switchgear', 'switchgear', 12, 18, 15, 'Schneider Electric Malaysia', 45000.00, 1, 'LV switchgear inventory (12 units) below reorder point (15 units). High sales demand (Q1: 3 deals). Shortage flag indicates procurement urgency. Lead time 6 weeks requires immediate order.', 512),
(6002, '2026-Q1', 'Medium Voltage Switchgear 11kV', 'switchgear', 3, 6, 5, 'Siemens Malaysia', 125000.00, 1, '11kV MV switchgear critically low (3 units vs 5 reorder point). Enterprise demand strong (Q1: 2 major deals RM 465k). Shortage disrupts sales pipeline. Urgent procurement needed.', 512),
(6003, '2026-Q1', 'Medium Voltage Switchgear 22kV', 'switchgear', 2, 4, 3, 'ABB Malaysia', 180000.00, 1, '22kV MV switchgear shortage (2 vs 3 reorder). High-value enterprise product. Q1 demand (1 deal RM 195k) depleted stock. Critical shortage for enterprise sales.', 512),
(6004, '2026-Q1', 'Distribution Transformer 500kVA', 'transformer', 8, 12, 10, 'Tenaga Transformer', 38000.00, 1, '500kVA transformer below reorder (8 vs 10). SMB/mid-market demand (Q1: 2 deals). Shortage impacts mid-market segment. 8-week lead time requires action.', 512),
(6005, '2026-Q1', 'Distribution Transformer 1000kVA', 'transformer', 4, 8, 6, 'Tenaga Transformer', 85000.00, 1, '1000kVA transformer shortage (4 vs 6 reorder). Enterprise demand strong (Q1: 2 deals RM 630k). Critical shortage for large projects. Urgent replenishment.', 512),
(6006, '2026-Q1', 'Distribution Transformer 1500kVA', 'transformer', 1, 3, 2, 'Tenaga Transformer', 125000.00, 1, '1500kVA transformer critical shortage (1 unit remaining). Mega-deal product (Q1: RM 420k sale). Out-of-stock risk high. Emergency order required.', 512),
(6007, '2026-Q1', 'Air Circuit Breakers (ACB)', 'circuit_breaker', 45, 35, 25, 'LS Electric', 2500.00, 0, 'ACB inventory healthy (45 vs 25 reorder). Moderate sales demand (Q1: 2 deals). No shortage. Standard stock level maintained for SMB segment.', 512),
(6008, '2026-Q1', 'Miniature Circuit Breakers (MCB)', 'circuit_breaker', 850, 600, 400, 'Hager Malaysia', 45.00, 0, 'MCB inventory strong (850 units). High-volume commodity product. Q1 demand (1 large multi-site deal). No shortage. Bulk pricing maintained.', 512),
(6009, '2026-Q1', 'Power Cable XLPE 240mm', 'cable', 15000, 18000, 12000, 'Cables Malaysia', 125.00, 1, 'XLPE 240mm cable below reorder (15k meters vs 12k reorder). Sales demand (Q1: 2 deals + channel volume). Shortage impacts standard projects. Order large volume.', 512),
(6010, '2026-Q1', 'Power Cable XLPE 120mm', 'cable', 8500, 8000, 6000, 'Cables Malaysia', 65.00, 0, 'XLPE 120mm cable adequate (8.5k meters vs 6k reorder). Moderate demand. No immediate shortage. Standard cable inventory maintained.', 512),
(6011, '2026-Q1', 'Control Cable 10-Core', 'cable', 4200, 5000, 4000, 'Cables Malaysia', 28.00, 1, 'Control cable slight shortage (4.2k vs 4k reorder). Automation projects demand. Q1 sales depleted stock. Reorder to maintain availability.', 512),
(6012, '2026-Q1', 'Diesel Generator 500kVA', 'generator', 5, 8, 6, 'Cummins Malaysia', 95000.00, 1, '500kVA generator shortage (5 vs 6 reorder). Backup power demand strong (Q1: 2 deals). Enterprise segment product. 10-week lead time requires action.', 512),
(6013, '2026-Q1', 'Diesel Generator 750kVA', 'generator', 3, 5, 4, 'Cummins Malaysia', 135000.00, 1, '750kVA generator below reorder (3 vs 4). Construction/industrial demand (Q1: 1 deal RM 135k). Shortage limits project sales. Urgent procurement.', 512),
(6014, '2026-Q1', 'Diesel Generator 1000kVA', 'generator', 2, 4, 3, 'Caterpillar Malaysia', 285000.00, 1, '1000kVA generator critical shortage (2 vs 3 reorder). Large enterprise backup power. Q1 mega-deal (RM 320k) depleted stock. High-value product requires replenishment.', 512),
(6015, '2026-Q1', 'UPS System 150kVA', 'ups', 8, 10, 8, 'Eaton Malaysia', 42000.00, 0, 'UPS 150kVA at reorder threshold (8 units). Education/mid-market demand (Q1: 1 deal). Borderline stock level. Monitor closely for reorder timing.', 512),
(6016, '2026-Q1', 'UPS System 200kVA', 'ups', 6, 8, 6, 'Eaton Malaysia', 62000.00, 0, 'UPS 200kVA at reorder threshold (6 units). Tech sector demand (Q1: 1 deal RM 65k). Adequate stock. Data center segment product.', 512),
(6017, '2026-Q1', 'UPS System 300kVA', 'ups', 3, 6, 4, 'Eaton Malaysia', 118000.00, 1, 'UPS 300kVA shortage (3 vs 4 reorder). Large data center/enterprise demand. Q3 2025 sale depleted stock. Reorder needed for tech sector pipeline.', 512),
(6018, '2026-Q1', 'Solar Panel System 100kW', 'solar', 4, 8, 6, 'Canadian Solar MY', 75000.00, 1, '100kW solar system shortage (4 vs 6 reorder). Green energy demand growing. Pipeline opportunity (1 stagnant lead). Shortage limits solar sales push.', 512),
(6019, '2026-Q1', 'Solar Panel System 250kW', 'solar', 3, 6, 4, 'Jinko Solar MY', 185000.00, 1, '250kW solar shortage (3 vs 4 reorder). Government/mid-market green energy projects (Q1: 1 deal RM 145k). Shortage impacts sustainability vertical. Reorder needed.', 512),
(6020, '2026-Q1', 'Solar Panel System 500kW', 'solar', 1, 3, 2, 'Longi Solar MY', 365000.00, 1, '500kW solar critical shortage (1 unit). Large enterprise green energy (Q1: RM 195k deal depleted stock). Mega-project product. Emergency procurement required.', 512),
(6021, '2026-Q1', 'LED Industrial Lighting 100 Units', 'lighting', 15, 12, 8, 'Philips Lighting MY', 18000.00, 0, 'LED lighting package healthy (15 packages vs 8 reorder). Volume lighting projects. Q1 demand (3 deals totaling 1800+ units). Adequate stock for retrofit projects.', 512),
(6022, '2026-Q1', 'Electrical Distribution Panel', 'distribution', 35, 30, 20, 'Legrand Malaysia', 8500.00, 0, 'Distribution panel inventory strong (35 vs 20 reorder). SMB standard product (Q1: 3 deals). No shortage. High-volume commodity product well-stocked.', 512),
(6023, '2026-Q1', 'EV Charging Station 150kW', 'ev_charging', 8, 10, 8, 'ABB E-Mobility', 98000.00, 0, 'EV charger at threshold (8 units). Emerging transport electrification demand (Q1: 1 deal RM 98k). Growth segment. Monitor demand trends for future ordering.', 512);

-- Q4 2025 inventory comparison
INSERT INTO supply_record (supply_id, period, item_name, item_category, inventory_level, demand_forecast, reorder_point, supplier_name, unit_cost, shortage_flag, ai_justification, source_id) VALUES
(6024, '2025-Q4', 'Low Voltage Switchgear', 'switchgear', 18, 20, 15, 'Schneider Electric Malaysia', 44000.00, 0, 'Q4 LV switchgear healthy (18 units). Q4 demand (3 deals) maintained adequate stock. No shortage in Q4. Q1 shortage developed from sustained sales without replenishment.', 511),
(6025, '2025-Q4', 'Distribution Transformer 1000kVA', 'transformer', 8, 10, 6, 'Tenaga Transformer', 82000.00, 0, 'Q4 transformer adequate (8 units). Q4 demand (1 deal). Stock erosion from Q3→Q4→Q1 sales cycle. Progressive depletion led to Q1 shortage.', 511),
(6026, '2025-Q4', 'Power Cable XLPE 240mm', 'cable', 22000, 20000, 12000, 'Cables Malaysia', 122.00, 0, 'Q4 cable inventory strong (22k meters). Q4 channel volume deal (250k) plus regular sales depleted stock by Q1. High-volume product requires frequent replenishment.', 511),
(6027, '2025-Q4', 'Diesel Generator 1000kVA', 'generator', 5, 6, 3, 'Caterpillar Malaysia', 280000.00, 0, 'Q4 generator adequate (5 units). Q4 mega-deal (RM 320k) and Q1 usage reduced to 2 units by Q1. High-value product with long lead time requires proactive ordering.', 511);

-- Vendor performance tracking
INSERT INTO supply_record (supply_id, period, item_name, item_category, inventory_level, demand_forecast, reorder_point, supplier_name, unit_cost, shortage_flag, ai_justification, source_id) VALUES
(6028, '2026-Q1', 'Vendor: Schneider Electric', 'vendor_metric', 0, 0, 0, 'Schneider Electric Malaysia', 0, 0, 'Schneider Electric vendor performance strong. On-time delivery 95%. LV switchgear lead time 6 weeks consistent. Pricing stable. Strategic vendor relationship maintained.', 521),
(6029, '2026-Q1', 'Vendor: Siemens', 'vendor_metric', 0, 0, 0, 'Siemens Malaysia', 0, 0, 'Siemens MV switchgear vendor reliable. Premium pricing but quality consistent. 8-week lead time for 11kV products. Enterprise-grade vendor partnership critical.', 521),
(6030, '2026-Q1', 'Vendor: Tenaga Transformer', 'vendor_metric', 0, 0, 0, 'Tenaga Transformer', 0, 1, 'Tenaga Transformer delivery delays noted (flagged). 8-10 week lead time extending to 12 weeks. Transformer shortage partially supplier-driven. Need backup vendor or larger safety stock.', 521),
(6031, '2026-Q1', 'Vendor: Cummins', 'vendor_metric', 0, 0, 0, 'Cummins Malaysia', 0, 0, 'Cummins generator supplier consistent. 10-week lead time for diesel generators. Pricing competitive. Service network strong (important for maintenance contracts).', 521),
(6032, '2026-Q1', 'Vendor: Cables Malaysia', 'vendor_metric', 0, 0, 0, 'Cables Malaysia', 0, 0, 'Cable supplier reliable for high-volume orders. 2-week lead time for standard cables. Bulk pricing negotiated. Volume rebates achieved Q1.', 521);

-- Critical procurement needs (flagged for decision engine)
INSERT INTO supply_record (supply_id, period, item_name, item_category, inventory_level, demand_forecast, reorder_point, supplier_name, unit_cost, shortage_flag, ai_justification, source_id) VALUES
(6033, '2026-Q2-Forecast', 'Emergency Transformer Order', 'transformer', 0, 12, 8, 'Tenaga Transformer', 85000.00, 1, 'Emergency transformer procurement needed (12 units across 500kVA, 1000kVA, 1500kVA). Total cost RM 1.02M. Critical for Q2 sales pipeline. 12-week lead time requires immediate PO.', 512),
(6034, '2026-Q2-Forecast', 'MV Switchgear Replenishment', 'switchgear', 0, 8, 6, 'Siemens Malaysia', 145000.00, 1, 'MV switchgear critical order (8 units 11kV/22kV mix). Total cost RM 1.16M. Enterprise sales pipeline at risk. 8-week delivery requires urgent order placement.', 512),
(6035, '2026-Q2-Forecast', 'Solar System Inventory Build', 'solar', 0, 10, 6, 'Canadian Solar MY', 195000.00, 1, 'Solar system inventory buildup (10 units across 100kW-500kW). Total cost RM 1.95M. Green energy demand accelerating. Strategic inventory investment for growth segment.', 512);

-- ============================================
-- LEGAL TABLES (policies, contracts, cases)
-- ============================================

-- Legal Policies (12 records)
INSERT INTO legal_policy (legal_id, policy_category, policy_name, rule_text, effective_date, region, ai_justification, source_id) VALUES
(7001, 'termination', 'Performance-Based Termination Policy', 
'Employees may be terminated for cause after two consecutive underperformance reviews (performance score < 2.5/5.0) AND completion of a mandatory 60-day Performance Improvement Plan (PIP). Termination must be approved by department head and HR Director. Severance: 1 month base salary per year of service, minimum RM 20,000, maximum RM 100,000.', 
'2025-06-01', 'Malaysia', 'Termination policy requires both performance threshold (2 reviews < 2.5) AND PIP completion. Dual requirements protect company from wrongful termination claims. Severance formula balances employee protection with cost control (RM 20k-100k cap).', 507),

(7002, 'termination', 'Severance Calculation Guidelines', 
'Severance formula: (Years of Service × 1 month base salary) + (Unused leave days × daily rate). Minimum: RM 20,000. Maximum: RM 100,000. Payment within 30 days of exit date. EPF and SOCSO contributions settled as per Malaysian law.', 
'2025-06-15', 'Malaysia', 'Severance calculation provides clear formula for cost estimation. Minimum RM 20k protects employees. Maximum RM 100k caps company liability. 30-day payment ensures compliance. EPF/SOCSO statutory requirements included.', 517),

(7003, 'termination', 'Immediate Termination - Misconduct', 
'Immediate termination allowed without PIP for: (1) Gross misconduct, (2) Fraud or theft, (3) Violence or harassment, (4) Breach of confidentiality, (5) Criminal conviction. No severance required if documented evidence exists. Must involve Legal and HR approval.', 
'2025-06-01', 'Malaysia', 'Immediate termination clause allows fast action for serious misconduct. No PIP required for egregious violations. No severance if proven misconduct protects company financially. Legal + HR approval prevents abuse.', 507),

(7004, 'hiring', 'Replacement Hiring Policy', 
'Replacement hires for terminated employees require: (1) Department head justification, (2) Budget approval from Finance, (3) HR screening process (minimum 3 weeks). Estimated replacement cost: RM 35,000 - RM 55,000 including recruitment fees, onboarding, and 3-month ramp time productivity loss.', 
'2025-06-01', 'Malaysia', 'Replacement hiring policy controls headcount decisions. Multi-stakeholder approval prevents impulsive hiring. Cost estimate (RM 35-55k) enables financial planning. 3-week minimum ensures thorough candidate screening.', 522),

(7005, 'performance', 'Performance Improvement Plan (PIP) Guidelines', 
'PIP duration: 60 days minimum, 90 days maximum. Must include: (1) Specific measurable goals, (2) Weekly check-ins with manager, (3) Mid-point review at 30 days, (4) Final assessment. Success criteria must be documented. PIP completion required before performance termination.', 
'2025-07-15', 'Malaysia', 'PIP guidelines create structured remediation process. 60-90 day timeframe balances improvement opportunity with business urgency. Measurable goals + weekly check-ins ensure fairness. Documentation protects legal position.', 508),

(7006, 'compliance', 'Malaysian Employment Act Compliance', 
'All terminations must comply with Employment Act 1955. Notice period: 1 month for employees with > 2 years service. Termination must not be discriminatory (race, religion, gender, disability). Written termination letter required. Employee entitled to appeal within 14 days.', 
'2025-06-01', 'Malaysia', 'Employment Act compliance mandatory for legal terminations. 1-month notice period for 2+ year employees statutory. Anti-discrimination protection prevents unlawful termination. Appeal rights provide employee due process.', 507),

(7007, 'expansion', 'Singapore Market Expansion Requirements', 
'To operate in Singapore: (1) Register Pte Ltd entity (paid-up capital min SGD 1), (2) Appoint local director (Singapore resident), (3) Comply with Employment Act (Singapore), (4) Commercial property lease, (5) Tax: 17% corporate tax, (6) Setup cost estimate: SGD 80,000 - SGD 120,000.', 
'2025-11-20', 'Singapore', 'Singapore expansion requires Pte Ltd registration (SGD 1 minimum capital). Local director mandatory per Companies Act. Different labor laws require compliance review. Setup cost SGD 80-120k (RM 380-570k) for full entity establishment.', 516),

(7008, 'compliance', 'Data Privacy and PDPA Compliance', 
'Personal Data Protection Act (PDPA) 2010 compliance mandatory. Employee data retention: 7 years post-exit. Customer data: consent-based processing only. Data breach notification: within 72 hours. PDPA fines up to RM 500,000. Annual compliance audit required.', 
'2025-08-01', 'Malaysia', 'PDPA compliance protects customer and employee data privacy. 7-year retention for employment records statutory. Consent-based processing prevents data misuse. 72-hour breach notification limits liability. RM 500k fine risk requires serious compliance.', 525),

(7009, 'IP', 'Intellectual Property Ownership', 
'All work product created by employees during employment is company property. Non-compete: 6 months post-exit for senior roles. Confidentiality obligations survive termination indefinitely. Technical designs, customer lists, and pricing are protected trade secrets.', 
'2025-06-01', 'Malaysia', 'IP ownership policy protects company technical knowledge and customer relationships. 6-month non-compete for senior roles prevents immediate competition. Perpetual confidentiality protects trade secrets. Electrical designs and pricing require protection.', 507),

(7010, 'contracts', 'Customer Contract Standards', 
'Enterprise contracts > RM 100,000 require Legal review. Standard terms: 12-month minimum, auto-renewal with 60-day notice, payment terms Net-30, liability cap at 12 months fees. Government contracts require additional compliance clauses.', 
'2025-06-01', 'Malaysia', 'Contract standards ensure legal review for large deals (> RM 100k). 12-month minimum provides revenue stability. Auto-renewal with opt-out protects retention. Net-30 payment standard for B2B. Liability cap limits risk exposure.', 507),

(7011, 'procurement', 'Vendor Contract Requirements', 
'Vendor contracts > RM 50,000 require Legal approval. Must include: (1) SLA terms, (2) Liability clauses, (3) Termination rights, (4) Payment terms. Emergency procurement (< 2 weeks lead time) requires CFO approval for spend > RM 100,000.', 
'2025-06-01', 'Malaysia', 'Procurement policy controls vendor commitments > RM 50k. Legal review protects company interests. SLA and liability terms essential for critical suppliers. Emergency procurement > RM 100k requires CFO approval to prevent financial risk.', 507),

(7012, 'acquisition', 'M&A Due Diligence Policy', 
'Acquisitions > RM 2M require: (1) Board approval, (2) Legal due diligence (minimum 4 weeks), (3) Financial audit, (4) Market analysis. Standard reps & warranties required. Escrow: 10-15% of purchase price for 12 months.', 
'2025-06-01', 'Malaysia', 'M&A policy governs potential competitor or supplier acquisitions. RM 2M threshold requires board involvement. 4-week due diligence ensures thorough review. Escrow (10-15%) protects against undisclosed liabilities. Strategic growth through acquisition governed.', 507);

-- Legal Contracts (43 records - one per employee)
INSERT INTO legal_contract (contract_id, employee_id, is_probation, notice_period, contract_type, start_date) VALUES
(1, 1001, 'No', 30, 'Permanent', '2022-03-15'),
(2, 1002, 'No', 30, 'Permanent', '2023-01-10'),
(3, 1003, 'No', 60, 'Permanent', '2021-06-01'),
(4, 1004, 'Yes', 30, 'Permanent', '2023-08-20'),
(5, 1005, 'No', 30, 'Permanent', '2022-11-12'),
(6, 1006, 'Yes', 30, 'Permanent', '2023-02-14'),
(7, 1007, 'No', 30, 'Permanent', '2022-09-01'),
(8, 1008, 'No', 90, 'Permanent', '2020-05-10'),
(9, 1009, 'Yes', 30, 'Permanent', '2024-01-15'),
(10, 1010, 'Yes', 30, 'Permanent', '2023-06-20'),
(11, 1011, 'No', 30, 'Permanent', '2022-07-03'),
(12, 1012, 'No', 60, 'Permanent', '2021-10-18'),
(13, 1020, 'No', 90, 'Permanent', '2020-11-05'),
(14, 1021, 'Yes', 30, 'Permanent', '2023-02-14'),
(15, 1022, 'No', 30, 'Permanent', '2022-04-10'),
(16, 1023, 'Yes', 30, 'Permanent', '2023-08-20'),
(17, 1024, 'No', 60, 'Permanent', '2021-07-18'),
(18, 1025, 'No', 60, 'Permanent', '2022-01-12'),
(19, 1026, 'Yes', 30, 'Permanent', '2023-09-05'),
(20, 1027, 'No', 30, 'Permanent', '2022-06-22'),
(21, 1028, 'Yes', 30, 'Permanent', '2023-03-10'),
(22, 1029, 'Yes', 30, 'Permanent', '2024-02-01'),
(23, 1030, 'No', 90, 'Permanent', '2021-03-08'),
(24, 1031, 'No', 30, 'Permanent', '2022-05-12'),
(25, 1032, 'Yes', 30, 'Permanent', '2023-01-20'),
(26, 1033, 'No', 30, 'Permanent', '2022-09-15'),
(27, 1034, 'Yes', 30, 'Permanent', '2023-07-01'),
(28, 1035, 'Yes', 30, 'Permanent', '2023-11-10'),
(29, 1036, 'Yes', 30, 'Permanent', '2024-01-05'),
(30, 1037, 'No', 90, 'Permanent', '2020-03-01'),
(31, 1038, 'No', 60, 'Permanent', '2021-08-15'),
(32, 1039, 'No', 30, 'Permanent', '2022-06-20'),
(33, 1040, 'Yes', 30, 'Permanent', '2023-10-01'),
(34, 1041, 'No', 90, 'Permanent', '2019-09-15'),
(35, 1042, 'No', 60, 'Permanent', '2021-04-10'),
(36, 1043, 'No', 30, 'Permanent', '2022-02-18'),
(37, 1044, 'Yes', 30, 'Permanent', '2023-05-22'),
(38, 1045, 'Yes', 30, 'Permanent', '2023-09-12'),
(39, 1046, 'No', 90, 'Permanent', '2020-07-01'),
(40, 1047, 'No', 30, 'Permanent', '2022-11-15'),
(41, 1048, 'No', 60, 'Permanent', '2021-05-20'),
(42, 1049, 'No', 30, 'Permanent', '2022-08-10'),
(43, 1050, 'Yes', 30, 'Permanent', '2023-12-01');

-- Legal Cases (10 records - employee issues)
INSERT INTO legal_cases (case_id, employee_id, issue_type, description) VALUES
(1, 1002, 'performance', 'Consistently missed frontend deadlines over last 2 sprints'),
(2, 1006, 'performance', 'QA defects increased significantly, failed quality benchmarks'),
(3, 1010, 'performance', 'Backend API delivery delayed repeatedly'),
(4, 1023, 'misconduct', 'Inappropriate communication with client reported'),
(5, 1028, 'performance', 'Sales operations errors affecting reporting accuracy'),
(6, 1034, 'performance', 'Design deliverables not meeting brand standards'),
(7, 1036, 'misconduct', 'Posted confidential campaign data on public platform'),
(8, 1040, 'performance', 'HR documentation errors and missed onboarding steps'),
(9, 1045, 'misconduct', 'Unauthorized financial data access attempt'),
(10, 1049, 'performance', 'Vendor coordination delays affecting supply chain');

-- ============================================
-- DECISION CASES (3 main cases for demo)
-- ============================================

INSERT INTO decision_case (case_id, question, context, target_type, target_id, status, submitted_by, created_at) VALUES
(8001, 'Should we terminate employee John Tan (ID 1023)?', 
'Sales executive with declining performance over 2 quarters. HR flagged for review. Sales team morale reportedly affected.', 
'employee', 1023, 'completed', 'Sarah Lim (Sales Director)', '2026-04-15 10:30:00'),

(8002, 'Should we expand to Singapore market?', 
'Received 3 inbound enterprise leads from Singapore in Q1. No local presence currently. Competitor entered SG market last quarter.', 
'market_expansion', NULL, 'completed', 'James Lim (CFO)', '2026-04-16 14:20:00'),

(8003, 'Should we emergency-procure additional transformers and MV switchgear?', 
'Multiple critical products below reorder point. Forecast shows shortage risk impacting Q2 sales pipeline. Supply chain flagged inventory crisis.', 
'procurement', NULL, 'completed', 'Azman Yusof (Procurement)', '2026-04-17 09:15:00');

-- ============================================
-- CASE EVIDENCE (linking cases to records)
-- ============================================

-- Case 8001: Fire John Tan (employee 1023)
INSERT INTO case_evidence (evidence_id, case_id, source_table, record_id, relevance_score, retrieval_method, notes) VALUES
(9001, 8001, 'hr_record', 2001, 0.92, 'sql_query', 'Q3 2025 underperformance review, score 2.8/5'),
(9002, 8001, 'hr_record', 2002, 0.98, 'sql_query', 'Q4 2025 declining performance, warning issued, score 2.1/5'),
(9003, 8001, 'hr_record', 2003, 0.99, 'sql_query', 'Q1 2026 continued underperformance, score 2.0/5, PIP recommended'),
(9004, 8001, 'sales_record', 3001, 0.88, 'sql_query', 'Q3 2025 sales: RM 18,500 (below team average)'),
(9005, 8001, 'sales_record', 3002, 0.90, 'sql_query', 'Q4 2025 sales: RM 8,500 (bottom 10% of team)'),
(9006, 8001, 'sales_record', 3003, 0.93, 'sql_query', 'Q1 2026 sales: RM 12,400 (bottom 8% of team)'),
(9007, 8001, 'sales_record', 3004, 0.85, 'sql_query', 'Q1 2026 lost enterprise transformer deal'),
(9008, 8001, 'legal_policy', 7001, 0.95, 'vector_search', 'Performance termination policy: PIP required'),
(9009, 8001, 'legal_policy', 7002, 0.92, 'vector_search', 'Severance calculation: min RM 20k for 2.5 years service'),
(9010, 8001, 'legal_policy', 7005, 0.90, 'vector_search', 'PIP guidelines: 60-day minimum duration'),
(9011, 8001, 'finance_record', 4001, 0.80, 'sql_query', 'Current salary cost: RM 10,500/month'),
(9012, 8001, 'finance_record', 4022, 0.78, 'sql_query', 'Severance reserve available: RM 150k'),
(9013, 8001, 'finance_record', 4023, 0.85, 'sql_query', 'Replacement cost estimate: RM 45k'),
(9014, 8001, 'finance_record', 4024, 0.82, 'sql_query', 'Onboarding cost estimate: RM 12k'),
(9015, 8001, 'sales_record', 3006, 0.70, 'sql_query', 'Comparison: Sarah Lim Q1 revenue RM 900k (top performer)');

-- Case 8002: Singapore expansion
INSERT INTO case_evidence (evidence_id, case_id, source_table, record_id, relevance_score, retrieval_method, notes) VALUES
(9016, 8002, 'legal_policy', 7007, 0.98, 'vector_search', 'Singapore legal requirements: Pte Ltd, local director, setup cost SGD 80-120k'),
(9017, 8002, 'finance_record', 4016, 0.85, 'sql_query', 'Q1 2026 revenue baseline: RM 2.68M'),
(9018, 8002, 'marketing_record', 5001, 0.80, 'sql_query', 'Enterprise campaign reach: 1.85M impressions'),
(9019, 8002, 'marketing_record', 5003, 0.82, 'sql_query', 'Enterprise campaign conversions: 420 leads'),
(9020, 8002, 'finance_record', 4019, 0.75, 'sql_query', 'Current infrastructure cost: RM 85k/quarter');

-- Case 8003: Emergency procurement
INSERT INTO case_evidence (evidence_id, case_id, source_table, record_id, relevance_score, retrieval_method, notes) VALUES
(9021, 8003, 'supply_record', 6001, 0.95, 'sql_query', 'LV switchgear: 12 current vs 15 reorder, shortage flagged'),
(9022, 8003, 'supply_record', 6002, 0.98, 'sql_query', '11kV MV switchgear: 3 vs 5 reorder, critical shortage'),
(9023, 8003, 'supply_record', 6005, 0.99, 'sql_query', '1000kVA transformer: 4 vs 6 reorder, enterprise demand high'),
(9024, 8003, 'supply_record', 6006, 0.97, 'sql_query', '1500kVA transformer: 1 unit remaining, critical'),
(9025, 8003, 'supply_record', 6033, 0.96, 'sql_query', 'Emergency transformer order forecast: 12 units, RM 1.02M'),
(9026, 8003, 'supply_record', 6034, 0.94, 'sql_query', 'MV switchgear replenishment: 8 units, RM 1.16M'),
(9027, 8003, 'finance_record', 4019, 0.85, 'sql_query', 'Current infrastructure budget: RM 85k/quarter'),
(9028, 8003, 'legal_policy', 7011, 0.88, 'vector_search', 'Emergency procurement policy: CFO approval for > RM 100k'),
(9029, 8003, 'supply_record', 6030, 0.80, 'sql_query', 'Vendor issue: Tenaga Transformer delays flagged'),
(9030, 8003, 'sales_record', 3007, 0.75, 'sql_query', 'Recent major transformer sale depleted inventory: RM 420k deal');

-- ============================================
-- DECISION OUTPUTS (final manager verdicts)
-- ============================================

INSERT INTO decision_output (decision_id, case_id, recommendation, risk_level, confidence_score, rationale, conservative_view, aggressive_view, manager_persona, ai_justification) VALUES
(10001, 8001,
'DO NOT TERMINATE — Initiate mandatory 60-day PIP with measurable exit criteria',
'Medium',
78,
$$**HR Agent Analysis:** Employee 1023 (John Tan) shows sustained underperformance across three consecutive quarters (Q3 2025: score 2.8/5, Q4 2025: score 2.1/5, Q1 2026: score 2.0/5). Two warnings issued. Attendance issues emerging (7 absence days Q4). However, Performance Improvement Plan (PIP) has NOT been initiated, which is mandatory per company policy (Legal Record 7001, 7005).

**Sales Agent Analysis:** Revenue contribution critically low: Q3 2025 (RM 18.5k), Q4 2025 (RM 8.5k), Q1 2026 (RM 12.4k). This places employee in bottom 8% of sales team. Comparison: top performer Sarah Lim generated RM 900k in Q1 2026. Lost 1 major enterprise transformer deal (estimated RM 120k+). Pipeline thin (only 1 stagnant solar opportunity). Team morale impact noted in reviews.

**Legal Agent Analysis:** Termination for performance is permitted ONLY after: (1) Two consecutive underperformance reviews (SATISFIED), (2) Completion of 60-day PIP (NOT SATISFIED). Company policy (Legal 7001) mandates PIP before termination. Severance cost: minimum RM 20,000 for 2.5 years of service (Legal 7002). Risk: wrongful termination claim if PIP skipped. Malaysian Employment Act requires due process.

**Finance Agent Analysis:** Current cost: RM 10,500/month salary. Termination cost breakdown: Severance RM 20k + Replacement RM 45k + Onboarding RM 12k = **Total RM 77k one-time cost**. Savings: RM 10.5k/month if not replaced, but realistically need backfill for sales coverage. Break-even: 7.3 months. Replacement ramp time: 3 months to productivity. During ramp, zero revenue from position.

**Manager Decision (Conservative Stance):**
Short-term termination cost (RM 77k total) + 3-month productivity gap during replacement ramp outweighs immediate savings. Legal risk of wrongful termination without PIP completion is significant (potential lawsuit + reputational damage). **Recommendation: Initiate mandatory 60-day PIP immediately with clear metrics: (1) Close minimum 2 deals totaling RM 50k+, (2) Generate 5 qualified enterprise opportunities, (3) Zero customer complaints, (4) Improve attendance to < 2 absence days/month.** If PIP fails, termination becomes legally justified with full documentation. This preserves optionality while protecting company from legal exposure. Cost of PIP (2 months additional salary RM 21k) is insurance against wrongful termination liability.$$,

$$Do NOT terminate - initiate PIP first. Legal risk too high without PIP completion per company policy. Replacement cost (RM 77k) + ramp time (3 months zero productivity) outweighs short-term savings. 60-day PIP provides documented exit path if performance does not improve. Conservative approach protects company legally while giving employee final chance.$$,

$$Terminate immediately - sustained underperformance hurts team morale and revenue. Bottom 8% performer for 3 consecutive quarters is clear cause. Legal policy technically allows termination after 2 reviews under 2.5/5. Severance cost (RM 20k) is acceptable. Replacement can be sourced from active pipeline within 4 weeks. Aggressive action sends clear performance message to sales team. Risk appetite higher.$$,

'conservative',
$$Conservative recommendation prioritizes legal compliance (PIP requirement) over immediate cost savings. Risk assessment values lawsuit avoidance and due process over aggressive personnel action. 78% confidence reflects strong evidence for underperformance but legal uncertainty from PIP non-completion. Balanced approach provides employee remediation opportunity while documenting failure case for justified termination if PIP unsuccessful.$$);

INSERT INTO decision_output (decision_id, case_id, recommendation, risk_level, confidence_score, rationale, conservative_view, aggressive_view, manager_persona, ai_justification) VALUES
(10002, 8002,
'EXPAND — Phased entry: Start with 2-person remote sales pod (6 months), then full office if KPIs hit',
'Low',
82,
$$**Market Agent Analysis:** Singapore electrical distribution TAM estimated at SGD 850M (MYR 4B+). Inbound signal strength: 3 enterprise leads in Q1 2026 WITHOUT local presence indicates demand validation. Competitor (Voltex Singapore) entered SG market Q4 2025, creating competitive urgency. Regional expansion aligns with ASEAN growth strategy. Singapore GDP growth 3.2% supports infrastructure investment.

**Legal Agent Analysis:** Singapore requirements (Legal 7007): (1) Pte Ltd registration (min SGD 1 paid-up capital), (2) Local director required (Singapore resident or EP holder), (3) Employment Act compliance (different from Malaysia), (4) Commercial property lease. Setup cost: SGD 80-120k (RM 380-570k). Timeline: 8-12 weeks for full entity setup. Legal complexity: MODERATE (manageable with local counsel).

**Finance Agent Analysis:** Current Q1 revenue baseline: RM 2.68M. Full office setup cost: RM 1.8M (year 1) includes: office lease (RM 480k), 5 staff (RM 900k), local entity (RM 120k), compliance (RM 80k), marketing (RM 220k). Break-even projection: 18 months if 5 enterprise deals closed (avg RM 150k each = RM 750k annual revenue). Current cash reserves: adequate to support expansion. Alternative: **remote sales pod cost RM 400k** (2 sales staff RM 300k + travel RM 60k + marketing RM 40k) for 6-month pilot.

**Marketing Agent Analysis:** Q1 2026 enterprise campaign generated 420 conversions, showing B2B demand for industrial electrical products in region. LinkedIn reach: 1.85M impressions (includes Singapore audience). Digital infrastructure ready to extend targeting to SG market. Estimated marketing spend for SG launch: RM 120k (Q2-Q3) for trade show presence and digital campaigns.

**Manager Decision (Balanced - Phased Approach):**
Inbound demand signals are REAL (3 enterprise leads without presence) but unproven at scale. Competitor entry creates first-mover urgency BUT full office commitment (RM 1.8M) is high risk without market validation. **Recommendation: Phase 1 (6 months) - Launch remote sales pod:** (1) Hire 2 sales executives based in Malaysia targeting Singapore market, (2) Monthly SG travel for in-person client meetings (4-5 days/month), (3) Target: close 2 enterprise deals generating RM 300k revenue minimum, (4) Cost: RM 400k total. **Phase 2 (conditional) - Full office:** IF Phase 1 hits KPIs (2+ deals + RM 300k revenue + 5 qualified pipeline opportunities), proceed with full Pte Ltd setup and local office (RM 1.8M investment). This approach: (1) Validates market demand at 22% cost of full commitment, (2) Limits downside to RM 400k vs RM 1.8M, (3) Preserves fast-scaling path if validated (office setup during months 4-6 of pilot), (4) Mitigates competitor first-mover advantage through immediate sales presence.$$,

$$Start with remote sales pod only (RM 400k). Validate demand for 6 months before committing RM 1.8M to full office infrastructure. Inbound leads are promising but unproven at scale. Phased approach limits financial risk while testing market. Can scale quickly if KPIs hit. Conservative validates before major investment.$$,

$$Launch full office immediately (RM 1.8M). First-mover advantage critical - competitor already in market capturing relationships. 3 inbound leads without presence proves organic demand exists. Speed wins in market expansion - establish brand presence immediately. 18-month break-even is acceptable. Commit fully to capture market share before competitor establishes dominance. Risk appetite higher.$$,

'balanced',
$$Balanced recommendation acknowledges both opportunity (inbound demand, competitor entry) and uncertainty (unproven market scale). Phased approach de-risks expansion through validation milestone (2 deals, RM 300k revenue). 82% confidence reflects strong demand signals but execution risk in new market. Cost efficiency (RM 400k pilot vs RM 1.8M full) preserves capital while maintaining strategic optionality. Risk mitigation through staged commitment.$$);

INSERT INTO decision_output (decision_id, case_id, recommendation, risk_level, confidence_score, rationale, conservative_view, aggressive_view, manager_persona, ai_justification) VALUES
(10003, 8003,
'APPROVE — Emergency-procure transformers (RM 1.02M) and MV switchgear (RM 1.16M) immediately. Total: RM 2.18M',
'High',
91,
$$**Supply Chain Agent Analysis:** CRITICAL SHORTAGE across multiple high-value product lines:
- **Transformers:** 1000kVA (4 vs 6 reorder), 1500kVA (1 unit remaining - CRITICAL), 500kVA (8 vs 10).
- **MV Switchgear:** 11kV (3 vs 5 reorder), 22kV (2 vs 3 reorder).
- **Root cause:** Sustained Q4 2025 + Q1 2026 sales (RM 2.68M revenue) depleted inventory faster than replenishment cycle. Transformer lead time 8-12 weeks means today's shortage persists 2-3 months. **Vendor issue:** Tenaga Transformer delays flagged (12-week actual vs 8-week stated lead time).

**Operations Agent (Sales Impact):** Shortage directly impacts Q2 sales pipeline:
- Enterprise deals require MV switchgear + large transformers (avg deal size RM 150-400k).
- Current pipeline: 8 enterprise opportunities totaling estimated RM 1.8M revenue AT RISK without product availability.
- Lost opportunity cost: If even 50% pipeline lost due to stockouts = RM 900k revenue loss + customer relationship damage.
- Competitor advantage: Customers will source from competitors if we cannot deliver (brand damage + market share loss).

**Finance Agent Analysis:** 
- Emergency procurement cost: Transformers (RM 1.02M) + MV Switchgear (RM 1.16M) = **RM 2.18M total**.
- Current Q1 infrastructure budget (RM 85k) insufficient - this is 25x quarterly budget.
- **Cost of inaction:** Lost revenue (RM 900k estimated) + margin impact (assume 25% margin = RM 225k gross profit lost) + customer churn risk.
- **Break-even:** If procurement enables closing even 2 major enterprise deals (RM 600k revenue = RM 150k gross profit), partially offsets procurement cost.
- Cash flow: RM 2.18M emergency spend impacts Q2 cash position but revenue recovery occurs within 60-90 days as deals close.

**Legal Agent Analysis:** 
- Emergency procurement policy (Legal 7011) allows fast-track approval for spend > RM 100k if: (1) Lead time < 2 weeks urgency (SATISFIED - stockouts imminent), (2) CFO approves (REQUIRED), (3) Business disruption risk (SATISFIED - sales pipeline at risk).
- Vendor contracts with Tenaga Transformer, Siemens, Schneider already in place - no new legal barriers.
- Risk: Tenaga Transformer delivery delays require backup vendor consideration or contractual SLA enforcement.

**Manager Decision (Aggressive - Immediate Action):**
Risk of inaction (lost sales RM 900k+, customer churn, competitor advantage) FAR EXCEEDS procurement cost (RM 2.18M). **Recommendation: APPROVE emergency procurement immediately:**

**Actions:**
1. **CFO approval obtained** for RM 2.18M emergency spend (override quarterly budget).
2. **Orders placed today:**
   - Tenaga Transformer: 12 transformers (mix of 500kVA/1000kVA/1500kVA) = RM 1.02M. Demand expedited delivery (8 weeks max) with penalty clause for delays beyond 10 weeks.
   - Siemens Malaysia: 8 MV switchgear units (11kV/22kV mix) = RM 1.16M. 8-week delivery confirmed.
3. **Supply Chain process improvement:** Root cause analysis - why did inventory reach crisis level? Implement:
   - Automated reorder point alerts (prevent future stockouts).
   - Safety stock increase for high-value, long-lead-time products (+20% buffer).
   - Backup vendor qualification (reduce Tenaga Transformer dependency).
4. **Sales team communication:** Notify enterprise sales of 8-10 week delivery timeline. Secure customer commitments now with delivery dates. Convert pipeline to orders during procurement lead time.
5. **Finance team:** Q2 budget reallocation to absorb RM 2.18M spend. Revenue recovery from deal closures offsets cost within 90 days.

**This is a SYSTEMIC ISSUE:** Q1 2026 marks SECOND major shortage event (also noted shortages in LV switchgear, cables, generators). Supply chain process overhaul required to prevent recurrence. Reactive procurement costs more than proactive inventory management.$$,

$$Approve emergency procurement but negotiate payment terms to spread cash flow impact. Order only critical items first (RM 1.5M for transformers + 11kV switchgear). Monitor Q2 demand before ordering full forecast. Cost-conscious approach balances risk and cash preservation. Conservative cash management.$$,

$$Approve FULL emergency procurement immediately (RM 2.18M). Sales pipeline disruption risk is unacceptable - lost revenue (RM 900k+) and customer churn far exceed procurement cost. Speed critical - order today with expedited delivery. Accept premium pricing for faster lead times if available. Also flag systemic procurement issue: Q1 shortage indicates process failure requiring overhaul. Aggressive action prevents revenue catastrophe.$$,

'aggressive',
$$Aggressive recommendation prioritizes revenue protection over cost optimization. 91% confidence reflects clear evidence of shortage crisis (inventory data), quantifiable sales impact (pipeline at risk), and cost-benefit strongly favoring procurement (RM 2.18M cost vs RM 900k+ revenue risk). Risk assessment values customer relationship preservation and market share defense over short-term cash conservation. Systemic issue identification (repeat shortage) requires strategic process improvement beyond immediate procurement decision.$$);

-- ============================================
-- DATA INTEGRITY VERIFICATION QUERIES
-- ============================================

-- These queries validate cross-table relationships
-- (Not executed, but documented for testing)

/*
-- Verify all foreign keys resolve
SELECT 'hr_record' as table_name, COUNT(*) as orphaned_fks
FROM hr_record h
LEFT JOIN employee e ON h.employee_id = e.employee_id
WHERE e.employee_id IS NULL;

-- Verify sales attribution
SELECT e.name, COUNT(s.sales_id) as deal_count, SUM(s.amount) as total_revenue
FROM employee e
LEFT JOIN sales_record s ON e.employee_id = s.employee_id
WHERE e.dept_id = 102
GROUP BY e.employee_id, e.name
ORDER BY total_revenue DESC;

-- Verify case evidence linking
SELECT c.case_id, c.question, COUNT(ce.evidence_id) as evidence_count
FROM decision_case c
LEFT JOIN case_evidence ce ON c.case_id = ce.case_id
GROUP BY c.case_id, c.question;

-- Verify supply-sales product linking
SELECT DISTINCT sr.product
FROM sales_record sr
WHERE sr.product NOT IN (SELECT DISTINCT item_name FROM supply_record)
AND sr.deal_stage = 'closed';

-- Verify legal contracts for all employees
SELECT COUNT(*) as employees_without_contracts
FROM employee e
LEFT JOIN legal_contract lc ON e.employee_id = lc.employee_id
WHERE lc.contract_id IS NULL;

-- Verify legal cases reference valid employees
SELECT COUNT(*) as invalid_case_references
FROM legal_cases lc
LEFT JOIN employee e ON lc.employee_id = e.employee_id
WHERE e.employee_id IS NULL;
*/
