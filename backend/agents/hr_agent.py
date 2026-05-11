"""
HR Agent — performance, attendance, warnings, PIP.
With Supabase (company_db): Zhipu JSON analysis (feature/hrlegal).
Without: local knowledge files + Gemini via _llm_analyze (legacy).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent, AgentInsight
from .llm_client import llm_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an HR specialist analyst for an AI business decision engine.
Analyze the employee profile and HR records provided and return ONLY valid JSON with no extra text:
{
  "findings": ["finding1", "finding2", "finding3"],
  "risks": ["risk1", "risk2"],
  "recommendation": "single actionable recommendation",
  "confidence": 0.75,
  "data_summary": "brief 3-5 word summary e.g. 'Senior engineer, Dept A'",
  "metric_value": "key metric e.g. '2.1/5 score'",
  "trend": "up or down or flat"
}
Cover: employee name/role/department/tenure, performance scores, attendance, warnings, PIP status.
If multiple employees appear (workforce), compare using performance_score and employee_id; for "best"
or "top" employee questions, name the employee explicitly.
"""


class HRAgent(BaseAgent):
    def __init__(self, knowledge: Any, company_db: Optional[Any] = None, llm=None):
        super().__init__(knowledge, llm)
        self._company_db = company_db
        if company_db is not None:
            logger.info("HRAgent: Supabase + Zhipu analysis path enabled")

    async def _append_workforce_snapshot(
        self, dbx: Any, evidence: List[Dict[str, Any]]
    ) -> None:
        roster = await dbx.fetch_employees_limited(100)
        if roster:
            evidence.append(
                {
                    "source": "employee_roster",
                    "type": "company_roster",
                    "data": roster,
                }
            )
        hr_sample = await dbx.fetch_hr_records_company_sample(limit=150)
        evidence.extend(
            [
                {
                    "source": "hr_record",
                    "type": "workforce_review",
                    "record_id": r.get("hr_id"),
                    "data": r,
                }
                for r in hr_sample
            ]
        )

    @staticmethod
    def _evidence_has_employee_or_hr(evidence: List[Dict[str, Any]]) -> bool:
        return any(e.get("source") in ("employee", "hr_record") for e in evidence)

    async def retrieve_evidence(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        evidence: List[Dict[str, Any]] = []

        if context.get("document_summary"):
            evidence.append(
                {
                    "source": "uploaded_document",
                    "path": context.get("document_path", "(runtime_upload)"),
                    "department": context.get("document_department", "HR"),
                    "summary": context.get("document_summary"),
                    "tags": context.get("document_tags", []),
                }
            )

        if self._company_db is not None:
            dbx = self._company_db
            employee_id = None
            if context.get("target_type") == "employee" and context.get("target_id"):
                employee_id = int(context["target_id"])
            elif context.get("target_name"):
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
                            employee_id = results[0].get("employee_id")
                    except Exception:
                        pass

            if employee_id is None:
                try:
                    await self._append_workforce_snapshot(dbx, evidence)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("HR workforce snapshot failed: %s", exc)
                return evidence

            try:
                employee = await dbx.get_employee(employee_id)
                if employee:
                    evidence.append({"source": "employee", "type": "profile", "data": employee})
            except Exception as exc:  # noqa: BLE001
                logger.warning("HR get_employee(%s) failed: %s", employee_id, exc)

            hr_records = await dbx.get_employee_hr_records(employee_id)
            evidence.extend(
                [
                    {
                        "source": "hr_record",
                        "type": "performance_review",
                        "record_id": r.get("hr_id"),
                        "data": r,
                    }
                    for r in hr_records
                ]
            )
            if not self._evidence_has_employee_or_hr(evidence):
                try:
                    await self._append_workforce_snapshot(dbx, evidence)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("HR workforce fallback (bad/missing target) failed: %s", exc)
            return evidence

        # Local knowledge (no Supabase)
        if context.get("target_type") == "employee" and context.get("target_id"):
            employee_id = context["target_id"]
            hr_records = await self.db.get_employee_hr_records(employee_id)
            evidence.extend(
                [
                    {
                        "source": "hr_record",
                        "type": "performance_review",
                        "record_id": record["hr_id"],
                        "data": record,
                    }
                    for record in hr_records
                ]
            )
        return evidence

    def _rule_based_analyze(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        """Legacy rule-based (local / fallback)."""
        hr_records = [e["data"] for e in evidence if e.get("source") == "hr_record"]
        doc_summaries = [
            e["summary"]
            for e in evidence
            if e.get("source") == "uploaded_document" and e.get("summary")
        ]

        findings: List[str] = []
        risks: List[str] = []

        if doc_summaries:
            combined_doc = " ".join(doc_summaries).lower()
            findings.append("HR document uploaded and reviewed for performance context")
            if "pip" in combined_doc:
                findings.append("PIP (Performance Improvement Plan) is mentioned in the uploaded document")
            if "warning" in combined_doc:
                findings.append("Warning history referenced in the document")
            if "attendance" in combined_doc:
                findings.append("Attendance issues noted in the uploaded document")
            if "underperform" in combined_doc or "below" in combined_doc:
                risks.append(
                    "Document indicates sustained underperformance — high unfair dismissal risk without prior PIP"
                )
            if "high" in combined_doc and "risk" in combined_doc:
                risks.append("Document flags elevated compliance or legal risk")

        if hr_records:
            recent_scores = [r["performance_score"] for r in hr_records[:3] if r.get("performance_score")]
            if recent_scores:
                avg_score = sum(recent_scores) / len(recent_scores)
                findings.append(
                    f"Average performance score (last 3 reviews): {avg_score:.1f}/5.0"
                )
                if avg_score < 2.5:
                    findings.append("Performance consistently below expectations (< 2.5/5)")
                    risks.append("Sustained underperformance documented across multiple review periods")
            total_warnings = sum(r.get("warning_count", 0) for r in hr_records)
            if total_warnings > 0:
                findings.append(f"Total formal warnings issued: {total_warnings}")
                risks.append("Disciplinary action history on record")
            pip_records = [r for r in hr_records if r.get("pip_status")]
            if pip_records:
                latest_pip = pip_records[0]["pip_status"]
                findings.append(f"PIP status: {latest_pip}")
            if not pip_records or not (pip_records[0].get("pip_status") if pip_records else None):
                if any(r.get("warning_count", 0) for r in hr_records):
                    risks.append("PIP not initiated — may be required before performance-based termination")

            if (
                recent_scores
                and sum(recent_scores) / len(recent_scores) < 2.5
                and total_warnings >= 2
            ):
                if not pip_records or not pip_records[0].get("pip_status"):
                    recommendation = (
                        "Do not fire employee yet; initiate a formal PIP first to reduce unfair dismissal risk."
                    )
                else:
                    recommendation = "Performance grounds may exist if PIP was formally completed and failed."
            else:
                recommendation = "Performance issues present; use structured review and written warnings as needed."
        else:
            recommendation = (
                "Do not fire employee yet; initiate a formal PIP first."
                if risks
                else "HR records not available from local knowledge; base decision on documentation only."
            )

        if not findings:
            findings = ["No HR evidence found in database or uploaded documents"]
        if not risks:
            risks = ["Insufficient evidence to assess risk — proceed with caution"]

        return AgentInsight(
            agent_name="HR",
            findings=findings,
            risks=risks,
            recommendation=recommendation,
            confidence=0.75 if (hr_records or doc_summaries) else 0.0,
            evidence_used=evidence,
        )

    def _rule_based_zhipu_fallback(
        self, hr_records: List[Dict[str, Any]], evidence: List[Dict[str, Any]], error_note: str = ""
    ) -> AgentInsight:
        findings, risks = [], []
        scores = [r["performance_score"] for r in hr_records[:3] if r.get("performance_score")]
        if scores:
            avg = sum(scores) / len(scores)
            findings.append(f"Average performance score: {avg:.1f}/5.0")
            if avg < 2.5:
                risks.append("Sustained underperformance documented")
        warnings = sum(r.get("warning_count", 0) for r in hr_records)
        if warnings > 0:
            findings.append(f"Total warnings: {warnings}")
            risks.append("Disciplinary history on record")
        pip = next((r.get("pip_status") for r in hr_records if r.get("pip_status")), None)
        if pip:
            findings.append(f"PIP status: {pip}")
        else:
            risks.append("PIP not yet initiated — required before many terminations per policy")
        avg_score = sum(scores) / len(scores) if scores else 3.0
        rec = (
            "Initiate a formal PIP before considering termination"
            if avg_score < 2.5
            else "Monitor with structured review"
        )
        metric = f"{avg_score:.1f}/5" if scores else "N/A"
        trend = "down" if len(scores) >= 2 and scores[0] < scores[-1] else "flat"
        return AgentInsight(
            agent_name="HR",
            findings=findings,
            risks=risks,
            recommendation=rec,
            confidence=0.7,
            evidence_used=evidence,
            emoji="👤",
            data_summary="HR performance review",
            metric_value=metric,
            trend=trend,
        )

    async def _analyze_supabase(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        hr_rows = [e["data"] for e in evidence if e.get("source") == "hr_record"]
        employee_profile = next(
            (e["data"] for e in evidence if e.get("source") == "employee"), None
        )
        roster = next(
            (e.get("data") for e in evidence if e.get("source") == "employee_roster"),
            None,
        )
        if not hr_rows:
            if employee_profile:
                name = (
                    employee_profile.get("name")
                    or employee_profile.get("full_name")
                    or "Unknown"
                )
                position = (
                    employee_profile.get("position")
                    or employee_profile.get("role")
                    or employee_profile.get("job_title")
                    or "Unknown position"
                )
                dept = employee_profile.get("dept_id", "")
                if isinstance(employee_profile.get("department"), dict):
                    dept = (employee_profile.get("department") or {}).get("name", "") or dept
                hire_date = str(employee_profile.get("hire_date") or "Unknown")
                status = (
                    "Inactive" if employee_profile.get("exit_date") else "Active"
                )
                findings = [
                    f"Employee: {name} — {position}",
                    f"Department / dept_id: {dept}" if dept else "Department: Not specified",
                    f"Hire: {hire_date} | exit_date: {status}",
                    "No performance review records on file",
                ]
                return AgentInsight(
                    agent_name="HR",
                    findings=findings,
                    risks=["Lack of HR records limits performance assessment"],
                    recommendation="Initiate performance tracking before personnel decisions",
                    confidence=0.3,
                    evidence_used=evidence,
                    emoji="👤",
                    data_summary=f"{name}, {position}",
                )
            if roster and isinstance(roster, list):
                roster_str = json.dumps(roster, default=str, indent=2)
                user_msg = (
                    f"Query: {query}\n\n"
                    "Context: roster only — no hr_record rows in evidence.\n"
                    f"Roster:\n{roster_str}"
                )
                try:
                    result = await llm_json(SYSTEM_PROMPT, user_msg)
                    return AgentInsight(
                        agent_name="HR",
                        findings=result.get("findings", []),
                        risks=result.get("risks", []),
                        recommendation=result.get("recommendation", "Add HR review data"),
                        confidence=float(result.get("confidence", 0.35)),
                        evidence_used=evidence,
                        emoji="👤",
                        data_summary=result.get("data_summary", "Roster only"),
                        metric_value=result.get("metric_value", ""),
                        trend=result.get("trend", "flat"),
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("HR Zhipu (roster-only) failed: %s", exc)
                return AgentInsight(
                    agent_name="HR",
                    findings=["Roster loaded but no hr_record rows to rank by score"],
                    risks=["Backfill hr_record to compare employees"],
                    recommendation="Seed performance data or clear an invalid target_id",
                    confidence=0.25,
                    evidence_used=evidence,
                    emoji="👤",
                )
            return AgentInsight(
                agent_name="HR",
                findings=["Employee not found or no HR records in database"],
                risks=["Cannot assess performance without data"],
                recommendation="Verify employee id and records; seed employee and hr_record if empty",
                confidence=0.0,
                evidence_used=evidence,
            )

        profile_str = (
            json.dumps(employee_profile, default=str, indent=2) if employee_profile else "N/A"
        )
        data_str = json.dumps(hr_rows, default=str, indent=2)
        extra = [e for e in evidence if e.get("source") == "uploaded_document"]
        workforce_note = (
            "\n(Workforce: compare by performance_score / employee_id; name the best if asked.)\n"
            if not employee_profile
            else ""
        )
        roster_str = ""
        if roster and not employee_profile and isinstance(roster, list):
            roster_str = (
                "\n\nRoster (names for employee_id):\n"
                + json.dumps(roster, default=str, indent=2)
            )
        user_msg = (
            f"Query: {query}{workforce_note}\n\nEmployee Profile:\n{profile_str}\n\nHR Records:\n{data_str}"
            f"{roster_str}"
        )
        if extra:
            user_msg += f"\n\nUploaded context:\n{json.dumps(extra, default=str)}"
        try:
            result = await llm_json(SYSTEM_PROMPT, user_msg)
            return AgentInsight(
                agent_name="HR",
                findings=result.get("findings", []),
                risks=result.get("risks", []),
                recommendation=result.get("recommendation", "See findings above"),
                confidence=float(result.get("confidence", 0.7)),
                evidence_used=evidence,
                emoji="👤",
                data_summary=result.get("data_summary", "HR data"),
                metric_value=result.get("metric_value", ""),
                trend=result.get("trend", "flat"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("HR Zhipu failed, using rule-based: %s", exc)
            return self._rule_based_zhipu_fallback(hr_rows, evidence, str(exc))

    async def analyze(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        if self._company_db is not None:
            return await self._analyze_supabase(evidence, query)
        fallback = self._rule_based_analyze(evidence, query)
        evidence_parts: List[str] = []
        for e in evidence:
            if e.get("source") == "uploaded_document":
                evidence_parts.append(f"Document summary: {e.get('summary', '')}")
            elif e.get("source") == "hr_record":
                data = e.get("data", {})
                evidence_parts.append(
                    f"HR Record — score: {data.get('performance_score')}, "
                    f"warnings: {data.get('warning_count')}, pip: {data.get('pip_status')}"
                )
        evidence_summary = "\n".join(evidence_parts) if evidence_parts else "No HR evidence."
        return await self._llm_analyze(
            query=query,
            evidence_summary=evidence_summary,
            domain_role="HR compliance and performance management specialist",
            domain_focus=(
                "Employee performance history, attendance, warnings, PIP status, and policy compliance."
            ),
            fallback_insight=fallback,
        )
