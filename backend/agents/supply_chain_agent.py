"""
Supply Chain Agent — combines local knowledge + optional Supabase supply_record reads.
Used by manager orchestration (docs) and /api/supply-chain/* (inventory checks).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent, AgentInsight

logger = logging.getLogger(__name__)


class SupplyChainAgent(BaseAgent):
    """
    Operational + inventory domain agent.
    - Local: department documents (supply_chain, operations)
    - Supabase: supply_record when company_db is set and supply_id is in context
    """

    LOW_INVENTORY_THRESHOLD = 1000

    def __init__(self, knowledge: Any, company_db: Optional[Any] = None, llm=None):
        super().__init__(knowledge, llm)
        self._company_db = company_db
        if company_db is not None:
            logger.info("SupplyChainAgent: Supabase supply_record reads enabled")

    async def retrieve_evidence(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        evidence: List[Dict[str, Any]] = []

        try:
            docs = await self.db.get_department_documents("supply_chain")
            evidence.extend(docs)
        except Exception:
            pass

        try:
            docs_ops = await self.db.get_department_documents("operations")
            evidence.extend(docs_ops)
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

        supply_id = context.get("supply_id")
        if not supply_id and context.get("target_type") in {"supply", "supply_record"}:
            supply_id = context.get("target_id")

        if self._company_db is not None and supply_id:
            try:
                supply_record = await self._company_db.get_supply_record(int(supply_id))
                if supply_record:
                    evidence.append(
                        {
                            "source": "supply_record",
                            "type": "inventory",
                            "record_id": supply_record.get("supply_id"),
                            "data": supply_record,
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("SupplyChain: get_supply_record failed: %s", exc)

        return evidence

    def _rule_based_from_docs(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        findings: List[str] = []
        risks: List[str] = []

        if not evidence:
            return AgentInsight(
                agent_name="Supply Chain",
                findings=["No operations or supply chain evidence found"],
                risks=["Delivery feasibility is uncertain without logistics evidence"],
                recommendation="Collect inventory levels and lead-time data before committing to any delivery or scaling plan",
                confidence=0.35,
                evidence_used=[],
            )

        summaries = [str(item.get("summary", "")).strip() for item in evidence if item.get("summary")]
        combined = " ".join(summaries).lower()

        findings.append("Operational evidence reviewed for delivery risk and capacity constraints")
        if "inventory" in combined or "stock" in combined:
            findings.append("Inventory or stock level signals detected in evidence")
        if "logistics" in combined or "lead time" in combined:
            findings.append("Logistics or lead-time data present — delivery schedule can be estimated")
        if "supplier" in combined:
            findings.append("Supplier dependency signals detected")
        if "warehouse" in combined or "fulfillment" in combined:
            findings.append("Fulfillment and warehousing data available for capacity assessment")

        if "delay" in combined or "shortage" in combined:
            risks.append("Potential supply disruption risk — shortages or delays flagged in evidence")
        if "critical" in combined and "delay" in combined:
            risks.append("Critical path delay detected — immediate bottleneck mitigation required")
        if "single source" in combined or "single supplier" in combined:
            risks.append("Single-source supplier dependency creates concentration risk")

        recommendation = "Proceed with phased rollout and monitor fulfillment KPIs closely"
        if "critical" in combined and "delay" in combined:
            recommendation = "Do not scale operations until a bottleneck mitigation plan is in place and validated"
        elif risks:
            recommendation = "Address identified supply-chain risks before scaling — prepare contingency supplier options"

        return AgentInsight(
            agent_name="Supply Chain",
            findings=findings,
            risks=risks,
            recommendation=recommendation,
            confidence=0.74,
            evidence_used=evidence,
        )

    def _analyze_supply_record_row(
        self, record: Dict[str, Any], evidence: List[Dict[str, Any]]
    ) -> AgentInsight:
        item_name = record.get("item_name", "Unknown item")
        supplier_name = record.get("supplier_name") or "Unknown supplier"
        inventory_level = record.get("inventory_level")
        unit_cost = record.get("unit_cost")

        findings = [
            f"Supply item: {item_name}",
            f"Current inventory level: {inventory_level}",
            f"Supplier: {supplier_name}",
            (
                f"Unit price per item: RM {unit_cost:,.2f}"
                if unit_cost is not None
                else "Unit price per item: Not available"
            ),
        ]
        risks: List[str] = []

        if inventory_level is None:
            risks.append("Inventory level is missing; restock trigger cannot be evaluated reliably")
            recommendation = "Verify inventory tracking data before taking procurement action"
            confidence = 0.6
        elif inventory_level < self.LOW_INVENTORY_THRESHOLD:
            risks.append(
                f"Low inventory detected: {inventory_level} is below threshold {self.LOW_INVENTORY_THRESHOLD}"
            )
            recommendation = (
                f"Trigger restock notification for {item_name} and coordinate replenishment with {supplier_name}"
            )
            confidence = 0.92
        else:
            recommendation = f"Inventory is sufficient for {item_name}; restock notification not required"
            confidence = 0.9

        return AgentInsight(
            agent_name="SupplyChain",
            findings=findings,
            risks=risks,
            recommendation=recommendation,
            confidence=confidence,
            evidence_used=evidence,
        )

    async def analyze(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        supply_rows = [e for e in evidence if e.get("source") == "supply_record"]
        if supply_rows and evidence and all(
            (e.get("source") == "supply_record") for e in evidence
        ):
            return self._analyze_supply_record_row(supply_rows[0]["data"], evidence)

        fallback = self._rule_based_from_docs(evidence, query)
        evidence_parts: List[str] = []
        for e in evidence:
            summary = e.get("summary", "")
            if summary:
                evidence_parts.append(f"Operations/supply chain evidence: {summary}")
        evidence_summary = "\n".join(evidence_parts) if evidence_parts else "No supply chain evidence found."

        return await self._llm_analyze(
            query=query,
            evidence_summary=evidence_summary,
            domain_role="supply chain and operations risk analyst",
            domain_focus=(
                "Inventory levels, logistics lead times, supplier dependencies, "
                "fulfillment capacity, delivery schedule risk, and operational bottleneck identification."
            ),
            fallback_insight=fallback,
        )
