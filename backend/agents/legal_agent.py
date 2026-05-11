"""
Legal Agent — policies, contracts, cases.
With Supabase: Zhipu (feature/hrlegal). Without: local policy docs + Gemini.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent, AgentInsight
from .llm_client import llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Legal compliance analyst for an AI business decision engine.
Analyze the legal data provided (policies, contracts, cases) and return ONLY valid JSON:
{
  "findings": ["finding1", "finding2", "finding3"],
  "risks": ["risk1", "risk2"],
  "recommendation": "single actionable legal recommendation",
  "confidence": 0.80,
  "data_summary": "brief 3-5 word summary",
  "metric_value": "e.g. notice period, severance",
  "trend": "up or down or flat"
}
Focus: policies, contracts, legal risk, Malaysian employment law context.
"""


class LegalAgent(BaseAgent):
    def __init__(self, knowledge: Any, company_db: Optional[Any] = None, llm=None):
        super().__init__(knowledge, llm)
        self._company_db = company_db
        if company_db is not None:
            logger.info("LegalAgent: Supabase + Zhipu analysis path enabled")

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
        evidence: List[Dict[str, Any]] = []

        if self._company_db is not None:
            dbx = self._company_db
            category_map = {
                "termination": ["termination", "compliance", "performance"],
                "expansion": ["expansion", "compliance"],
                "procurement": ["procurement", "contracts"],
                "acquisition": ["acquisition", "contracts", "compliance"],
            }
            category = context.get("query_category", "") or ""
            cats = category_map.get(str(category), [])
            all_policies = await dbx.get_legal_policies()
            relevant = [p for p in (all_policies or []) if (not cats) or p.get("policy_category") in cats]
            evidence.extend(
                [
                    {
                        "source": "legal_policy",
                        "type": "policy",
                        "record_id": p.get("legal_id"),
                        "data": p,
                    }
                    for p in relevant
                ]
            )
            emp_id = await self._resolve_employee_id(context, dbx)
            if emp_id is not None:
                try:
                    contracts = await dbx.get_legal_contracts(emp_id)
                    evidence.extend(
                        [
                            {
                                "source": "legal_contract",
                                "type": "contract",
                                "record_id": c.get("contract_id"),
                                "data": c,
                            }
                            for c in contracts
                        ]
                    )
                    cases = await dbx.get_legal_cases(emp_id)
                    evidence.extend(
                        [
                            {
                                "source": "legal_cases",
                                "type": "case",
                                "record_id": c.get("case_id"),
                                "data": c,
                            }
                            for c in cases
                        ]
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Legal employee data fetch: %s", exc)
            if context.get("document_summary"):
                evidence.append(
                    {
                        "source": "uploaded_document",
                        "path": context.get("document_path", "(runtime_upload)"),
                        "department": context.get("document_department", "legal"),
                        "summary": context.get("document_summary"),
                        "tags": context.get("document_tags", []),
                    }
                )
            return evidence

        # Local / no Supabase
        try:
            docs = await self.db.get_department_documents("legal")
            evidence.extend(docs or [])
        except Exception:
            pass
        if context.get("document_summary"):
            evidence.append(
                {
                    "source": "uploaded_document",
                    "path": context.get("document_path", "(runtime_upload)"),
                    "department": context.get("document_department", "unknown"),
                    "summary": context.get("document_summary"),
                    "tags": context.get("document_tags", []),
                }
            )
        return evidence

    def _rule_based_analyze(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        """Legacy rules for non-Supabase path."""
        if not evidence:
            return AgentInsight(
                agent_name="Legal",
                findings=["No legal or policy documents in the knowledge base"],
                risks=["Compliance position unclear without policy evidence"],
                recommendation="Obtain internal HR/legal policy before action",
                confidence=0.35,
                evidence_used=[],
            )
        summaries = [str(item.get("summary", "")).strip() for item in evidence if item.get("summary")]
        combined = " ".join(summaries).lower()
        findings: List[str] = ["Legal review against available policy evidence"]
        risks: List[str] = []
        if "pip" in combined or "due process" in combined:
            findings.append("Due process and PIP sequencing are material to compliance")
        if "termination" in query.lower() or "dismissal" in combined:
            risks.append("Termination without due process may create liability")
        if not risks:
            risks.append("Review policy detail before final action")
        return AgentInsight(
            agent_name="Legal",
            findings=findings,
            risks=risks,
            recommendation="Ensure documented process; consult policy",
            confidence=0.65,
            evidence_used=evidence,
        )

    async def _analyze_supabase(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        if not evidence:
            return AgentInsight(
                agent_name="Legal",
                findings=["No legal records matched"],
                risks=["Cannot assess legal risk without data"],
                recommendation="Engage legal team",
                confidence=0.0,
                evidence_used=[],
                emoji="⚖️",
            )
        data_str = json.dumps([e.get("data") for e in evidence if e.get("data")], default=str, indent=2)
        user_msg = f"Query: {query}\n\nLegal Data:\n{data_str}"
        try:
            result = await llm_json(SYSTEM_PROMPT, user_msg)
            return AgentInsight(
                agent_name="Legal",
                findings=result.get("findings", []),
                risks=result.get("risks", []),
                recommendation=result.get("recommendation", "Review legal findings"),
                confidence=float(result.get("confidence", 0.8)),
                evidence_used=evidence,
                emoji="⚖️",
                data_summary=result.get("data_summary", "Legal check"),
                metric_value=result.get("metric_value", ""),
                trend=result.get("trend", "flat"),
            )
        except Exception:  # noqa: BLE001
            return AgentInsight(
                agent_name="Legal",
                findings=["Legal records retrieved for policy review", f"{len(evidence)} item(s)"],
                risks=["Verify Employment Act 1955 notice/severance requirements"],
                recommendation="Align actions with company policies and statute",
                confidence=0.6,
                evidence_used=evidence,
                emoji="⚖️",
                data_summary="Legal policy review",
            )

    async def analyze(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        if self._company_db is not None:
            return await self._analyze_supabase(evidence, query)
        fallback = self._rule_based_analyze(evidence, query)
        parts: List[str] = []
        for e in evidence:
            s = e.get("summary", "")
            if s:
                parts.append(f"Document/policy summary: {s}")
        evidence_summary = "\n".join(parts) if parts else "No legal documents found."
        return await self._llm_analyze(
            query=query,
            evidence_summary=evidence_summary,
            domain_role="employment law and HR compliance specialist",
            domain_focus="Due process, unfair dismissal, PIP, evidentiary requirements.",
            fallback_insight=fallback,
        )
