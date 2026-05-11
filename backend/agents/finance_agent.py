"""
Finance Agent — budgets, costs, KPIs, ROI (Supabase + Zhipu from feature/hrlegal).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent, AgentInsight
from .llm_client import llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Finance analyst for an AI business decision engine.
Analyze the financial records provided and return ONLY valid JSON:
{
  "findings": ["finding1", "finding2", "finding3"],
  "risks": ["risk1", "risk2"],
  "recommendation": "single actionable financial recommendation",
  "confidence": 0.80,
  "data_summary": "brief summary",
  "metric_value": "e.g. RM 65k total",
  "trend": "up or down or flat"
}
Focus: cost of action vs inaction, budget headroom, ROI, financial risk. Currency: Malaysian Ringgit (RM).
Rows with null employee_id are often platform/vendor; prioritize rows with employee_id for pay/salary context.
"""


class FinanceAgent(BaseAgent):
    def __init__(self, knowledge: Any, company_db: Optional[Any] = None, llm=None):
        super().__init__(knowledge, llm)
        self._company_db = company_db
        if company_db is not None:
            logger.info("FinanceAgent: Supabase + Zhipu analysis path enabled")

    async def _resolve_employee_id(self, context: Dict[str, Any], dbx: Any) -> Optional[int]:
        if context.get("target_type") == "employee" and context.get("target_id"):
            return int(context["target_id"])
        if context.get("target_name"):
            raw = re.sub(
                r"employee\s*#?\d*\s*",
                "",
                str(context["target_name"]),
                flags=re.IGNORECASE,
            ).strip()
            if raw and not raw.isdigit():
                try:
                    results = await dbx.search_employees_by_name(raw)
                    if results:
                        return int(results[0].get("employee_id"))
                except Exception:
                    pass
        return None

    async def retrieve_evidence(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self._company_db is None:
            return []
        dbx = self._company_db
        evidence: List[Dict[str, Any]] = []
        emp_id = await self._resolve_employee_id(context, dbx)

        if context.get("document_summary"):
            evidence.append(
                {
                    "source": "uploaded_document",
                    "summary": context.get("document_summary"),
                }
            )

        if emp_id is not None:
            try:
                records = await dbx.get_finance_records(employee_id=emp_id)
                if records:
                    evidence.extend(
                        [
                            {
                                "source": "finance_record",
                                "type": "employee_finance",
                                "record_id": r.get("finance_id"),
                                "data": r,
                            }
                            for r in records
                        ]
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Finance employee records: %s", exc)
            if not any(e.get("source") == "finance_record" for e in evidence):
                try:
                    employee = await dbx.get_employee(emp_id)
                    dept_id = employee.get("dept_id") if employee else None
                    if dept_id is not None:
                        records = await dbx.get_finance_records(dept_id=int(dept_id), limit=10)
                        if records:
                            evidence.extend(
                                [
                                    {
                                        "source": "finance_record",
                                        "type": "department_finance",
                                        "record_id": r.get("finance_id"),
                                        "data": r,
                                    }
                                    for r in records[:10]
                                ]
                            )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Finance dept context: %s", exc)
            if not any(e.get("source") == "finance_record" for e in evidence):
                try:
                    records = await dbx.get_finance_records_employee_linked(limit=80)
                    ftype = "payroll_context_finance"
                    if not records:
                        records = await dbx.get_finance_records(limit=50)
                        ftype = "general_finance"
                    if records:
                        cap = 40 if ftype == "payroll_context_finance" else 30
                        evidence.extend(
                            [
                                {
                                    "source": "finance_record",
                                    "type": ftype,
                                    "record_id": r.get("finance_id"),
                                    "data": r,
                                }
                                for r in records[:cap]
                            ]
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Finance fallback (no per-target rows): %s", exc)
            return evidence

        try:
            records = await dbx.get_finance_records_employee_linked(limit=80)
            ftype = "payroll_context_finance"
            if not records:
                records = await dbx.get_finance_records(limit=50)
                ftype = "general_finance"
            if records:
                cap = 40 if ftype == "payroll_context_finance" else 30
                evidence.extend(
                    [
                        {
                            "source": "finance_record",
                            "type": ftype,
                            "record_id": r.get("finance_id"),
                            "data": r,
                        }
                        for r in records[:cap]
                    ]
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Finance general records: %s", exc)
        return evidence

    async def analyze(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        if self._company_db is None:
            return AgentInsight(
                agent_name="Finance",
                findings=["Finance analysis requires a configured database (Supabase)."],
                risks=["No financial data retrieved"],
                recommendation="Connect Supabase and seed finance_record to use this agent.",
                confidence=0.0,
                evidence_used=[],
                emoji="💰",
            )
        if not any(e.get("source") == "finance_record" for e in evidence):
            return AgentInsight(
                agent_name="Finance",
                findings=["No financial records in database for this query context"],
                risks=["Cannot quantify financial impact without data"],
                recommendation="Add finance_record rows or provide employee/dept target",
                confidence=0.0,
                evidence_used=evidence,
                emoji="💰",
            )
        data_str = json.dumps(
            [e["data"] for e in evidence if e.get("source") == "finance_record"],
            default=str,
            indent=2,
        )
        source_type = "general"
        for e in evidence:
            if e.get("type"):
                source_type = e.get("type", "general")
                break
        context_note = ""
        if source_type == "department_finance":
            context_note = "\n(Department-level; employee-level rows missing.)"
        elif source_type == "payroll_context_finance":
            context_note = "\n(Rows with employee_id set — payroll / per-person cost context.)"
        elif source_type == "general_finance":
            context_note = (
                "\n(General finance sample; null employee_id may be platform e-commerce, not salary baselines.)"
            )
        user_msg = f"Query: {query}{context_note}\n\nFinancial Records:\n{data_str}"
        extra = [e for e in evidence if e.get("source") == "uploaded_document"]
        if extra:
            user_msg += f"\n\nUpload context: {json.dumps(extra, default=str)}"
        try:
            result = await llm_json(SYSTEM_PROMPT, user_msg)
            return AgentInsight(
                agent_name="Finance",
                findings=result.get("findings", []),
                risks=result.get("risks", []),
                recommendation=result.get("recommendation", "Review financials carefully"),
                confidence=float(result.get("confidence", 0.75)),
                evidence_used=evidence,
                emoji="💰",
                data_summary=result.get("data_summary", "Financial analysis"),
                metric_value=result.get("metric_value", ""),
                trend=result.get("trend", "flat"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Finance Zhipu failed: %s", exc)
            return AgentInsight(
                agent_name="Finance",
                findings=[f"Analyzed {len([e for e in evidence if e.get('source') == 'finance_record'])} records (fallback)."],
                risks=["Re-validate before committing spend"],
                recommendation="Re-run with valid Zhipu config or check data",
                confidence=0.5,
                evidence_used=evidence,
                emoji="💰",
            )
