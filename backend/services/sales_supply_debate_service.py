"""
Sales vs Supply Chain debate simulator service.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from agents.supply_chain_agent import SupplyChainAgent
from config import get_settings
from db import DatabaseService
from services.sales_campaign_service import SalesCampaignService


class SalesSupplyDebateService:
    """
    Simulates a round-based debate:
    1) Sales proposes an execution plan using Tavily market signals.
    2) Supply chain approves/rejects based on inventory constraints.
    3) Each turn feeds into the next turn for both agents.
    """

    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.low_inventory_threshold = SupplyChainAgent.LOW_INVENTORY_THRESHOLD
        settings = get_settings()
        self._apply_zhipu_env_aliases()
        default_debate_model = self._default_zhipu_model()
        self._market_region = os.getenv("SALES_DEBATE_REGION", "Malaysia")
        self._sales_campaign_service = (
            SalesCampaignService(settings.tavily_api_key) if settings.tavily_api_key else None
        )
        self.sales_model = self._init_model(
            os.getenv("SALES_DEBATE_MODEL", default_debate_model)
        )
        self.supply_model = self._init_model(
            os.getenv("SUPPLY_DEBATE_MODEL", default_debate_model)
        )
        self.judge_model = self._init_model(
            os.getenv("JUDGE_DEBATE_MODEL", default_debate_model)
        )

    async def run(self, max_rounds: int = 4, item_name: str | None = None) -> dict[str, Any]:
        fixed_rounds = 5
        records = await self.db.get_supply_records_for_debate(item_name=item_name, limit=1)
        if not records:
            return {
                "status": "no_data",
                "message": "No supply_record rows matched the provided filter.",
                "retrieved_item_names": [],
                "simulations": [],
            }

        simulations = []
        for record in records:
            market_context = await self._get_market_context_for_item(str(record.get("item_name") or ""))
            session = await self._simulate_for_record(
                record=record,
                max_rounds=fixed_rounds,
                market_context=market_context,
            )
            simulations.append(session)

        approved_count = sum(1 for session in simulations if session["final_result"]["status"] == "approved")
        rejected_count = len(simulations) - approved_count

        return {
            "status": "ok",
            "max_rounds": fixed_rounds,
            "max_items": 1,
            "retrieved_item_names": [row.get("item_name") for row in records if row.get("item_name")],
            "simulations": simulations,
            "summary": {
                "total_items": len(simulations),
                "approved": approved_count,
                "rejected": rejected_count,
            },
        }

    async def _simulate_for_record(
        self,
        record: dict[str, Any],
        max_rounds: int,
        market_context: dict[str, Any],
    ) -> dict[str, Any]:
        item_name = str(record.get("item_name") or "Unknown item")
        rounds: list[dict[str, Any]] = []
        last_supply_reply: str | None = None
        context = self._inventory_context(record)
        debate_history: list[dict[str, Any]] = []

        for round_no in range(1, max_rounds + 1):
            sales_suggestion = self._build_sales_suggestion_with_llm(
                item_name=item_name,
                inventory_context=context,
                market_context=market_context,
                round_no=round_no,
                previous_supply_reply=last_supply_reply,
                debate_history=debate_history,
            )
            supply_review = self._build_supply_review_with_llm(
                record=record,
                suggestion=sales_suggestion,
                round_no=round_no,
                debate_history=debate_history,
            )

            round_output = {
                "round": round_no,
                "sales_agent": {
                    "agent_id": "AI-1",
                    "role": "Sales Agent",
                    "suggestion": sales_suggestion,
                    "market_signal": market_context.get("signal_line", ""),
                },
                "supply_chain_agent": {
                    "agent_id": "AI-2",
                    "role": "Supply Chain Agent",
                    "validity": "valid" if supply_review["is_valid"] else "invalid",
                    "strict_checks": supply_review["risk_signals"],
                    "response": supply_review["response"],
                },
            }
            rounds.append(round_output)
            debate_history.append(
                {
                    "round": round_no,
                    "sales_suggestion": sales_suggestion,
                    "supply_validity": supply_review["is_valid"],
                    "supply_response": supply_review["response"],
                }
            )
            last_supply_reply = supply_review["response"]

        judge_result = self._judge_debate_with_llm(
            item_name=item_name,
            inventory_context=context,
            market_context=market_context,
            rounds=rounds,
        )

        return {
            "supply_id": record.get("supply_id"),
            "item_name": item_name,
            "inventory_context": context,
            "market_context": market_context,
            "rounds": rounds,
            "judge_result": judge_result,
            "final_result": self._build_final_result(
                item_name=item_name,
                rounds=rounds,
                judge_result=judge_result,
                max_rounds=max_rounds,
            ),
        }

    def _build_supply_review_with_llm(
        self,
        record: dict[str, Any],
        suggestion: str,
        round_no: int,
        debate_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        inventory_level = record.get("inventory_level")
        demand_forecast = record.get("demand_forecast")
        reorder_point = record.get("reorder_point")
        shortage_flag = record.get("shortage_flag")

        shortage_active = False
        try:
            shortage_active = int(shortage_flag or 0) == 1
        except (TypeError, ValueError):
            shortage_active = False

        risk_signals, risk_score, critical_risk = self._build_supply_risk_profile(
            inventory_level=inventory_level,
            demand_forecast=demand_forecast,
            reorder_point=reorder_point,
            shortage_active=shortage_active,
        )
        sales_case = self._assess_sales_business_case(suggestion)
        llm_assessment = self._supply_chain_llm_assessment(
            record=record,
            suggestion=suggestion,
            round_no=round_no,
            risk_signals=risk_signals,
            debate_history=debate_history,
            sales_case=sales_case,
        )
        final_validity = self._resolve_supply_validity(
            llm_validity=str(llm_assessment.get("validity", "")).lower(),
            risk_score=risk_score,
            critical_risk=critical_risk,
            sales_case=sales_case,
            llm_roi_score=self._coerce_score(llm_assessment.get("roi_score"), fallback=sales_case["roi_score"]),
            llm_reasonability_score=self._coerce_score(
                llm_assessment.get("reasonability_score"), fallback=sales_case["reasonability_score"]
            ),
            llm_risk_control_score=self._coerce_score(
                llm_assessment.get("risk_control_score"), fallback=sales_case["risk_control_score"]
            ),
        )
        response = self._merge_supply_review(
            is_valid=final_validity,
            base_response=str(llm_assessment.get("response", "")).strip(),
            item_name=str(record.get("item_name") or "Unknown item"),
            suggestion=suggestion,
            risk_signals=risk_signals,
            risk_score=risk_score,
            sales_case=sales_case,
        )
        return {
            "is_valid": final_validity,
            "response": response,
            "risk_score": risk_score,
            "risk_signals": risk_signals,
        }

    def _build_supply_risk_profile(
        self,
        inventory_level: Any,
        demand_forecast: Any,
        reorder_point: Any,
        shortage_active: bool,
    ) -> tuple[list[str], int, bool]:
        risk_signals: list[str] = []
        risk_score = 0
        critical_risk = False

        if inventory_level is None:
            risk_signals.append("Inventory level is missing, so fulfillment feasibility cannot be validated.")
            risk_score += 3
            if shortage_active:
                critical_risk = True

        if shortage_active:
            risk_signals.append("Shortage flag is active and indicates unstable supply.")
            risk_score += 2

        if (
            isinstance(reorder_point, (int, float))
            and isinstance(inventory_level, (int, float))
            and inventory_level <= reorder_point
        ):
            risk_signals.append(f"Inventory ({inventory_level}) is at or below reorder point ({reorder_point}).")
            risk_score += 2

        if isinstance(inventory_level, (int, float)) and inventory_level < self.low_inventory_threshold:
            risk_signals.append(
                f"Inventory ({inventory_level}) is below minimum safety threshold ({self.low_inventory_threshold})."
            )
            risk_score += 2

        if (
            isinstance(demand_forecast, (int, float))
            and isinstance(inventory_level, (int, float))
            and inventory_level < int(demand_forecast * 0.8)
        ):
            risk_signals.append(
                f"Inventory ({inventory_level}) is below 80% of demand forecast ({demand_forecast})."
            )
            risk_score += 2

        if (
            shortage_active
            and isinstance(inventory_level, (int, float))
            and isinstance(demand_forecast, (int, float))
            and demand_forecast > 0
            and inventory_level < demand_forecast * 0.5
        ):
            critical_risk = True

        return risk_signals, risk_score, critical_risk

    @staticmethod
    def _assess_sales_business_case(suggestion: str) -> dict[str, int]:
        lowered = suggestion.lower()
        mitigation_terms = [
            "phased",
            "pilot",
            "capped",
            "throttle",
            "waitlist",
            "preorder",
            "pre-order",
            "limited release",
            "inventory",
            "sla",
            "checkpoint",
        ]
        roi_terms = [
            "roi",
            "revenue",
            "margin",
            "profit",
            "payback",
            "conversion",
            "roas",
            "growth",
            "uplift",
        ]
        reasoning_terms = ["because", "due to", "based on", "therefore", "market signal", "source"]

        mitigation_hits = sum(1 for term in mitigation_terms if term in lowered)
        roi_hits = sum(1 for term in roi_terms if term in lowered)
        reasoning_hits = sum(1 for term in reasoning_terms if term in lowered)
        percent_mentions = len(re.findall(r"\b\d+(?:\.\d+)?\s*%", lowered))
        currency_mentions = len(re.findall(r"\b(?:rm|usd|sgd|\$)\s*\d", lowered))

        roi_score = 4 + min(3, percent_mentions) + min(2, roi_hits) + min(1, currency_mentions)
        reasonability_score = 4 + min(3, mitigation_hits) + min(2, reasoning_hits)
        risk_control_score = 3 + min(5, mitigation_hits)

        if len(suggestion) >= 120:
            reasonability_score += 1
        if "kpi" in lowered or "target" in lowered:
            risk_control_score += 1

        return {
            "roi_score": SalesSupplyDebateService._coerce_score(roi_score, fallback=5),
            "reasonability_score": SalesSupplyDebateService._coerce_score(reasonability_score, fallback=5),
            "risk_control_score": SalesSupplyDebateService._coerce_score(risk_control_score, fallback=5),
        }

    def _build_sales_suggestion_with_llm(
        self,
        item_name: str,
        inventory_context: dict[str, Any],
        market_context: dict[str, Any],
        round_no: int,
        previous_supply_reply: str | None,
        debate_history: list[dict[str, Any]],
    ) -> str:
        if self.sales_model is None:
            return self._fallback_sales_suggestion(
                item_name=item_name,
                round_no=round_no,
                previous_supply_reply=previous_supply_reply,
                market_context=market_context,
            )

        prompt = (
            "You are AI-1 Sales Agent in a live executive debate.\n"
            "Core rule: Always stand on execution. You must advocate that the user should perform your suggestion.\n"
            "You are not allowed to recommend canceling, pausing, or abandoning execution.\n"
            "If supply concerns exist, propose constrained execution, phased execution, or alternate execution path.\n"
            "You must incorporate current Tavily-derived market signal in every response.\n"
            "Constraints:\n"
            "- 80 to 130 words.\n"
            "- Include one concrete tactical plan and one KPI target.\n"
            "- Mention one web signal source/title from provided market context.\n"
            "- Must respond to latest supply-chain argument so debate stays on track.\n"
            f"- Item name: {item_name}\n"
            f"- Round: {round_no}\n"
            f"- Inventory context: {json.dumps(inventory_context, default=str)}\n"
            f"- Tavily market context: {json.dumps(market_context, default=str)}\n"
            f"- Latest supply-chain reply: {previous_supply_reply or 'None'}\n"
            f"- Debate history: {json.dumps(debate_history[-4:], default=str)}\n"
            'Respond in strict JSON: {"suggestion":"...", "web_signal":"..."}'
        )
        try:
            response = self.sales_model.invoke(prompt)
            text = self._extract_text(response)
            parsed = self._parse_json_object(text)
            suggestion = str(parsed.get("suggestion", "")).strip()
            web_signal = str(parsed.get("web_signal", "")).strip()
            if not suggestion:
                raise ValueError("Missing sales suggestion")
            if self._looks_like_non_execution(suggestion):
                raise ValueError("Sales response violated always-execute rule")
            signal_line = web_signal or str(market_context.get("signal_line") or "").strip()
            if signal_line:
                return f"{suggestion} Market signal: {signal_line}"
            return suggestion
        except Exception:
            return self._fallback_sales_suggestion(
                item_name=item_name,
                round_no=round_no,
                previous_supply_reply=previous_supply_reply,
                market_context=market_context,
            )

    def _supply_chain_llm_assessment(
        self,
        record: dict[str, Any],
        suggestion: str,
        round_no: int,
        risk_signals: list[str],
        debate_history: list[dict[str, Any]],
        sales_case: dict[str, int],
    ) -> dict[str, Any]:
        item_name = str(record.get("item_name") or "Unknown item")
        if self.supply_model is None:
            return self._fallback_supply_assessment(item_name, suggestion, risk_signals, sales_case)

        prompt = (
            "You are AI-2 Supply Chain Agent in a realistic boardroom debate.\n"
            "Evaluate the Sales proposal with strict validation discipline and give an executive-grade response.\n"
            "Requirements:\n"
            "- Your role is to challenge weak assumptions and verify if the proposal is valid under current inventory conditions.\n"
            "- Do not output approve/reject. Output only validity: valid or invalid.\n"
            "- Be strict; when uncertain, lean invalid and explain what must be fixed.\n"
            "- Tone should be precise, high-credibility, and persuasive.\n"
            "- 90-140 words.\n"
            "- Must explicitly reference the latest sales suggestion so debate stays aligned.\n"
            f"- Round: {round_no}\n"
            f"- Item: {item_name}\n"
            f"- Proposal: {suggestion}\n"
            f"- Supply record: {json.dumps(record, default=str)}\n"
            f"- Supply risk signals: {json.dumps(risk_signals)}\n"
            f"- Heuristic sales-case scores (1-10): {json.dumps(sales_case)}\n"
            f"- Debate history: {json.dumps(debate_history[-4:], default=str)}\n"
            "Respond in strict JSON with numeric scores from 1 to 10: "
            '{"validity":"valid|invalid","response":"...","roi_score":7,"reasonability_score":7,"risk_control_score":7}'
        )
        try:
            response = self.supply_model.invoke(prompt)
            text = self._extract_text(response)
            parsed = self._parse_json_object(text)
            validity = str(parsed.get("validity", "")).strip().lower()
            response_text = str(parsed.get("response", "")).strip()
            if validity not in {"valid", "invalid"} or not response_text:
                raise ValueError("Invalid model response")

            return {
                "validity": validity,
                "response": response_text,
                "roi_score": self._coerce_score(parsed.get("roi_score"), fallback=sales_case["roi_score"]),
                "reasonability_score": self._coerce_score(
                    parsed.get("reasonability_score"),
                    fallback=sales_case["reasonability_score"],
                ),
                "risk_control_score": self._coerce_score(
                    parsed.get("risk_control_score"),
                    fallback=sales_case["risk_control_score"],
                ),
            }
        except Exception:
            return self._fallback_supply_assessment(item_name, suggestion, risk_signals, sales_case)

    @staticmethod
    def _resolve_supply_validity(
        llm_validity: str,
        risk_score: int,
        critical_risk: bool,
        sales_case: dict[str, int],
        llm_roi_score: int,
        llm_reasonability_score: int,
        llm_risk_control_score: int,
    ) -> str:
        roi_score = max(sales_case["roi_score"], llm_roi_score)
        reasonability_score = max(sales_case["reasonability_score"], llm_reasonability_score)
        risk_control_score = max(sales_case["risk_control_score"], llm_risk_control_score)

        strong_business_case = roi_score >= 7 and reasonability_score >= 6
        strong_controls = risk_control_score >= 6

        if critical_risk and not (strong_business_case and strong_controls and roi_score >= 9):
            return False
        if risk_score >= 7 and not (strong_business_case and strong_controls):
            return False
        if risk_score >= 6 and not (strong_business_case and strong_controls and roi_score >= 8):
            return False

        if llm_validity == "valid":
            return reasonability_score >= 6 and risk_control_score >= 6 and risk_score <= 5

        if llm_validity == "invalid":
            return risk_score <= 3 and strong_business_case and strong_controls and roi_score >= 8

        return risk_score <= 4 and strong_controls and reasonability_score >= 7 and roi_score >= 7

    def _judge_debate_with_llm(
        self,
        item_name: str,
        inventory_context: dict[str, Any],
        market_context: dict[str, Any],
        rounds: list[dict[str, Any]],
    ) -> dict[str, Any]:
        latest_supply_validity = ""
        if rounds:
            latest_supply_validity = str(rounds[-1].get("supply_chain_agent", {}).get("validity", ""))

        if self.judge_model is None:
            return self._fallback_judge_result(item_name=item_name, rounds=rounds)

        prompt = (
            "You are AI-3 Debate Judge for a boardroom simulation.\n"
            "You must read all debate turns between Sales Agent and Supply Chain Agent, then choose whose recommendation to follow.\n"
            "Decision policy:\n"
            "- Choose `sales` when execution plan is persuasive and operationally manageable.\n"
            "- Choose `supply` when inventory/operational risks outweigh sales upside.\n"
            "- You must not invent facts outside transcript.\n"
            "- Keep rationale concrete and concise.\n"
            f"- Item: {item_name}\n"
            f"- Inventory context: {json.dumps(inventory_context, default=str)}\n"
            f"- Market context: {json.dumps(market_context, default=str)}\n"
            f"- Full debate rounds: {json.dumps(rounds, default=str)}\n"
            f"- Latest supply validity check: {latest_supply_validity or 'unknown'}\n"
            'Respond in strict JSON: {"winner":"sales|supply","rationale":"...","confidence":0.0,"verdict":"execute|hold"}'
        )
        try:
            response = self.judge_model.invoke(prompt)
            parsed = self._parse_json_object(self._extract_text(response))
            winner = str(parsed.get("winner", "")).strip().lower()
            verdict = str(parsed.get("verdict", "")).strip().lower()
            rationale = str(parsed.get("rationale", "")).strip()
            confidence = self._coerce_confidence(parsed.get("confidence"), fallback=0.7)
            if winner not in {"sales", "supply"} or verdict not in {"execute", "hold"} or not rationale:
                raise ValueError("Invalid judge output")
            return {
                "winner": winner,
                "verdict": verdict,
                "rationale": rationale,
                "confidence": confidence,
            }
        except Exception:
            return self._fallback_judge_result(item_name=item_name, rounds=rounds)

    def _fallback_judge_result(self, item_name: str, rounds: list[dict[str, Any]]) -> dict[str, Any]:
        if not rounds:
            return {
                "winner": "supply",
                "verdict": "hold",
                "rationale": f"No complete debate evidence for {item_name}; choose supply-side caution by default.",
                "confidence": 0.55,
            }
        valid_count = sum(
            1
            for row in rounds
            if str(row.get("supply_chain_agent", {}).get("validity", "invalid")).lower() == "valid"
        )
        if valid_count >= 3:
            return {
                "winner": "sales",
                "verdict": "execute",
                "rationale": "Majority of supply-chain strict checks considered the proposal valid, so execute with controls.",
                "confidence": 0.7,
            }
        return {
            "winner": "supply",
            "verdict": "hold",
            "rationale": "Supply-chain strict checks repeatedly found invalid conditions, so hold execution.",
            "confidence": 0.72,
        }

    def _build_final_result(
        self,
        item_name: str,
        rounds: list[dict[str, Any]],
        judge_result: dict[str, Any],
        max_rounds: int,
    ) -> dict[str, Any]:
        winner = str(judge_result.get("winner", "supply")).lower()
        verdict = str(judge_result.get("verdict", "hold")).lower()
        rationale = str(judge_result.get("rationale", "")).strip()

        if winner == "sales" and verdict == "execute":
            return {
                "status": "approved",
                "winner": "sales_agent",
                "conclusion": (
                    f"Judge selected Sales Agent direction for {item_name}. Execute the sales suggestion with operational guardrails. "
                    f"Judge rationale: {rationale}"
                ),
            }

        if rounds and len(rounds) >= max_rounds:
            base = f"Judge selected Supply Chain direction for {item_name} after {max_rounds} debate rounds."
        else:
            base = f"Judge selected Supply Chain direction for {item_name}."

        return {
            "status": "rejected",
            "winner": "supply_chain_agent",
            "conclusion": f"{base} Hold execution and follow supply constraints. Judge rationale: {rationale}",
        }

    def _merge_supply_review(
        self,
        is_valid: bool,
        base_response: str,
        item_name: str,
        suggestion: str,
        risk_signals: list[str],
        risk_score: int,
        sales_case: dict[str, int],
    ) -> str:
        if base_response:
            response = base_response
        else:
            fallback = self._fallback_supply_assessment(item_name, suggestion, risk_signals, sales_case)
            response = str(fallback.get("response", "")).strip()

        if is_valid and risk_signals:
            top_risks = "; ".join(risk_signals[:2])
            return (
                f"{response} Strict controls required: enforce phased volume caps, daily fill-rate monitoring, "
                f"and immediate throttle if risk signals worsen ({top_risks})."
            )

        if (not is_valid) and risk_signals and "risk" not in response.lower():
            top_risks = "; ".join(risk_signals[:2])
            return (
                f"{response} Primary risk signals: {top_risks}. "
                f"Current weighted supply risk score: {risk_score}/10."
            )
        return response

    @staticmethod
    def _fallback_supply_assessment(
        item_name: str,
        suggestion: str,
        risk_signals: list[str],
        sales_case: dict[str, int],
    ) -> dict[str, Any]:
        roi_score = sales_case["roi_score"]
        reasonability_score = sales_case["reasonability_score"]
        risk_control_score = sales_case["risk_control_score"]

        if risk_signals and not (roi_score >= 7 and reasonability_score >= 6 and risk_control_score >= 6):
            blockers = " ".join(f"[{idx + 1}] {risk}" for idx, risk in enumerate(risk_signals[:3]))
            return {
                "validity": "invalid",
                "response": (
                    f"Invalid for {item_name}. The proposal '{suggestion}' does not yet provide enough ROI "
                    f"or risk controls to offset current supply exposure. Key supply risks: {blockers} "
                    "Strengthen mitigation steps and measurable return assumptions before execution."
                ),
                "roi_score": roi_score,
                "reasonability_score": reasonability_score,
                "risk_control_score": risk_control_score,
            }

        if risk_signals:
            return {
                "validity": "invalid",
                "response": (
                    f"Currently invalid for {item_name} under strict review. The proposal '{suggestion}' has potential, "
                    "but supply risk still requires stronger safeguards before it can be treated as valid."
                ),
                "roi_score": roi_score,
                "reasonability_score": reasonability_score,
                "risk_control_score": risk_control_score,
            }

        return {
            "validity": "valid",
            "response": (
                f"Valid for {item_name} under strict review. The proposal '{suggestion}' is aligned with current "
                "inventory conditions, provided guardrails remain enforced."
            ),
            "roi_score": roi_score,
            "reasonability_score": reasonability_score,
            "risk_control_score": risk_control_score,
        }

    @staticmethod
    def _coerce_score(value: Any, fallback: int = 5) -> int:
        try:
            score = int(float(value))
        except (TypeError, ValueError):
            score = fallback
        return max(1, min(10, score))

    @staticmethod
    def _coerce_confidence(value: Any, fallback: float = 0.7) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = fallback
        return max(0.0, min(1.0, score))

    def _fallback_sales_suggestion(
        self,
        item_name: str,
        round_no: int,
        previous_supply_reply: str | None,
        market_context: dict[str, Any],
    ) -> str:
        signal_line = str(market_context.get("signal_line") or "Recent market momentum supports targeted execution.")
        if round_no == 1:
            return (
                f"Execute a demand-growth campaign for {item_name} with phased channel rollout and weekly conversion checkpoints. "
                f"Target +12% week-over-week orders while controlling spend by cohort. Market signal: {signal_line}"
            )
        return (
            f"Proceed with a constrained execution plan for {item_name}: capped-volume release, waitlist routing, and reorder-trigger throttles. "
            f"Addressing supply feedback: {previous_supply_reply or 'operational risk controls required'}. "
            f"Target +8% qualified demand with fulfillment SLA above 95%. Market signal: {signal_line}"
        )

    async def _get_market_context_for_item(self, item_name: str) -> dict[str, Any]:
        if not item_name:
            return {"search_query": "", "signal_line": "", "signals": []}

        if self._sales_campaign_service is None:
            return {
                "search_query": "",
                "signal_line": "Tavily market feed unavailable (missing API key).",
                "signals": [],
            }

        try:
            result = await self._sales_campaign_service.suggest_campaigns(
                product=item_name,
                region=self._market_region,
            )
            signals = result.get("news_signals", []) if isinstance(result, dict) else []
            compact_signals: list[dict[str, str]] = []
            for signal in signals[:3]:
                if not isinstance(signal, dict):
                    continue
                compact_signals.append(
                    {
                        "title": str(signal.get("title") or ""),
                        "source": str(signal.get("source") or ""),
                        "summary": str(signal.get("summary") or ""),
                    }
                )
            signal_line = self._format_market_signal_line(compact_signals)
            return {
                "search_query": str(result.get("search_query") or ""),
                "signal_line": signal_line,
                "signals": compact_signals,
            }
        except Exception:
            return {
                "search_query": "",
                "signal_line": "Tavily query failed; proceed with conservative market assumption.",
                "signals": [],
            }

    @staticmethod
    def _format_market_signal_line(signals: list[dict[str, str]]) -> str:
        if not signals:
            return "No strong external signal returned from Tavily."
        first = signals[0]
        title = first.get("title") or "Market headline"
        source = first.get("source") or "web source"
        return f"{title} ({source})"

    @staticmethod
    def _looks_like_non_execution(text: str) -> bool:
        lowered = text.lower()
        blockers = [
            "do not execute",
            "do not proceed",
            "should not proceed",
            "cancel",
            "stop the campaign",
            "avoid execution",
            "defer entirely",
            "postpone entirely",
        ]
        return any(word in lowered for word in blockers)

    @staticmethod
    def _default_zhipu_model() -> str:
        zhipu_model = os.getenv("ZHIPU_MODEL", "ilmu-glm-5.1")
        return zhipu_model if ":" in zhipu_model else f"openai:{zhipu_model}"

    @staticmethod
    def _apply_zhipu_env_aliases() -> None:
        zhipu_key = os.getenv("ZHIPU_API_KEY")
        if zhipu_key and not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = zhipu_key
        zhipu_base_url = os.getenv("ZHIPU_BASE_URL")
        if zhipu_base_url and not os.getenv("OPENAI_BASE_URL"):
            os.environ["OPENAI_BASE_URL"] = zhipu_base_url

    @staticmethod
    def _init_model(model_name: str) -> Any | None:
        try:
            from langchain.chat_models import init_chat_model

            return init_chat_model(model=model_name)
        except Exception:
            return None

    @staticmethod
    def _extract_text(response: Any) -> str:
        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
                elif isinstance(part, str):
                    parts.append(part)
            return "\n".join(parts)
        return str(content)

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any]:
        stripped = text.strip()
        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            pass

        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _inventory_context(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "inventory_level": record.get("inventory_level"),
            "demand_forecast": record.get("demand_forecast"),
            "reorder_point": record.get("reorder_point"),
            "shortage_flag": record.get("shortage_flag"),
            "supplier_name": record.get("supplier_name"),
            "unit_cost": float(record["unit_cost"]) if record.get("unit_cost") is not None else None,
        }
