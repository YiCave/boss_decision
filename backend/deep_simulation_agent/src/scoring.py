from __future__ import annotations

from typing import Any

from .schema import ActionIntent
from .schema import KPIState
from .schema import PersonaScoreBreakdown
from .schema import SocialLink
from .schema import TickScoreBreakdown


def _resource_efficiency_points(intent: ActionIntent | None) -> float:
    if intent is None:
        return 0.0
    if intent.action_type == "spend_shift":
        budget_pct = float(intent.args.get("budget_pct", 0.0))
        return max(-0.6, -0.01 * max(0.0, budget_pct))
    if intent.action_type == "procurement":
        return 0.18
    if intent.action_type == "wait":
        return -0.05
    return 0.0


def _timing_points(intent: ActionIntent | None, tick: int, max_ticks: int) -> float:
    if intent is None or intent.action_type == "wait":
        return 0.0
    if max_ticks <= 0:
        return 0.0
    urgency = 1.0 - ((tick - 1) / max(1.0, float(max_ticks)))
    return round(0.14 * max(0.0, urgency), 3)


def _social_points(links: list[SocialLink], persona_id: str, tick: int) -> float:
    current_tick_links = [
        link for link in links if link.source_persona_id == persona_id and link.updated_tick == tick
    ]
    if not current_tick_links:
        return 0.0
    trust_sum = sum(link.trust for link in current_tick_links)
    return max(-0.45, min(0.45, round(0.08 * trust_sum, 3)))


def score_tick(
    *,
    tick: int,
    max_ticks: int,
    active_ids: set[str],
    persona_names: dict[str, str],
    current_scores: dict[str, float],
    rules: dict[str, float],
    rolls: dict[str, int],
    resolved: list[ActionIntent],
    kpi_before: KPIState,
    kpi_after: KPIState,
    crisis: dict[str, Any] | None,
    social_links: list[SocialLink],
) -> tuple[dict[str, float], TickScoreBreakdown]:
    next_scores = dict(current_scores)
    intent_by_persona = {intent.persona_id: intent for intent in resolved}
    kpi_shift = (
        (kpi_after.revenue - kpi_before.revenue)
        + (kpi_after.margin - kpi_before.margin)
        + (kpi_after.sentiment - kpi_before.sentiment)
        - (kpi_after.churn_risk - kpi_before.churn_risk)
    )
    per_persona_kpi = kpi_shift / max(1, len(active_ids))
    matched_actions = set(crisis.get("matched_actions", [])) if isinstance(crisis, dict) else set()
    rows: list[PersonaScoreBreakdown] = []

    for persona_id in active_ids:
        total = next_scores.get(persona_id, 0.0)
        intent = intent_by_persona.get(persona_id)
        base_points = rules["daily_base_points"]
        movement_points = rules["move_points_per_step"] * float(rolls.get(persona_id, 0))
        intent_quality_points = 0.0
        if intent is not None:
            intent_quality_points = rules["intent_points_multiplier"] * max(0.1, float(intent.confidence))
        kpi_contribution_points = rules["kpi_points_multiplier"] * per_persona_kpi
        crisis_response_points = 0.0
        if intent is not None and intent.action_type in matched_actions:
            crisis_response_points = 0.7
        timing_points = _timing_points(intent, tick, max_ticks)
        resource_efficiency_points = _resource_efficiency_points(intent)
        social_influence_points = _social_points(social_links, persona_id, tick)

        total_delta = (
            base_points
            + movement_points
            + intent_quality_points
            + kpi_contribution_points
            + crisis_response_points
            + timing_points
            + resource_efficiency_points
            + social_influence_points
        )
        total = max(0.0, total + total_delta)
        rounded_total = round(total, 2)
        next_scores[persona_id] = rounded_total

        rows.append(
            PersonaScoreBreakdown(
                persona_id=persona_id,
                persona_name=persona_names.get(persona_id, persona_id),
                base_points=round(base_points, 3),
                movement_points=round(movement_points, 3),
                intent_quality_points=round(intent_quality_points, 3),
                kpi_contribution_points=round(kpi_contribution_points, 3),
                crisis_response_points=round(crisis_response_points, 3),
                timing_points=round(timing_points, 3),
                resource_efficiency_points=round(resource_efficiency_points, 3),
                social_influence_points=round(social_influence_points, 3),
                total_delta=round(total_delta, 3),
                total_score=rounded_total,
            )
        )
    rows.sort(key=lambda item: item.total_delta, reverse=True)
    return next_scores, TickScoreBreakdown(
        tick=tick,
        kpi_shift=round(kpi_shift, 3),
        personas=rows,
    )
