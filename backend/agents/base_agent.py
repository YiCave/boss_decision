"""
Base agent class for domain-specific analysis.
All agents (HR, Sales, Legal, etc.) inherit from this class.
"""
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from . import agent_logging

from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv

from services.llm_client import UnifiedLLMClient

# Ensure env vars are loaded for all agents
load_dotenv()

class AgentInsight(BaseModel):
    """Structured output from an agent."""
    model_config = ConfigDict(extra="ignore")

    agent_name: str
    findings: List[str]
    risks: List[str]
    recommendation: str
    confidence: float  # 0.0 to 1.0
    evidence_used: List[Dict[str, Any]]  # List of record IDs and sources
    # Optional: HR/Legal/Finance (Zhipu) helpers — ignored by other consumers
    emoji: Optional[str] = None
    data_summary: Optional[str] = None
    metric_value: Optional[str] = None
    trend: Optional[str] = None


class BaseAgent(ABC):
    """
    Abstract base class for domain-specific agents.
    Each agent retrieves relevant data and provides structured insights.
    """

    def __init__(self, db_service, llm=None):
        """
        Initialize agent with database service and optional LLM.

        Args:
            db_service: DatabaseService instance for data retrieval
            llm: LangChain LLM instance (optional, for AI-powered analysis)
        """
        self.db = db_service
        self.llm = llm
        self.agent_name = self.__class__.__name__.replace('Agent', '')
        # Shared LLM client for all sub-agents
        self._llm_client: UnifiedLLMClient | None = UnifiedLLMClient.from_settings()

    @abstractmethod
    async def retrieve_evidence(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve relevant evidence from database for this agent's domain.

        Args:
            query: User's decision query
            context: Additional context (target_type, target_id, etc.)

        Returns:
            List of relevant records
        """
        pass

    @abstractmethod
    async def analyze(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        """
        Analyze evidence and produce structured insights.

        Args:
            evidence: Retrieved records
            query: User's decision query

        Returns:
            AgentInsight with findings, risks, recommendation
        """
        pass

    async def _llm_analyze(
        self,
        *,
        query: str,
        evidence_summary: str,
        domain_role: str,
        domain_focus: str,
        fallback_insight: AgentInsight,
    ) -> AgentInsight:
        """
        Shared LLM-powered analysis helper for all sub-agents.

        Sends the query + evidence summary to the shared Gemini client and parses
        structured JSON findings/risks/recommendation.  Falls back gracefully to
        `fallback_insight` on any LLM or parse error.

        Args:
            query: The original user business query.
            evidence_summary: A compact plain-text summary of retrieved evidence.
            domain_role: E.g. "HR specialist", "Legal compliance reviewer".
            domain_focus: What this agent cares about (used in the prompt).
            fallback_insight: Rule-based AgentInsight to return on LLM failure.
        """
        if self._llm_client is None:
            return fallback_insight

        system_prompt = (
            f"You are a {domain_role} in a business decision-support system. "
            "Return strict JSON only with concise, practical analysis."
        )
        user_prompt = f"""
Business query: {query}

Your focus area: {domain_focus}

Evidence summary:
{evidence_summary[:6000]}

Return a single JSON object:
{{
  "findings": ["concise finding 1", "concise finding 2"],
  "risks": ["key risk 1", "key risk 2"],
  "recommendation": "single clear recommendation",
  "confidence": 0.0
}}
""".strip()

        try:
            parsed, _ = await self._llm_client.acomplete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=600,
            )
            findings = [str(f) for f in (parsed.get("findings") or [])][:4]
            risks = [str(r) for r in (parsed.get("risks") or [])][:4]
            recommendation = str(parsed.get("recommendation") or "")
            confidence = float(parsed.get("confidence", fallback_insight.confidence))

            if not findings:
                findings = fallback_insight.findings
            if not risks:
                risks = fallback_insight.risks
            if not recommendation:
                recommendation = fallback_insight.recommendation

            return AgentInsight(
                agent_name=fallback_insight.agent_name,
                findings=findings,
                risks=risks,
                recommendation=recommendation,
                confidence=max(0.0, min(confidence, 1.0)),
                evidence_used=fallback_insight.evidence_used,
            )
        except Exception as e:
            # Import logging here to avoid potential circular imports
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"LLM subagent analysis failed for {domain_role}: {str(e)}")
            # LLM unavailable or parse failed — return the rule-based fallback
            return fallback_insight

    async def run(self, query: str, context: Dict[str, Any]) -> AgentInsight:
        """
        Execute full agent pipeline: retrieve evidence + analyze.

        Args:
            query: User's decision query
            context: Additional context

        Returns:
            AgentInsight
        """
        log = logging.getLogger(self.__class__.__module__)
        label = self.agent_name or self.__class__.__name__
        log.info(
            "[%s] run_start query_preview=%r context=%s",
            label,
            (query or "")[:200],
            agent_logging.context_for_log(context),
        )
        evidence = await self.retrieve_evidence(query, context)
        ev = agent_logging.summarize_evidence(evidence)
        log.info(
            "[%s] evidence_retrieved total=%d by_source=%s types_by_source=%s",
            label,
            ev["total"],
            ev["by_source"],
            ev.get("types_by_source") or {},
        )
        insight = await self.analyze(evidence, query)
        first_f = (insight.findings[0] if insight.findings else "") or ""
        log.info(
            "[%s] analyze_done confidence=%.3f findings=%d risks=%d rec_preview=%r",
            label,
            float(insight.confidence),
            len(insight.findings or []),
            len(insight.risks or []),
            (insight.recommendation or "")[:180],
        )
        if first_f:
            log.info("[%s] first_finding: %r", label, first_f[:400])
        return insight
