"""
Manager Agent - Orchestrates domain agents and synthesizes final decision.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .base_agent import AgentInsight
from . import agent_logging
from services.llm_client import UnifiedLLMClient

logger = logging.getLogger(__name__)


class ManagerAgent:
    """Manager orchestrator with dynamic LLM routing and TLDR synthesis."""

    def __init__(self, agents: List[Any], llm=None):
        self.agents = agents
        self.llm = llm
        self.agent_registry = self._build_agent_registry(agents)
        self.router_client = UnifiedLLMClient.from_settings()
        self.router_init_error = None if self.router_client else "GOOGLE_API_KEY not configured"
        self.supported_departments = [
            "hr",
            "sales",
            "legal",
            "finance",
            "marketing",
            "supply_chain",
            "operations",
        ]

    def _build_agent_registry(self, agents: List[Any]) -> Dict[str, Any]:
        registry: Dict[str, Any] = {}
        for agent in agents:
            canonical = self._canonical_agent_name(getattr(agent, "agent_name", agent.__class__.__name__))
            registry[canonical] = agent
        return registry

    def _canonical_agent_name(self, raw_name: str) -> str:
        lowered = (raw_name or "").strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "hragent": "hr",
            "hr": "hr",
            "salesagent": "sales",
            "sales": "sales",
            "legalagent": "legal",
            "legal": "legal",
            "financeagent": "finance",
            "finance": "finance",
            "marketingagent": "marketing",
            "marketing": "marketing",
            "supplychainagent": "supply_chain",
            "supplychain": "supply_chain",
            "supply_chain": "supply_chain",
            "operationsagent": "operations",
            "operations": "operations",
            "operation": "operations",
        }
        lowered = lowered.replace("_agent", "agent")
        return aliases.get(lowered, lowered)

    @staticmethod
    def _extract_json_object(raw: str) -> Dict[str, Any] | None:
        text = (raw or "").strip()
        if not text:
            return None

        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()

        if text.startswith("{") and text.endswith("}"):
            try:
                return json.loads(text)
            except Exception:
                return None

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return None

        return None

    def _derive_agents_from_text(self, text: str) -> List[str]:
        """
        Keyword-free derivation: ask the LLM directly. This is only used as a
        last-resort text-mode fallback inside route_agents, after a failed JSON
        parse.  We scan for department names that the LLM itself wrote in its
        response — no extra keyword lists needed.
        """
        lowered = (text or "").lower()
        selected = [dept for dept in self.supported_departments if dept.replace("_", " ") in lowered or dept in lowered]
        return list(dict.fromkeys(selected))

    async def route_agents(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Select target departments dynamically with LLM."""
        doc_summary = context.get("document_summary")
        doc_department = context.get("document_department")
        allowed = ", ".join(self.supported_departments)

        llm_error = None
        if self.router_client is not None:
            system_prompt = "You are a business manager router. Return strict JSON only."
            user_prompt = f"""
Pick the MINIMUM departments required to answer this business query.

Allowed departments: [{allowed}]
User query: {query}
Optional extracted document department: {doc_department}
Optional extracted document summary: {doc_summary}
Optional target_type: {context.get('target_type')}
Optional target_id: {context.get('target_id')}

Output JSON schema:
{{
  "selected_agents": ["hr", "legal"],
  "reasoning": "short explanation",
  "confidence": 0.0
}}
""".strip()
            try:
                parsed, model_used = await self.router_client.acomplete_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.1,
                    max_tokens=500,
                )
                selected_raw = parsed.get("selected_agents", [])
                selected = [
                    self._canonical_agent_name(name)
                    for name in selected_raw
                    if self._canonical_agent_name(name) in self.supported_departments
                ]
                selected = list(dict.fromkeys(selected))
                if selected:
                    return {
                        "selected_agents": selected,
                        "reasoning": parsed.get("reasoning", "LLM routing completed"),
                        "confidence": float(parsed.get("confidence", 0.7)),
                        "route_source": "llm",
                        "model_used": model_used,
                    }
                llm_error = "LLM returned no valid selected_agents"
            except Exception as exc:
                llm_error = str(exc)

            # Text-mode fallback for providers that occasionally return non-JSON/empty output.
            try:
                text_output = await self.router_client.acomplete_text(
                    system_prompt="You are a business manager router.",
                    user_prompt=(
                        f"Choose minimum departments from [{allowed}] for this query: {query}. "
                        "If uncertain, mention 1-2 departments and why in one sentence."
                    ),
                    temperature=0.1,
                    max_tokens=180,
                )
                parsed = self._extract_json_object(text_output.text)
                if parsed:
                    selected = [
                        self._canonical_agent_name(name)
                        for name in parsed.get("selected_agents", [])
                        if self._canonical_agent_name(name) in self.supported_departments
                    ]
                else:
                    selected = [
                        s for s in self._derive_agents_from_text(text_output.text)
                        if s in self.supported_departments
                    ]

                if selected:
                    return {
                        "selected_agents": selected,
                        "reasoning": (text_output.text or "LLM text routing fallback used")[:240],
                        "confidence": 0.62,
                        "route_source": "llm",
                        "model_used": text_output.model,
                    }
            except Exception as exc:
                llm_error = f"{llm_error} | text_fallback: {str(exc)}" if llm_error else str(exc)

        # --- Pure structural fallback (no hardcoded topic keywords) ---
        selected = []
        if isinstance(doc_department, str):
            canonical = self._canonical_agent_name(doc_department)
            if canonical in self.supported_departments:
                selected.append(canonical)

        target_type = (context.get("target_type") or "").strip().lower()
        if not selected and target_type == "employee":
            selected = ["hr", "legal"]

        if not selected:
            # Last resort: ask LLM synchronously what departments fit — if that
            # also fails we fall back to a neutral two-department default that
            # covers the broadest set of queries without domain bias.
            selected = ["hr", "sales"]
            logger.warning("Manager routing fully degraded — defaulted to ['hr', 'sales']. LLM error: %s", llm_error)

        return {
            "selected_agents": selected,
            "reasoning": "Fallback routing used because LLM routing was unavailable.",
            "confidence": 0.45,
            "route_source": "fallback",
            "route_error": llm_error or self.router_init_error,
        }

    async def _llm_subagent_reply(self, department: str, query: str, context: Dict[str, Any]) -> AgentInsight:
        """Generate a lightweight simulated sub-agent insight via LLM."""
        label = department.replace("_", " ").title()

        if self.router_client is None:
            return AgentInsight(
                agent_name=label,
                findings=[f"{label} agent selected but LLM client is unavailable."],
                risks=["Sub-agent analysis is degraded due to missing LLM configuration."],
                recommendation=f"Configure GOOGLE_API_KEY to enable dynamic {label} analysis.",
                confidence=0.3,
                evidence_used=[{"source": "manager_router", "detail": "llm_not_configured"}],
            )

        system_prompt = (
            "You are a specialized business sub-agent. Return strict JSON only with concise, practical analysis."
        )
        user_prompt = f"""
Department role: {label}
Business query: {query}
Context JSON: {context}

Return JSON only:
{{
  "findings": ["point 1", "point 2"],
  "risks": ["risk 1", "risk 2"],
  "recommendation": "single-line recommendation",
  "confidence": 0.0
}}
""".strip()

        try:
            parsed, _ = await self.router_client.acomplete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=800,
            )
            findings = parsed.get("findings") or [f"{label} analysis completed."]
            risks = parsed.get("risks") or [f"No major {label.lower()} risk flagged."]
            recommendation = parsed.get("recommendation") or f"Proceed with {label.lower()} guardrails."
            confidence = float(parsed.get("confidence", 0.7))

            return AgentInsight(
                agent_name=label,
                findings=[str(x) for x in findings][:4],
                risks=[str(x) for x in risks][:4],
                recommendation=str(recommendation),
                confidence=max(0.0, min(confidence, 1.0)),
                evidence_used=[
                    {
                        "source": "gemini_llm",
                        "detail": f"dynamic_sub_agent_{department}",
                    }
                ],
            )
        except Exception as exc:
            try:
                text_output = await self.router_client.acomplete_text(
                    system_prompt=f"You are the {label} business sub-agent.",
                    user_prompt=(
                        f"Query: {query}\n"
                        f"Context: {context}\n"
                        "List exactly 2 findings, 1 key risk, and 1 recommendation. "
                        "Use plain numbered lines: '1. ...', '2. ...', 'Risk: ...', 'Recommendation: ...'"
                    ),
                    temperature=0.25,
                    max_tokens=400,
                )
                body = (text_output.text or "").strip()
                if body:
                    import re as _re
                    # Parse structured numbered/labelled lines robustly.
                    findings: list[str] = []
                    risk_line = ""
                    rec_line = ""
                    for raw_line in body.splitlines():
                        stripped = raw_line.strip(" -\t")
                        if not stripped:
                            continue
                        lower = stripped.lower()
                        if lower.startswith("risk"):
                            risk_line = _re.sub(r'^risk[:\s]*', '', stripped, flags=_re.IGNORECASE).strip()
                        elif lower.startswith("recommendation") or lower.startswith("recommend"):
                            rec_line = _re.sub(r'^recommend\w*[:\s]*', '', stripped, flags=_re.IGNORECASE).strip()
                        else:
                            # Strip leading "1. " / "2. " / "- " prefixes.
                            clean = _re.sub(r'^[\d]+[.)\s]+', '', stripped).strip()
                            if clean and len(findings) < 3:
                                findings.append(clean)

                    if not findings:
                        findings = [body[:200]]
                    if not rec_line:
                        rec_line = findings[-1] if findings else body[:180]
                    risk_str = risk_line or f"Structured JSON parse failed; used text-mode fallback for {label.lower()} analysis."

                    return AgentInsight(
                        agent_name=label,
                        findings=findings[:3],
                        risks=[risk_str],
                        recommendation=rec_line,
                        confidence=0.58,
                        evidence_used=[{"source": "llm_text_fallback", "detail": f"{department}_non_json_response"}],
                    )
            except Exception:
                pass

            return AgentInsight(
                agent_name=label,
                findings=[
                    f"{label} analysis completed with reduced confidence (LLM service temporarily unavailable).",
                    "Rule-based assessment applied using available context.",
                ],
                risks=[
                    f"LLM-enhanced {label.lower()} analysis could not be completed — using fallback policy rules.",
                    "Verify LLM API connectivity and retry for a higher-confidence assessment.",
                ],
                recommendation=(
                    f"Proceed cautiously: {label} considerations apply to this decision. "
                    "Consult the relevant department lead for a detailed review given the reduced AI confidence."
                ),
                confidence=0.35,
                evidence_used=[{"source": "fallback", "detail": f"{department}_degraded_analysis"}],
            )

    async def orchestrate_dynamic(
        self, 
        query: str, 
        context: Dict[str, Any], 
        forced_agents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Dynamically route or use forced agents, then execute and synthesize."""
        logger.info(
            "[Manager] orchestrate_start context=%s",
            agent_logging.context_for_log(context),
        )
        if forced_agents:
            logger.info("\n[Manager] Using FORCED agents: %s", forced_agents)
            selected_names = forced_agents
            routing = {
                "selected_agents": selected_names,
                "reasoning": "User manually selected specific agents.",
                "confidence": 1.0,
                "route_source": "manual"
            }
        else:
            logger.info("\n[Manager] Routing query: %s...", query[:100])
            routing = await self.route_agents(query, context)
            selected_names = routing.get("selected_agents", [])
            logger.info(
                "[Manager] route_done agents=%s source=%s confidence=%.2f reasoning=%r",
                selected_names,
                routing.get("route_source"),
                float(routing.get("confidence") or 0),
                (routing.get("reasoning") or "")[:200],
            )
        
        force_simple_llm = bool(context.get("force_simple_llm_subagents", False))

        agent_insights: List[AgentInsight] = []
        for name in selected_names:
            logger.info(
                "[Manager] executing_agent: %s (force_simple_llm=%s)", name, force_simple_llm
            )
            if force_simple_llm:
                insight = await self._llm_subagent_reply(name, query, context)
                agent_insights.append(insight)
                logger.info(
                    "[Manager] agent_finished: %s (simple_llm) confidence=%.2f",
                    name,
                    float(insight.confidence),
                )
                continue

            agent = self.agent_registry.get(name)
            if agent is None:
                logger.info("[Manager] Agent '%s' not found in registry, using simple LLM reply.", name)
                insight = await self._llm_subagent_reply(name, query, context)
                agent_insights.append(insight)
                logger.info(
                    "[Manager] agent_finished: %s (registry_miss) confidence=%.2f",
                    name,
                    float(insight.confidence),
                )
                continue

            try:
                insight = await agent.run(query, context)
            except Exception as exc:
                logger.error("[Manager] Agent '%s' failed: %s", name, exc)
                insight = AgentInsight(
                    agent_name=getattr(agent, "agent_name", agent.__class__.__name__),
                    findings=["Agent execution failed"],
                    risks=[f"{agent.__class__.__name__} unavailable during analysis"],
                    recommendation="Proceed with degraded confidence and gather more evidence",
                    confidence=0.2,
                    evidence_used=[{"source": "error", "detail": str(exc)}],
                )
            agent_insights.append(insight)
            ev_n = len(insight.evidence_used or [])
            logger.info(
                "[Manager] agent_finished: %s confidence=%.3f evidence_items=%d findings=%d",
                name,
                float(insight.confidence),
                ev_n,
                len(insight.findings or []),
            )

        logger.info("[Manager] Synthesizing final decision...")
        conservative_view = await self._generate_conservative_view(agent_insights, query)
        aggressive_view = await self._generate_aggressive_view(agent_insights, query)
        final_decision = await self._synthesize_decision(
            agent_insights,
            conservative_view,
            aggressive_view,
            persona="conservative",
            query=query,
        )

        if len(agent_insights) > 1:
            final_decision["tldr"] = self._build_tldr(agent_insights, final_decision)

        return {
            "routing": routing,
            "agent_insights": [insight.model_dump() for insight in agent_insights],
            "conservative_view": conservative_view,
            "aggressive_view": aggressive_view,
            "final_decision": final_decision,
        }

    async def orchestrate(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy full-orchestration path."""
        logger.info(
            "[Manager] orchestrate_legacy context=%s",
            agent_logging.context_for_log(context),
        )
        agent_insights = []
        for agent in self.agents:
            an = getattr(agent, "agent_name", agent.__class__.__name__)
            logger.info("[Manager] legacy_run agent=%s", an)
            try:
                insight = await agent.run(query, context)
            except Exception as exc:
                logger.exception("[Manager] legacy agent %s failed: %s", an, exc)
                insight = AgentInsight(
                    agent_name=getattr(agent, "agent_name", agent.__class__.__name__),
                    findings=["Agent execution failed"],
                    risks=[f"{agent.__class__.__name__} unavailable during analysis"],
                    recommendation="Proceed with degraded confidence and gather more evidence",
                    confidence=0.2,
                    evidence_used=[{"source": "error", "detail": str(exc)}],
                )
            agent_insights.append(insight)
            logger.info(
                "[Manager] legacy_run_done agent=%s confidence=%.3f",
                an,
                float(insight.confidence),
            )

        conservative_view = await self._generate_conservative_view(agent_insights, query)
        aggressive_view = await self._generate_aggressive_view(agent_insights, query)

        final_decision = await self._synthesize_decision(
            agent_insights,
            conservative_view,
            aggressive_view,
            persona="conservative",
            query=query,
        )

        return {
            "agent_insights": [insight.model_dump() for insight in agent_insights],
            "conservative_view": conservative_view,
            "aggressive_view": aggressive_view,
            "final_decision": final_decision,
        }

    def _build_tldr(self, insights: List[AgentInsight], final_decision: Dict[str, Any]) -> str:
        risk = final_decision.get("risk_level", "Medium")
        confidence = final_decision.get("confidence_score", 0)
        departments = ", ".join(i.agent_name for i in insights)
        return (
            f"Departments consulted: {departments}. "
            f"Recommendation: {final_decision.get('recommendation', 'No recommendation')}. "
            f"Risk: {risk}. Confidence: {confidence}%."
        )

    async def _generate_conservative_view(self, insights: List[AgentInsight], query: str) -> str:
        """Generate a conservative strategic perspective using LLM — no hardcoded keywords."""
        all_risks = []
        all_findings = []
        for insight in insights:
            all_risks.extend(insight.risks)
            all_findings.extend(insight.findings)

        if self.router_client is None:
            # Graceful static fallback when LLM is unavailable
            risk_summary = "; ".join(all_risks[:3]) if all_risks else "No specific risks identified."
            return (
                f"Conservative perspective: Key risks identified — {risk_summary}. "
                "Recommend controlled steps, documentation, and measurable checkpoints before proceeding."
            )

        system_prompt = (
            "You are a conservative business strategist. Give a concise, risk-aware perspective in 2-3 sentences."
        )
        user_prompt = f"""
Business query: {query}

Agent findings: {all_findings[:6]}
Agent risks: {all_risks[:6]}

Write a conservative perspective on this decision — focus on risk mitigation, caution, and protective measures.
Output plain text only (no JSON, no markdown).
""".strip()

        try:
            resp = await self.router_client.acomplete_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=200,
            )
            return f"Conservative perspective: {(resp.text or '').strip()}"
        except Exception as exc:
            logger.warning("Conservative view LLM call failed: %s", exc)
            risk_summary = "; ".join(all_risks[:3]) if all_risks else "No specific risks identified."
            return (
                f"Conservative perspective: Key risks — {risk_summary}. "
                "Recommend controlled steps, documentation, and measurable checkpoints."
            )

    async def _generate_aggressive_view(self, insights: List[AgentInsight], query: str) -> str:
        """Generate an aggressive strategic perspective using LLM — no hardcoded keywords."""
        all_findings = []
        for insight in insights:
            all_findings.extend(insight.findings)

        if self.router_client is None:
            finding_summary = "; ".join(all_findings[:3]) if all_findings else "No specific findings."
            return (
                f"Aggressive perspective: Key findings — {finding_summary}. "
                "Recommend decisive execution with risk controls in parallel."
            )

        system_prompt = (
            "You are an aggressive growth-oriented business strategist. "
            "Give a concise, opportunity-focused perspective in 2-3 sentences."
        )
        user_prompt = f"""
Business query: {query}

Agent findings: {all_findings[:6]}

Write an aggressive perspective on this decision — focus on opportunity, speed, and competitive advantage.
Output plain text only (no JSON, no markdown).
""".strip()

        try:
            resp = await self.router_client.acomplete_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4,
                max_tokens=200,
            )
            return f"Aggressive perspective: {(resp.text or '').strip()}"
        except Exception as exc:
            logger.warning("Aggressive view LLM call failed: %s", exc)
            finding_summary = "; ".join(all_findings[:3]) if all_findings else "No specific findings."
            return (
                f"Aggressive perspective: Key findings — {finding_summary}. "
                "Recommend decisive execution with risk controls in parallel."
            )

    async def _synthesize_decision(
        self,
        insights: List[AgentInsight],
        conservative_view: str,
        aggressive_view: str,
        persona: str = "balanced",
        query: str = "",
    ) -> Dict[str, Any]:
        """Fully LLM-driven decision synthesis — no hardcoded domain keywords."""

        avg_confidence = sum(insight.confidence for insight in insights) / len(insights) if insights else 0.0

        # Build a compact agent summary for the LLM
        agent_summary_lines = []
        for insight in insights:
            agent_summary_lines.append(
                f"[{insight.agent_name}] Findings: {insight.findings[:2]} | "
                f"Risks: {insight.risks[:2]} | Rec: {insight.recommendation}"
            )
        agent_summary = "\n".join(agent_summary_lines) if agent_summary_lines else "No agent insights available."

        # --- LLM synthesis ---
        if self.router_client is not None:
            system_prompt = (
                "You are a senior business manager synthesizing multi-agent analysis. "
                "Return strict JSON only."
            )
            user_prompt = f"""
Business query: {query}

Agent analyses:
{agent_summary}

Conservative view: {conservative_view}
Aggressive view: {aggressive_view}
Manager persona: {persona}

Return a JSON object:
{{
  "recommendation": "clear, actionable final recommendation",
  "risk_level": "Low | Medium | High",
  "rationale": "2-4 sentence explanation referencing the agent findings",
  "confidence": 0.0
}}
""".strip()
            try:
                parsed, _ = await self.router_client.acomplete_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.3,
                    max_tokens=600,
                )
                recommendation = parsed.get("recommendation", "Proceed with caution — consult department leads.")
                risk_level = parsed.get("risk_level", "Medium")
                if risk_level not in ("Low", "Medium", "High"):
                    risk_level = "Medium"
                rationale = parsed.get("rationale", agent_summary)
                llm_confidence = float(parsed.get("confidence", avg_confidence))
                llm_confidence = max(0.0, min(llm_confidence, 1.0))

                full_rationale = (
                    f"Multi-agent analysis:\n\n{agent_summary}\n\n"
                    f"**Manager Decision ({persona.title()}):** {rationale}\n\n"
                    f"{conservative_view}\n\n{aggressive_view}"
                )

                return {
                    "recommendation": recommendation,
                    "risk_level": risk_level,
                    "confidence_score": round(llm_confidence * 100, 2),
                    "rationale": full_rationale,
                    "manager_persona": persona,
                }
            except Exception as exc:
                logger.warning("Decision synthesis LLM call failed: %s", exc)

        # --- Structural fallback (no domain keyword checks) ---
        # Derive risk level from agent confidence scores alone
        if avg_confidence < 0.4:
            risk_level = "High"
        elif avg_confidence < 0.65:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        rationale = f"Multi-agent analysis:\n\n{agent_summary}\n\n"
        if persona == "conservative":
            rationale += f"\n**Manager Decision (Conservative):** {conservative_view}"
        elif persona == "aggressive":
            rationale += f"\n**Manager Decision (Aggressive):** {aggressive_view}"
        else:
            rationale += "\n**Manager Decision (Balanced):** Weighing both perspectives."

        # Surface the most common recommendation from the sub-agents
        recs = [i.recommendation for i in insights if i.recommendation]
        recommendation = recs[0] if recs else "Proceed with phased approach — validate before full commitment."

        return {
            "recommendation": recommendation,
            "risk_level": risk_level,
            "confidence_score": round(avg_confidence * 100, 2),
            "rationale": rationale,
            "manager_persona": persona,
        }
