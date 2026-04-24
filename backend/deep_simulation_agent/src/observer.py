from __future__ import annotations

import html
import json
import re
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from .schema import DeepSimulationFinalResponse
from .schema import DeepSimulationState
from .schema import ObserverSummary
from .schema import PersonaObservationReport


class _TickObserverOutput(BaseModel):
    markdown: str = Field(min_length=24, max_length=2200)


class _PersonaObservationOutput(BaseModel):
    persona_id: str
    stance: str
    evidence: list[str] = Field(default_factory=list)
    suggested_next_action: str = ""


class _FinalObserverOutput(BaseModel):
    summary: str = Field(min_length=20, max_length=1200)
    key_turning_points: list[str] = Field(default_factory=list, max_length=8)
    recommendation: str = Field(min_length=20, max_length=1600)
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    persona_observations: list[_PersonaObservationOutput] = Field(default_factory=list, max_length=16)


def _json_from_text(value: str) -> dict[str, Any]:
    text = value.strip()
    if not text:
        return {}
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
    if not text.startswith("{"):
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _state_observer_payload(state: DeepSimulationState) -> dict[str, Any]:
    persona_index = {
        persona.id: {
            "id": persona.id,
            "name": persona.name,
            "role": persona.role,
            "objective": persona.objective,
        }
        for persona in state.personas
    }
    agents = []
    for agent in state.agents:
        agents.append(
            {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "status": agent.status,
                "confidence": agent.confidence,
                "score": state.agent_scores.get(agent.id, 0.0),
                "tool_calls": agent.tool_calls[-8:],
                "transcript_tail": agent.transcript[-1800:],
            }
        )
    return {
        "query": state.query,
        "scenario_id": state.scenario_id,
        "seed": state.seed,
        "tick": state.tick,
        "max_ticks": state.max_ticks,
        "kpi": state.global_kpis.model_dump(),
        "personas": list(persona_index.values()),
        "agents": agents,
        "timeline_recent": [item.model_dump(mode="json") for item in state.timeline[:20]],
        "tick_events_recent": [item.model_dump(mode="json") for item in state.tick_events[-60:]],
        "observer_summaries_recent": [item.model_dump(mode="json") for item in state.observer_summaries[-6:]],
    }


def _fallback_periodic_markdown(state: DeepSimulationState) -> str:
    top = state.timeline[0].message if state.timeline else "No major event logged yet."
    return (
        f"## Day {state.tick} Observer Pulse\n"
        f"- Revenue delta: `{state.global_kpis.revenue:.2f}`\n"
        f"- Margin delta: `{state.global_kpis.margin:.2f}`\n"
        f"- Brand trust delta: `{state.global_kpis.sentiment:.2f}`\n"
        f"- Churn risk delta: `{state.global_kpis.churn_risk:.2f}`\n"
        f"- Most recent event: {top}\n"
        "- Posture: keep staged rollout and force strict stop-loss thresholds."
    )


def _fallback_persona_observations(state: DeepSimulationState) -> list[PersonaObservationReport]:
    out: list[PersonaObservationReport] = []
    by_id = {agent.id: agent for agent in state.agents}
    for persona in state.personas:
        agent = by_id.get(persona.id)
        latest_tool = agent.tool_calls[-1] if agent and agent.tool_calls else "no tool call observed"
        evidence = [f"Latest action trace: {latest_tool}"]
        out.append(
            PersonaObservationReport(
                persona_id=persona.id,
                name=persona.name,
                role=persona.role,
                objective=persona.objective,
                stance="Cautious monitoring posture",
                evidence=evidence,
                suggested_next_action="Run one more targeted day-cycle before scaling market-wide.",
            )
        )
    return out


def _fallback_final(state: DeepSimulationState) -> DeepSimulationFinalResponse:
    ranking = sorted(state.agent_scores.items(), key=lambda item: item[1], reverse=True)
    leader = ranking[0][0] if ranking else "none"
    return DeepSimulationFinalResponse(
        summary=(
            f"Simulation ended at day {state.tick}/{state.max_ticks}. "
            f"Current KPI envelope: revenue {state.global_kpis.revenue:.2f}, margin {state.global_kpis.margin:.2f}, "
            f"sentiment {state.global_kpis.sentiment:.2f}, churn risk {state.global_kpis.churn_risk:.2f}."
        ),
        key_turning_points=[
            item.message for item in state.timeline[:4]
        ]
        or [
            "No major timeline turns were recorded.",
        ],
        recommendation=(
            "Proceed with controlled expansion only where churn risk remains below threshold and "
            "the highest-scoring strategist assumptions are validated by fresh demand data."
        ),
        confidence=0.62,
        periodic_summaries=state.observer_summaries,
        persona_observations=_fallback_persona_observations(state),
        html_slides="",
    )


def build_periodic_summary(state: DeepSimulationState, observer_model: Any | None) -> ObserverSummary:
    fallback_md = _fallback_periodic_markdown(state)
    if observer_model is None:
        return ObserverSummary(tick=state.tick, markdown=fallback_md)

    payload = _state_observer_payload(state)
    prompt = (
        "You are an observer agent reviewing a multi-persona business simulation.\n"
        "Return ONLY JSON using this schema: "
        f"{json.dumps(_TickObserverOutput.model_json_schema(), separators=(',', ':'))}\n"
        "The markdown must be concise, easy for business users, and explain what changed this day.\n"
        f"State JSON: {json.dumps(payload, ensure_ascii=True)}"
    )
    try:
        if hasattr(observer_model, "with_structured_output"):
            structured = observer_model.with_structured_output(_TickObserverOutput)
            result = structured.invoke(prompt)
            markdown = result.markdown.strip()
        else:
            raw = observer_model.invoke(prompt)
            text = str(getattr(raw, "content", raw)).strip()
            parsed = _json_from_text(text)
            markdown = str(parsed.get("markdown") or "").strip()
        return ObserverSummary(tick=state.tick, markdown=markdown or fallback_md)
    except Exception:
        return ObserverSummary(tick=state.tick, markdown=fallback_md)


def _slides_html(state: DeepSimulationState, report: DeepSimulationFinalResponse) -> str:
    summary_items = "".join(
        f"<li><strong>Day {item.tick}</strong><p>{html.escape(item.markdown)}</p></li>"
        for item in report.periodic_summaries[-5:]
    )
    top_timeline = "".join(
        f"<li><span>Day {item.tick}</span><p>{html.escape(item.message)}</p></li>"
        for item in state.timeline[:10]
    )
    persona_rows = "".join(
        (
            "<li>"
            f"<h3>{html.escape(item.name)} ({html.escape(item.role)})</h3>"
            f"<p><strong>Objective:</strong> {html.escape(item.objective)}</p>"
            f"<p><strong>Observed stance:</strong> {html.escape(item.stance)}</p>"
            f"<p><strong>Next action:</strong> {html.escape(item.suggested_next_action)}</p>"
            "</li>"
        )
        for item in report.persona_observations[:10]
    )
    turning_rows = "".join(f"<li>{html.escape(item)}</li>" for item in report.key_turning_points[:8])
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Deep Simulation Report</title>
  <style>
    body {{ margin:0; font-family: 'Sora', 'Segoe UI', sans-serif; background:#f5f6f2; color:#101010; }}
    .deck {{ display:grid; gap:16px; padding:18px; }}
    .slide {{ border:1px solid #ddd7ca; background:#fffdf8; border-radius:16px; padding:20px; }}
    h1,h2,h3 {{ margin:0 0 8px 0; letter-spacing:0.01em; }}
    .kpis {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }}
    .kpi {{ border:1px solid #e5dfd1; border-radius:12px; padding:10px; background:#fbf8ef; }}
    ul {{ margin:8px 0 0 18px; padding:0; }}
    li {{ margin:8px 0; }}
    p {{ margin:4px 0; line-height:1.4; }}
    .muted {{ color:#665f52; font-size:12px; }}
  </style>
</head>
<body>
  <main class="deck">
    <section class="slide">
      <p class="muted">Deep Simulation Observer</p>
      <h1>Scenario: {html.escape(state.scenario_id)}</h1>
      <p>{html.escape(state.query)}</p>
      <p class="muted">Seed {state.seed} | Tick = 1 day | Max ticks {state.max_ticks}</p>
    </section>
    <section class="slide">
      <h2>Outcome Snapshot</h2>
      <p>{html.escape(report.summary)}</p>
      <p><strong>Recommendation:</strong> {html.escape(report.recommendation)}</p>
      <p class="muted">Confidence: {round(report.confidence * 100)}%</p>
      <div class="kpis">
        <div class="kpi"><p class="muted">Revenue Delta</p><p>{state.global_kpis.revenue:.2f}</p></div>
        <div class="kpi"><p class="muted">Margin Delta</p><p>{state.global_kpis.margin:.2f}</p></div>
        <div class="kpi"><p class="muted">Sentiment</p><p>{state.global_kpis.sentiment:.2f}</p></div>
        <div class="kpi"><p class="muted">Churn Risk</p><p>{state.global_kpis.churn_risk:.2f}</p></div>
      </div>
    </section>
    <section class="slide">
      <h2>Turning Points</h2>
      <ul>{turning_rows or "<li>No turning points captured.</li>"}</ul>
    </section>
    <section class="slide">
      <h2>Persona Observer Notes</h2>
      <ul>{persona_rows or "<li>No persona notes available.</li>"}</ul>
    </section>
    <section class="slide">
      <h2>Periodic Observer Notes</h2>
      <ul>{summary_items or "<li><p>No periodic summaries generated.</p></li>"}</ul>
    </section>
    <section class="slide">
      <h2>Timeline</h2>
      <ul>{top_timeline or "<li><p>No timeline events recorded.</p></li>"}</ul>
    </section>
  </main>
</body>
</html>
"""


def build_final_report(state: DeepSimulationState, observer_model: Any | None) -> DeepSimulationFinalResponse:
    fallback = _fallback_final(state)
    payload = _state_observer_payload(state)

    report = fallback
    if observer_model is not None:
        prompt = (
            "You are an observer agent for a multi-persona simulation.\n"
            "Analyze what each persona represented and how they influenced the result.\n"
            "Return ONLY JSON following this schema: "
            f"{json.dumps(_FinalObserverOutput.model_json_schema(), separators=(',', ':'))}\n"
            "Constraints:\n"
            "- `summary`: executive narrative for non-technical stakeholders.\n"
            "- `key_turning_points`: concrete events, max 8.\n"
            "- `persona_observations`: include stance/evidence for personas actually present.\n"
            "- No markdown fences, no prose outside JSON.\n"
            f"State JSON: {json.dumps(payload, ensure_ascii=True)}"
        )
        try:
            if hasattr(observer_model, "with_structured_output"):
                structured = observer_model.with_structured_output(_FinalObserverOutput)
                result = structured.invoke(prompt)
            else:
                raw = observer_model.invoke(prompt)
                text = str(getattr(raw, "content", raw)).strip()
                parsed = _json_from_text(text)
                result = _FinalObserverOutput.model_validate(parsed)

            persona_index = {persona.id: persona for persona in state.personas}
            observations: list[PersonaObservationReport] = []
            for item in result.persona_observations:
                persona = persona_index.get(item.persona_id)
                if persona is None:
                    continue
                evidence = [str(row) for row in item.evidence if isinstance(row, str)][:5]
                observations.append(
                    PersonaObservationReport(
                        persona_id=persona.id,
                        name=persona.name,
                        role=persona.role,
                        objective=persona.objective,
                        stance=item.stance.strip() or "No stance provided",
                        evidence=evidence,
                        suggested_next_action=item.suggested_next_action.strip(),
                    )
                )
            if not observations:
                observations = _fallback_persona_observations(state)

            report = DeepSimulationFinalResponse(
                summary=result.summary.strip() or fallback.summary,
                key_turning_points=[str(item) for item in result.key_turning_points if isinstance(item, str)][:8]
                or fallback.key_turning_points,
                recommendation=result.recommendation.strip() or fallback.recommendation,
                confidence=max(0.0, min(1.0, float(result.confidence))),
                periodic_summaries=state.observer_summaries,
                persona_observations=observations,
                html_slides="",
            )
        except Exception:
            report = fallback

    report.html_slides = _slides_html(state, report)
    return report
