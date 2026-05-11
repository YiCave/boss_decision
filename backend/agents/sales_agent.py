"""
Sales Agent - Analyzes revenue contribution, deal pipeline, sales performance.
"""
import logging
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent, AgentInsight

logger = logging.getLogger(__name__)


class SalesAgent(BaseAgent):
    """
    Sales domain specialist agent.
    Focuses on: revenue contribution, deals closed, pipeline health, quota attainment.
    """

    def __init__(self, knowledge, company_db: Optional[Any] = None, llm=None):
        super().__init__(knowledge, llm)
        self._company_db = company_db
        if company_db is not None:
            logger.info("SalesAgent: Supabase reads enabled (sales_record + shallow context)")

    async def retrieve_evidence(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve sales-related evidence.

        For employee decisions:
        - Sales records (revenue, deals closed)
        - Pipeline status
        - Deal win/loss analysis
        """
        evidence = []

        # Injected document context
        if context.get("document_summary"):
            evidence.append(
                {
                    "source": "uploaded_document",
                    "path": context.get("document_path", "(runtime_upload)"),
                    "department": context.get("document_department", "Sales"),
                    "summary": context.get("document_summary"),
                    "tags": context.get("document_tags", []),
                }
            )

        if self._company_db is not None:
            try:
                eid = context.get("target_id") if context.get("target_type") == "employee" else None
                sales_rows = await self._company_db.fetch_sales_records_for_agent(
                    limit=80,
                    employee_id=eid,
                )
                for row in sales_rows:
                    evidence.append(
                        {
                            "source": "supabase_sales_record",
                            "type": "deal",
                            "record_id": row.get("sales_id"),
                            "data": row,
                        }
                    )
                if eid is not None:
                    emp = await self._company_db.get_employee(eid)
                    if emp:
                        evidence.append({"source": "supabase_employee", "data": emp})
                    hr_sk = await self._company_db.fetch_hr_shallow_for_employee(eid, limit=8)
                    if hr_sk:
                        evidence.append(
                            {
                                "source": "supabase_hr_sketch",
                                "note": "Light cross-check only; full HR review is a separate agent.",
                                "rows": hr_sk,
                            }
                        )
                depts = await self._company_db.fetch_departments_all()
                if depts:
                    evidence.append(
                        {
                            "source": "supabase_departments_sketch",
                            "row_count": len(depts),
                            "rows": depts,
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("SalesAgent: Supabase evidence failed: %s", exc)
        else:
            # If target is an employee, get their sales records from local knowledge files
            if context.get("target_type") == "employee" and context.get("target_id"):
                employee_id = context["target_id"]
                sales_records = await self.db.get_employee_sales_records(employee_id)
                evidence.extend(
                    [
                        {
                            "source": "sales_record",
                            "type": "deal",
                            "record_id": record["sales_id"],
                            "data": record,
                        }
                        for record in sales_records
                    ]
                )

        return evidence

    # ------------------------------------------------------------------
    # Rule-based core analysis
    # ------------------------------------------------------------------

    def _rule_based_analyze(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        """Produce structured insights from pure rule-based logic."""
        sales_records = [
            e["data"]
            for e in evidence
            if e.get("source") in ("sales_record", "supabase_sales_record") and e.get("data")
        ]
        doc_summaries = [
            e["summary"] for e in evidence if e.get("source") == "uploaded_document" and e.get("summary")
        ]

        findings: List[str] = []
        risks: List[str] = []

        # Document context signals
        if doc_summaries:
            combined_doc = " ".join(doc_summaries).lower()
            findings.append("Sales-related document reviewed for performance context")
            if "revenue" in combined_doc or "sales" in combined_doc:
                findings.append("Revenue or sales performance mentioned in uploaded document")

        if not sales_records:
            recommendation = (
                "No sales database records found; assessment based on uploaded document context only"
                if doc_summaries
                else "Insufficient data for sales assessment — retrieve sales records before making decisions"
            )
            return AgentInsight(
                agent_name="Sales",
                findings=findings or ["No sales records found in the database"],
                risks=risks or ["Cannot assess sales performance without data"],
                recommendation=recommendation,
                confidence=0.2 if doc_summaries else 0.0,
                evidence_used=evidence,
            )

        closed_deals = [r for r in sales_records if r.get("deal_stage") == "closed"]
        pipeline_deals = [r for r in sales_records if r.get("deal_stage") == "pipeline"]
        lost_deals = [r for r in sales_records if r.get("deal_stage") == "lost"]

        total_revenue = sum(r.get("amount", 0) for r in closed_deals)
        deal_count = len(closed_deals)

        findings.append(f"Total closed deals: {deal_count}")
        findings.append(f"Total revenue contribution: RM {total_revenue:,.2f}")

        if deal_count > 0:
            avg_deal_size = total_revenue / deal_count
            findings.append(f"Average deal size: RM {avg_deal_size:,.2f}")

        period_revenue: dict = {}
        for record in closed_deals:
            period = record.get("period", "unknown")
            period_revenue[period] = period_revenue.get(period, 0) + record.get("amount", 0)

        if period_revenue:
            findings.append(f"Revenue by period: {period_revenue}")
            periods = sorted(period_revenue.keys())
            if len(periods) >= 2:
                latest = period_revenue[periods[-1]]
                previous = period_revenue[periods[-2]]
                if previous > 0 and latest < previous * 0.5:
                    risks.append("Revenue declined >50% quarter-over-quarter — significant performance deterioration")
                    findings.append("Sales performance trending down sharply")

        findings.append(f"Active pipeline: {len(pipeline_deals)} deals | Lost deals: {len(lost_deals)}")
        if len(pipeline_deals) < 2:
            risks.append("Pipeline health is weak — insufficient active opportunities")

        if total_revenue < 50000 and deal_count < 3:
            recommendation = "Sales performance is below team standards; revenue contribution is insufficient"
            if len(pipeline_deals) < 2:
                recommendation += ". Weak pipeline indicates a systemic performance issue"
        elif total_revenue < 100000:
            recommendation = "Sales performance is acceptable but below top-performer benchmarks"
        else:
            recommendation = "Sales performance is meeting or exceeding expectations"

        return AgentInsight(
            agent_name="Sales",
            findings=findings,
            risks=risks,
            recommendation=recommendation,
            confidence=0.80,
            evidence_used=evidence,
        )

    async def analyze(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        """Analyze sales evidence using rule-based logic enhanced by LLM."""
        fallback = self._rule_based_analyze(evidence, query)

        evidence_parts: List[str] = []
        for e in evidence:
            if e.get("source") == "uploaded_document":
                evidence_parts.append(f"Document summary: {e.get('summary', '')}")
            elif e.get("source") in ("sales_record", "supabase_sales_record"):
                data = e.get("data", {})
                evidence_parts.append(
                    f"Deal — stage: {data.get('deal_stage')}, amount: {data.get('amount')}, period: {data.get('period')}"
                )
            elif e.get("source") == "supabase_employee" and e.get("data"):
                d = e["data"]
                evidence_parts.append(
                    f"Employee (DB): {d.get('name', '')} | role: {d.get('role', '')} | id: {d.get('employee_id')}"
                )
            elif e.get("source") == "supabase_departments_sketch":
                evidence_parts.append(
                    f"Departments (sketch, {e.get('row_count', 0)} rows): {e.get('rows', [])!s}"[:2000]
                )
            elif e.get("source") == "supabase_hr_sketch":
                evidence_parts.append(
                    f"HR (sketch, cross-check only): {e.get('rows', [])!s}"[:2500]
                )
        evidence_summary = "\n".join(evidence_parts) if evidence_parts else "No sales evidence retrieved."

        return await self._llm_analyze(
            query=query,
            evidence_summary=evidence_summary,
            domain_role="sales performance analyst",
            domain_focus=(
                "Revenue contribution, deal pipeline health, quota attainment, "
                "closed/lost/pipeline deal ratios, and quarter-over-quarter trend analysis."
            ),
            fallback_insight=fallback,
        )
