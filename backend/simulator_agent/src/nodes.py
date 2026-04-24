import asyncio
import json
import logging
import os
from threading import Thread
from collections import defaultdict
from datetime import UTC
from datetime import datetime
from typing import Any
from typing import Callable
from typing import Literal

from deepagents import create_deep_agent
from tavily import TavilyClient
from langgraph.config import get_stream_writer
from langgraph.types import Send
from pydantic import BaseModel
from pydantic import ValidationError

from .model import get_branch_model
from .model import get_openai_compat_kwargs
from .model import get_parser_model
from .model import get_persona_model_name
from .model import get_recommendation_model
from .model import get_selector_model
from .schemas import DecisionLLMOutput
from .schemas import PersonaResultOutput
from .schemas import PersonaSelectionOutput
from .schemas import RecommendationOutput
from .schemas import ScenarioBranchOutput
from .schemas import ScenarioFieldsOutput
from .state import PersonaResult
from .state import PersonaTemplate
from .state import RecommendationResult
from .state import ScenarioBranchResult
from .state import SimulatorState
from .utils.parsing import extract_json_block
from .utils.parsing import extract_text_content
from .utils.parsing import fallback_parse_decision
from .utils.parsing import normalize_decision

logger = logging.getLogger(__name__)

_PERSONA_SUBAGENTS: dict[tuple[str, str, float], Any] = {}
_DEFAULT_PERSONA_TOOLS: list[Any] | None = None
_SUBAGENT_MARKDOWN_FORMAT_GUIDELINES = """
Markdown authoring contract (strict):

Goal:
- Produce polished, UI-friendly Markdown that streams cleanly.
- Write for business users: concise, concrete, and evidence-led.

You CAN do:
- Use headings with `##` and `###`.
- Use short paragraphs and bullet lists (`- item`) for scanability.
- Use inline code with backticks for metrics, fields, tools, and literals (example: `gross_margin`, `+10%`).
- Use fenced code blocks with language tags only when showing real code/commands/log snippets.
- Use tables for compact comparisons.
- Use math in LaTeX form when useful:
  - Inline: `$Revenue = Price \\times Volume$`
  - Block:
    $$\\Delta Revenue \\approx (1+\\Delta Price)\\times(1+\\Delta Volume)-1$$
- Use callouts as bold labels (example: `**Risk:** ...`, `**Assumption:** ...`).

You CANNOT do:
- Do NOT output JSON, YAML, XML, or pseudo-JSON wrappers.
- Do NOT wrap the whole answer inside a single code block.
- Do NOT include chain-of-thought, hidden reasoning markers, or internal scratch notes.
- Do NOT ask users for missing access; proceed with explicit assumptions and uncertainty.
- Do NOT use HTML tags unless explicitly requested.
- Do NOT use nested bullets deeper than one level.

Required section order (always):
1. `## Situation`
2. `## Evidence`
3. `## Analysis`
4. `## Recommendation`
5. `## Validation`

Section rules:
- `Situation`: 2-4 lines summarizing scenario and objective.
- `Evidence`: concrete metrics, tool findings, sources, and observed constraints.
- `Analysis`: trade-offs, elasticity/impact logic, alternatives considered.
- `Recommendation`: explicit action, scope, timing, and success criteria.
- `Validation`: what to monitor next, trigger thresholds, and rollback conditions.

Style constraints:
- Keep each bullet to one idea.
- Keep paragraphs to 1-3 sentences.
- Prefer specific numbers/ranges over vague language.
- State confidence and key assumptions when data is incomplete.
"""


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
) -> dict[str, Any]:
    """Run web search with Tavily."""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return {
            "error": "TAVILY_API_KEY is not set.",
            "query": query,
            "suggestion": "Set TAVILY_API_KEY in backend/.env and restart backend.",
        }

    try:
        client = TavilyClient(api_key=api_key)
        return client.search(
            query=query,
            max_results=max_results,
            topic=topic,
            include_raw_content=include_raw_content,
        )
    except Exception as exc:
        logger.warning("simulator.tavily.search_failed error=%s", exc)
        return {
            "error": str(exc),
            "query": query,
        }


def _get_default_persona_tools() -> list[Any]:
    global _DEFAULT_PERSONA_TOOLS
    if _DEFAULT_PERSONA_TOOLS is None:
        _DEFAULT_PERSONA_TOOLS = [internet_search]
    return _DEFAULT_PERSONA_TOOLS


def _run_coro_in_sync_context(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: dict[str, Exception] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except Exception as exc:
            error["value"] = exc

    worker = Thread(target=_runner, daemon=True)
    worker.start()
    worker.join()
    if "value" in error:
        raise error["value"]
    return result.get("value")


def _get_parser_model() -> Any:
    # Reuse one chat model configuration across parser and synthesis steps.
    return get_parser_model()


def _schema_instruction(schema_type: type[BaseModel]) -> str:
    schema = schema_type.model_json_schema()
    schema.pop("$schema", None)
    schema.pop("title", None)
    return json.dumps(schema, ensure_ascii=True, separators=(",", ":"))


def _invoke_validated_json(model: Any, prompt: str, schema_type: type[BaseModel]) -> dict[str, Any] | None:
    if model is None:
        return None

    try:
        if hasattr(model, "with_structured_output"):
            structured_model = model.with_structured_output(schema_type)
            response = structured_model.invoke(prompt)
            if isinstance(response, schema_type):
                return response.model_dump()
            if isinstance(response, dict):
                return schema_type.model_validate(response).model_dump()
    except Exception:
        pass

    try:
        response = model.invoke(prompt)
        text = extract_text_content(getattr(response, "content", ""))
        parsed = extract_json_block(text)
        if isinstance(parsed, dict):
            return schema_type.model_validate(parsed).model_dump()
    except ValidationError:
        return None
    except Exception:
        return None

    return None


def _parse_with_llm(query: str) -> dict[str, Any] | None:
    model = _get_parser_model()
    prompt = (
        "Extract business decision fields from the request. "
        "Return only one JSON object, no markdown, no prose, and no extra keys. "
        "Prefer explicit values from the request; if missing, use conservative defaults instead of inventing specifics. "
        f"JSON schema: {_schema_instruction(DecisionLLMOutput)} "
        f"Request: {json.dumps(query)}"
    )
    return _invoke_validated_json(model, prompt, DecisionLLMOutput)


def _get_persona_subagent(persona: PersonaTemplate) -> Any:
    # Build persona-specific deep agents so role instructions live in system_prompt.
    global _PERSONA_SUBAGENTS

    model_name = get_persona_model_name()
    persona_prompt = str(persona.get("system_prompt") or "You are a business simulation persona.")
    system_prompt = f"{persona_prompt.strip()}\n\n{_SUBAGENT_MARKDOWN_FORMAT_GUIDELINES.strip()}"
    temperature = float(persona.get("temperature", 0.2))
    cache_key = (model_name, system_prompt, temperature)
    if cache_key in _PERSONA_SUBAGENTS:
        return _PERSONA_SUBAGENTS[cache_key]

    tools = _get_default_persona_tools()
    try:
        from langchain.chat_models import init_chat_model

        kwargs: dict[str, Any] = {"temperature": temperature}
        if model_name.startswith("openai:") or ":" not in model_name:
            kwargs.update(get_openai_compat_kwargs())
        model = init_chat_model(model=model_name, **kwargs)
        agent = create_deep_agent(model=model, system_prompt=system_prompt, tools=tools)
    except Exception:
        # Fallback to model string path if provider integration kwargs are unavailable.
        agent = create_deep_agent(model=model_name, system_prompt=system_prompt, tools=tools)

    _PERSONA_SUBAGENTS[cache_key] = agent
    return agent


def _extract_persona_structured_result(
    persona: PersonaTemplate, scenario: dict[str, Any], raw_text: str
) -> dict[str, Any] | None:
    model = _get_parser_model()
    prompt = (
        "You are normalizing a persona simulation response into a fixed schema. "
        "Return only one JSON object, no markdown, no prose, and no extra keys. "
        f"JSON schema: {_schema_instruction(PersonaResultOutput)} "
        f"Persona metadata: {json.dumps({'id': persona.get('id'), 'name': persona.get('name'), 'focus': persona.get('focus')})} "
        f"Scenario: {json.dumps(scenario)} "
        f"Persona free-form response: {json.dumps(raw_text)} "
        "Infer kpi_deltas only when direction or magnitude is explicitly implied; otherwise leave kpi_deltas empty. "
        "Extract risks and opportunities as short concrete items, deduplicated, max 5 each. "
        "Rationale must be concise and evidence-grounded; remove rhetorical filler. "
        "Set confidence using this rubric: 0.8-1.0 when response cites concrete internal evidence and quantified logic; "
        "0.5-0.79 when partially evidenced or mostly directional; 0.2-0.49 when speculative or data-sparse."
    )
    return _invoke_validated_json(model, prompt, PersonaResultOutput)


def _extract_persona_response_text(result: Any) -> str:
    if isinstance(result, dict):
        messages = result.get("messages")
        if isinstance(messages, list) and messages:
            for message in reversed(messages):
                content = getattr(message, "content", message.get("content") if isinstance(message, dict) else "")
                text = extract_text_content(content)
                if text.strip():
                    return text

        for key in ("output", "content", "text"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value
            text = extract_text_content(value)
            if text.strip():
                return text

    content = getattr(result, "content", "")
    text = extract_text_content(content)
    if text.strip():
        return text

    return str(result) if result is not None else ""


def _clip_stream_text(text: str, max_chars: int = 800) -> str:
    cleaned = text.replace("\r", "")
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[:max_chars]}..."


def _safe_emit_custom_event(
    payload: dict[str, Any],
    stream_writer: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    if stream_writer is not None:
        try:
            stream_writer(payload)
            return
        except Exception:
            return
    try:
        writer = get_stream_writer()
        writer(payload)
    except Exception:
        # No active stream writer (non-stream invocation) or unsupported runtime context.
        return


def _extract_tool_call_chunks(message_chunk: Any) -> list[dict[str, Any]]:
    chunks = getattr(message_chunk, "tool_call_chunks", None)
    if isinstance(chunks, list):
        return [chunk for chunk in chunks if isinstance(chunk, dict)]

    content = getattr(message_chunk, "content", None)
    if not isinstance(content, list):
        return []

    tool_chunks: list[dict[str, Any]] = []
    for block in content:
        if isinstance(block, dict) and str(block.get("type") or "") == "tool_call_chunk":
            tool_chunks.append(block)
    return tool_chunks


async def _collect_persona_subagent_stream(
    agent: Any,
    prompt: str,
    persona_id: str,
    emit_event: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[str, list[dict[str, str]]]:
    stream_events: list[dict[str, str]] = []
    latest_values: dict[str, Any] | None = None
    emitted_tool_calls: set[str] = set()

    async for part in agent.astream(
        {"messages": [{"role": "user", "content": prompt}]},
        stream_mode=["messages", "values"],
        version="v2",
    ):
        if not isinstance(part, dict):
            continue

        part_type = part.get("type")
        if part_type == "messages":
            data = part.get("data")
            if not isinstance(data, (tuple, list)) or not data:
                continue
            message_chunk = data[0]
            metadata = data[1] if len(data) > 1 and isinstance(data[1], dict) else {}
            for tool_chunk in _extract_tool_call_chunks(message_chunk):
                tool_name = str(tool_chunk.get("name") or tool_chunk.get("tool_name") or "").strip()
                tool_id = str(tool_chunk.get("id") or "").strip()
                if not tool_name:
                    continue
                dedupe_key = f"{tool_id}:{tool_name}" if tool_id else tool_name
                if dedupe_key in emitted_tool_calls:
                    continue
                emitted_tool_calls.add(dedupe_key)
                if emit_event is not None:
                    emit_event(
                        {
                            "event": "subagent_tool",
                            "persona_id": persona_id,
                            "tool_name": tool_name,
                            "tool_id": tool_id,
                            "node": str(metadata.get("langgraph_node") or "subagent"),
                            "message": f"Calling tool `{tool_name}`",
                        }
                    )
            content = getattr(message_chunk, "content", "")
            token_text = extract_text_content(content)
            clipped = _clip_stream_text(token_text)
            if clipped:
                if emit_event is not None:
                    emit_event(
                        {
                            "event": "subagent_token",
                            "persona_id": persona_id,
                            "text": clipped,
                            "node": str(metadata.get("langgraph_node") or "subagent"),
                        }
                    )
                stream_events.append(
                    {
                        "persona_id": persona_id,
                        "text": clipped,
                        "node": str(metadata.get("langgraph_node") or "subagent"),
                    }
                )
        elif part_type == "values":
            values = part.get("data")
            if isinstance(values, dict):
                latest_values = values

    raw_text = ""
    if latest_values is not None:
        raw_text = _extract_persona_response_text(latest_values)
    if not raw_text and stream_events:
        raw_text = "".join(event["text"] for event in stream_events if event.get("text"))

    return raw_text, stream_events


def parse_decision_node(state: SimulatorState) -> dict[str, Any]:
    query = state.get("query", "")
    parsed = _parse_with_llm(query)
    if not parsed:
        logger.warning("simulator.parse_decision.fallback_used query_len=%s", len(str(query)))
    decision = normalize_decision(parsed) if parsed else normalize_decision(fallback_parse_decision(query))
    return {"decision": decision}


def _fallback_scenario_fields(state: SimulatorState) -> dict[str, Any]:
    decision = state.get("decision", {})
    decision_type = str(decision.get("decision_type") or "unknown")
    delta_value = decision.get("delta_value")
    delta_unit = decision.get("delta_unit")
    time_horizon = str(decision.get("time_horizon") or "unknown")
    target_segments = decision.get("target_segments") if isinstance(decision.get("target_segments"), list) else []

    impact_text = "unspecified impact"
    if isinstance(delta_value, (int, float)) and isinstance(delta_unit, str) and delta_unit.strip():
        impact_text = f"{delta_value:g} {delta_unit.strip()}"

    return {
        "title": f"{decision_type.title()} Scenario",
        "summary": (
            f"Evaluate a {decision_type} decision with expected impact of {impact_text} "
            f"over {time_horizon}."
        ),
        "objectives": ["Estimate KPI impact", "Surface major risks and opportunities"],
        "key_questions": [
            "What are the main upside and downside outcomes?",
            "Which assumptions most affect the outcome?",
            "What execution dependencies could block success?",
        ],
        "constraints": ["Use available business context and provided assumptions only"],
        "primary_kpis": ["revenue_pct", "risk_level"],
        "target_segments": [str(item) for item in target_segments if isinstance(item, str)],
    }


def _build_scenario_with_llm(state: SimulatorState) -> dict[str, Any] | None:
    model = _get_parser_model()
    prompt = (
        "You are building a simulation scenario from a business decision input. "
        "Return only one JSON object, no markdown, no prose, and no extra keys. "
        "Focus on testable objectives, measurable KPIs, and decision-relevant constraints. "
        "If information is missing, include explicit uncertainty via assumptions in questions/constraints instead of fabricating facts. "
        f"JSON schema: {_schema_instruction(ScenarioFieldsOutput)} "
        f"Decision: {json.dumps(state.get('decision', {}))} "
        f"Query: {json.dumps(state.get('query', ''))} "
        f"Structured data: {json.dumps(state.get('structured_data', {}))} "
        f"Business context: {json.dumps(state.get('business_context', {}))} "
        f"Documents: {json.dumps(state.get('documents', []))}"
    )
    return _invoke_validated_json(model, prompt, ScenarioFieldsOutput)


def build_scenario_node(state: SimulatorState) -> dict[str, Any]:
    llm_fields = _build_scenario_with_llm(state)
    if not llm_fields:
        logger.warning("simulator.build_scenario.fallback_used")
        llm_fields = _fallback_scenario_fields(state)
    scenario = {
        "scenario_id": datetime.now(UTC).strftime("sim-%Y%m%d%H%M%S"),
        "query": state.get("query", ""),
        "decision": state.get("decision", {}),
        "structured_data": state.get("structured_data", {}),
        "documents": state.get("documents", []),
        "business_context": state.get("business_context", {}),
        **llm_fields,
    }
    return {"scenario": scenario}


def _normalize_persona_template(data: dict[str, Any], index: int) -> PersonaTemplate:
    persona_id = str(data.get("id") or f"dynamic_persona_{index + 1}").strip().lower().replace(" ", "_")
    expected_outputs = [str(item) for item in data.get("expected_outputs", []) if isinstance(item, str)]
    if not expected_outputs:
        expected_outputs = ["kpi_deltas", "risks", "opportunities", "rationale"]

    tools = [str(item) for item in data.get("tools", []) if isinstance(item, str)]
    temperature = data.get("temperature", 0.2)
    if not isinstance(temperature, (int, float)):
        temperature = 0.2

    return {
        "id": persona_id,
        "name": str(data.get("name") or f"Dynamic Persona {index + 1}"),
        "role": str(data.get("role") or "scenario evaluator"),
        "focus": str(data.get("focus") or "business impact analysis"),
        "system_prompt": str(data.get("system_prompt") or "You are a business simulation persona."),
        "tools": tools,
        "temperature": float(temperature),
        "expected_outputs": expected_outputs,
    }


def _fallback_personas(state: SimulatorState) -> list[PersonaTemplate]:
    decision = state.get("decision", {})
    decision_type = str(decision.get("decision_type", "unknown")).lower()

    if "launch" in decision_type:
        personas_data = [
            {
                "id": "product_owner",
                "name": "Product Owner",
                "role": "product launch evaluator",
                "focus": "adoption, product fit, and launch readiness",
                "system_prompt": "You are a product owner evaluating launch readiness, adoption, and product-market fit.",
            },
            {
                "id": "go_to_market_strategist",
                "name": "Go-To-Market Strategist",
                "role": "market rollout strategist",
                "focus": "positioning, channels, and launch traction",
                "system_prompt": "You are a go-to-market strategist focused on positioning, channels, and launch traction.",
            },
        ]
    else:
        personas_data = [
            {
                "id": "finance_operator",
                "name": "Finance Operator",
                "role": "pricing and unit economics evaluator",
                "focus": "margin, revenue quality, and downside risk",
                "system_prompt": "You are a finance operator evaluating pricing, margin, and downside risk.",
            },
            {
                "id": "customer_voice_lead",
                "name": "Customer Voice Lead",
                "role": "customer impact evaluator",
                "focus": "retention, sentiment, and adoption friction",
                "system_prompt": "You are a customer voice lead focused on retention, sentiment, and adoption friction.",
            },
        ]

    personas_data.append(
        {
            "id": "execution_manager",
            "name": "Execution Manager",
            "role": "execution risk evaluator",
            "focus": "operational complexity, rollout sequencing, and dependencies",
            "system_prompt": "You are an execution manager focused on rollout sequencing, dependencies, and operational risk.",
        }
    )

    return [
        _normalize_persona_template(
            {
                **persona,
                "tools": [],
                "temperature": 0.2,
                "expected_outputs": ["kpi_deltas", "risks", "opportunities", "rationale"],
            },
            index,
        )
        for index, persona in enumerate(personas_data)
    ]


def _select_personas_with_llm(state: SimulatorState) -> list[PersonaTemplate] | None:
    model = get_selector_model()
    prompt = (
        "You are designing simulation subagents for a business decision. "
        "Invent personas dynamically from the scenario instead of picking from a fixed catalog. "
        "Return only one JSON object, no markdown, no prose, and no extra keys. "
        f"JSON schema: {_schema_instruction(PersonaSelectionOutput)} "
        "Select the number of personas dynamically based on scenario complexity, minimum 1 and maximum 10, target 3-6. "
        "Each persona must have a distinct role and a system prompt suitable for its subagent. "
        "Persona set should cover at least three angles when applicable: economics/finance, customer/market, and execution/operations. "
        "Write each system_prompt to be action-oriented, evidence-seeking, and decision-focused. "
        "System prompts must tell personas to avoid asking humans for access and to proceed with explicit uncertainty when data is sparse. "
        f"Scenario: {json.dumps(state.get('scenario', {}))} "
        f"Decision: {json.dumps(state.get('decision', {}))}"
    )
    parsed = _invoke_validated_json(model, prompt, PersonaSelectionOutput)
    if parsed and isinstance(parsed.get("selected_personas"), list):
        personas = [
            _normalize_persona_template(persona, index)
            for index, persona in enumerate(parsed["selected_personas"])
            if isinstance(persona, dict)
        ]
        if personas:
            return personas[:10]

    return None


def select_personas_node(state: SimulatorState) -> dict[str, Any]:
    selected_personas = _select_personas_with_llm(state)
    if not selected_personas:
        logger.warning("simulator.select_personas.fallback_used")
        selected_personas = _fallback_personas(state)
    logger.info("simulator.select_personas.count=%s", len(selected_personas))
    return {"selected_personas": selected_personas}


def dispatch_subagents_route(state: SimulatorState) -> list[Send] | str:
    # Route to fan-out when personas exist, otherwise skip directly to the fan-in node.
    personas = state.get("selected_personas", [])
    scenario = state.get("scenario", {})

    if not personas:
        return "collect_results"

    return [Send("persona_worker", {"active_persona": persona, "scenario": scenario}) for persona in personas]


def _run_persona_subagent(
    persona: PersonaTemplate,
    scenario: dict[str, Any],
    stream_writer: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[PersonaResult, list[dict[str, str]]]:
    # Persona workers stream free-form reasoning first; structuring happens in a parser pass.
    persona_id = str(persona.get("id") or "unknown")
    prompt = (
        "Role-play this persona for the given business scenario and produce a decisive analysis. "
        "Think through tradeoffs and uncertainty before conclusions. "
        "Use the internet_search tool first to gather evidence relevant to this scenario. "
        "Do not ask for file access, approvals, or external help; operate only with provided tools and context. "
        "If evidence is missing, explicitly state data gaps and continue with bounded assumptions/sensitivity ranges. "
        "End with a concrete recommendation and one validation experiment (A/B test, phased rollout, or guardrail metric). "
        "Follow the Markdown output contract from your system prompt exactly. "
        "Do not output JSON. Respond in markdown prose suitable for live streaming in a UI. "
        "Keep output practical, concise, and specific. "
        f"Persona metadata: {json.dumps({'id': persona_id, 'name': persona.get('name'), 'focus': persona.get('focus')})} "
        "Available tools: ['internet_search'] "
        f"Scenario: {json.dumps(scenario)}"
    )

    raw_text = ""
    stream_events: list[dict[str, str]] = []
    try:
        logger.info("simulator.persona.start persona_id=%s", persona_id)
        _safe_emit_custom_event(
            {"event": "subagent_status", "persona_id": persona_id, "status": "running"},
            stream_writer=stream_writer,
        )
        agent = _get_persona_subagent(persona)
        raw_text, stream_events = _run_coro_in_sync_context(
            _collect_persona_subagent_stream(
                agent,
                prompt,
                persona_id,
                emit_event=lambda payload: _safe_emit_custom_event(payload, stream_writer=stream_writer),
            )
        )
        if not raw_text:
            result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
            raw_text = _extract_persona_response_text(result)
        parsed = _extract_persona_structured_result(persona, scenario, raw_text)
        if parsed:
            normalized = PersonaResultOutput.model_validate(parsed).model_dump()
            rationale = str(normalized.get("rationale") or "").strip()
            if not rationale and raw_text.strip():
                rationale = raw_text.strip()[:1200]
            return (
                {
                    "persona_id": str(normalized.get("persona_id") or persona_id),
                    "confidence": float(normalized.get("confidence", 0.5)),
                    "kpi_deltas": normalized.get("kpi_deltas") if isinstance(normalized.get("kpi_deltas"), dict) else {},
                    "risks": [str(item) for item in normalized.get("risks", []) if isinstance(item, str)],
                    "opportunities": [str(item) for item in normalized.get("opportunities", []) if isinstance(item, str)],
                    "rationale": rationale,
                },
                stream_events[-40:],
            )
        logger.warning(
            "simulator.persona.structured_parse_failed persona_id=%s raw_len=%s",
            persona_id,
            len(raw_text),
        )
    except (ValidationError, Exception):
        logger.exception("simulator.persona.failed persona_id=%s", persona_id)

    logger.warning("simulator.persona.fallback_used persona_id=%s raw_len=%s", persona_id, len(raw_text))
    _safe_emit_custom_event(
        {"event": "subagent_status", "persona_id": persona_id, "status": "fallback"},
        stream_writer=stream_writer,
    )
    return (
        {
            "persona_id": persona_id,
            "confidence": 0.35,
            "kpi_deltas": {},
            "risks": ["Persona parser fallback used."],
            "opportunities": [],
            "rationale": raw_text[:1200] if raw_text else "Persona returned no usable content.",
        },
        stream_events[-40:],
    )


def persona_worker_node(state: SimulatorState) -> dict[str, Any]:
    persona = state.get("active_persona", {"id": "unknown", "name": "Unknown", "focus": "unknown"})
    scenario = state.get("scenario", {})
    try:
        stream_writer = get_stream_writer()
    except Exception:
        stream_writer = None

    persona_result, stream_events = _run_persona_subagent(persona, scenario, stream_writer=stream_writer)
    persona_id = str(persona_result.get("persona_id", "unknown"))
    final_status = "fallback" if any("fallback" in str(r).lower() for r in persona_result.get("risks", [])) else "done"
    _safe_emit_custom_event(
        {"event": "subagent_status", "persona_id": persona_id, "status": final_status},
        stream_writer=stream_writer,
    )
    return {"persona_results": [persona_result], "persona_stream_events": stream_events}


def collect_results_node(_state: SimulatorState) -> dict[str, Any]:
    # No state mutation needed; this node marks the fan-in boundary before aggregation.
    # this makes the graph readable, gives a stable place to add logic in future
    # eg. validation etc
    return {}


def _aggregate_kpi_deltas(persona_results: list[PersonaResult]) -> dict[str, float]:
    weighted_sums: dict[str, float] = defaultdict(float)
    weighted_totals: dict[str, float] = defaultdict(float)

    for result in persona_results:
        confidence = float(result.get("confidence", 0.0))
        kpis = result.get("kpi_deltas", {})
        if not isinstance(kpis, dict):
            continue

        for key, value in kpis.items():
            if isinstance(value, (int, float)):
                weighted_sums[key] += float(value) * confidence
                weighted_totals[key] += confidence

    return {
        key: (weighted_sums[key] / weighted_totals[key]) if weighted_totals[key] > 0 else 0.0
        for key in weighted_sums
    }


def _rank_signal_items(persona_results: list[PersonaResult], field_name: str) -> list[str]:
    scores: dict[str, float] = defaultdict(float)
    first_seen_order: dict[str, int] = {}
    next_index = 0

    for result in persona_results:
        confidence = float(result.get("confidence", 0.0))
        items = result.get(field_name, [])
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if not normalized:
                continue
            if normalized not in first_seen_order:
                first_seen_order[normalized] = next_index
                next_index += 1
            scores[normalized] += confidence if confidence > 0 else 0.1

    return [
        item
        for item, _score in sorted(
            scores.items(),
            key=lambda pair: (-pair[1], first_seen_order[pair[0]]),
        )
    ]


def aggregate_impacts_node(state: SimulatorState) -> dict[str, Any]:
    # Roll up all numeric KPI deltas and preserve a few summary counters for downstream nodes.
    persona_results = state.get("persona_results", [])
    kpi_rollup = _aggregate_kpi_deltas(persona_results)
    ranked_risks = _rank_signal_items(persona_results, "risks")
    ranked_opportunities = _rank_signal_items(persona_results, "opportunities")

    aggregated_impacts = {
        "weighted_revenue_pct": kpi_rollup.get("revenue_pct", 0.0),
        "kpi_rollup": kpi_rollup,
        "total_personas": len(persona_results),
        "risk_count": sum(
            len(result.get("risks", [])) for result in persona_results if isinstance(result.get("risks"), list)
        ),
        "opportunity_count": sum(
            len(result.get("opportunities", []))
            for result in persona_results
            if isinstance(result.get("opportunities"), list)
        ),
        "top_risks": ranked_risks,
        "top_opportunities": ranked_opportunities,
    }
    return {"aggregated_impacts": aggregated_impacts}


def dispatch_scenario_branches_route(_state: SimulatorState) -> list[Send]:
    # Fan out into three simple forecast branches to stress the aggregated result.
    branch_names = ["optimistic", "base", "pessimistic"]
    return [Send("scenario_branch_worker", {"active_branch": branch_name}) for branch_name in branch_names]


def _fallback_scenario_branch(branch_name: str, impacts: dict[str, Any]) -> ScenarioBranchResult:
    base_revenue = float(impacts.get("weighted_revenue_pct", 0.0))
    risk_count = int(impacts.get("risk_count", 0))
    opportunity_count = int(impacts.get("opportunity_count", 0))

    adjustments = {
        "optimistic": 1.5,
        "base": 1.0,
        "pessimistic": 0.5,
    }
    revenue_pct = base_revenue * adjustments.get(branch_name, 1.0)

    if branch_name == "optimistic":
        revenue_pct += max(opportunity_count - risk_count, 0) * 0.25
    elif branch_name == "pessimistic":
        revenue_pct -= max(risk_count - opportunity_count, 0) * 0.25

    if risk_count >= opportunity_count + 2:
        risk_level = "high"
    elif risk_count > opportunity_count:
        risk_level = "medium"
    else:
        risk_level = "low"

    summary = (
        f"{branch_name.title()} case projects {revenue_pct:.2f}% revenue change "
        f"with {risk_level} execution risk."
    )
    return {
        "branch_name": branch_name,
        "revenue_pct": revenue_pct,
        "risk_level": risk_level,
        "assumptions": ["Fallback branch logic used because model output was unavailable."],
        "summary": summary,
    }


def _run_scenario_branch(
    branch_name: str,
    impacts: dict[str, Any],
    persona_results: list[PersonaResult],
    decision: dict[str, Any],
) -> ScenarioBranchResult:
    model = get_branch_model()
    if model is None:
        logger.warning("simulator.branch.fallback_no_model branch=%s", branch_name)
        return _fallback_scenario_branch(branch_name, impacts)

    prompt = (
        "You are simulating one forecast branch for a business decision. "
        "Return only one JSON object, no markdown, no prose, and no extra keys. "
        "Keep assumptions explicit and branch-specific; optimistic/base/pessimistic must materially differ. "
        f"JSON schema: {_schema_instruction(ScenarioBranchOutput)} "
        f"Decision: {json.dumps(decision)} "
        f"Aggregated impacts: {json.dumps(impacts)} "
        f"Persona results: {json.dumps(persona_results)} "
        f"Requested branch: {branch_name}"
    )
    parsed = _invoke_validated_json(model, prompt, ScenarioBranchOutput)
    if parsed:
        return {
            "branch_name": str(parsed.get("branch_name") or branch_name),
            "revenue_pct": float(parsed.get("revenue_pct", 0.0)),
            "risk_level": str(parsed.get("risk_level") or "medium").lower(),
            "assumptions": [str(item) for item in parsed.get("assumptions", []) if isinstance(item, str)],
            "summary": str(parsed.get("summary") or ""),
        }

    logger.warning("simulator.branch.fallback_parse_failed branch=%s", branch_name)
    return _fallback_scenario_branch(branch_name, impacts)


def scenario_branch_worker_node(state: SimulatorState) -> dict[str, Any]:
    branch_name = str(state.get("active_branch", "base"))
    impacts = state.get("aggregated_impacts", {})
    persona_results = state.get("persona_results", [])
    decision = state.get("decision", {})
    return {"scenario_branches": [_run_scenario_branch(branch_name, impacts, persona_results, decision)]}


def _fallback_recommendation(state: SimulatorState) -> RecommendationResult:
    impacts = state.get("aggregated_impacts", {})
    scenario_branches = state.get("scenario_branches", [])
    weighted_revenue = float(impacts.get("weighted_revenue_pct", 0.0))
    risk_count = int(impacts.get("risk_count", 0))
    opportunity_count = int(impacts.get("opportunity_count", 0))
    pessimistic_branch = next((branch for branch in scenario_branches if branch.get("branch_name") == "pessimistic"), {})
    pessimistic_revenue = float(pessimistic_branch.get("revenue_pct", weighted_revenue))

    if weighted_revenue > 0 and pessimistic_revenue >= 0 and opportunity_count >= risk_count:
        summary = "Proceed with a controlled rollout and weekly KPI checkpoints."
    elif weighted_revenue < 0 or pessimistic_revenue < 0 or risk_count > opportunity_count:
        summary = "Hold broad rollout. Run a limited experiment and mitigate top risks first."
    else:
        summary = "Proceed cautiously with staged rollout and explicit guardrails."

    return {
        "summary": summary,
        "reasoning": [
            f"Weighted revenue forecast is {weighted_revenue:.2f}%.",
            f"Pessimistic branch forecast is {pessimistic_revenue:.2f}%.",
            f"Risks count {risk_count} versus opportunities count {opportunity_count}.",
        ],
        "assumptions": ["Fallback recommendation logic used because model output was unavailable."],
    }


def _generate_recommendation(state: SimulatorState) -> RecommendationResult:
    model = get_recommendation_model()
    if model is None:
        logger.warning("simulator.recommendation.fallback_no_model")
        return _fallback_recommendation(state)

    prompt = (
        "You are writing the final recommendation for a business simulation. "
        "Return only one JSON object, no markdown, no prose, and no extra keys. "
        "Recommendation must be decision-oriented: state go/no-go or staged-go, key rationale, and operational guardrails. "
        "Reasoning items must be concrete and reference the strongest signals from impacts/branches/personas. "
        "Assumptions must explicitly call out major uncertainty and what data would most reduce it. "
        f"JSON schema: {_schema_instruction(RecommendationOutput)} "
        f"Decision: {json.dumps(state.get('decision', {}))} "
        f"Scenario: {json.dumps(state.get('scenario', {}))} "
        f"Aggregated impacts: {json.dumps(state.get('aggregated_impacts', {}))} "
        f"Scenario branches: {json.dumps(state.get('scenario_branches', []))} "
        f"Persona results: {json.dumps(state.get('persona_results', []))}"
    )
    parsed = _invoke_validated_json(model, prompt, RecommendationOutput)
    if parsed:
        summary = str(parsed.get("summary") or "").strip()
        if summary:
            return {
                "summary": summary,
                "reasoning": [str(item) for item in parsed.get("reasoning", []) if isinstance(item, str)],
                "assumptions": [str(item) for item in parsed.get("assumptions", []) if isinstance(item, str)],
            }

    logger.warning("simulator.recommendation.fallback_parse_failed")
    return _fallback_recommendation(state)


def generate_recommendation_node(state: SimulatorState) -> dict[str, Any]:
    recommendation = _generate_recommendation(state)
    return {
        "recommendation": recommendation["summary"],
        "recommendation_details": recommendation,
    }


def format_response_node(state: SimulatorState) -> dict[str, Any]:
    # Shape the final payload around the four output blocks described in the plan.
    persona_results = state.get("persona_results", [])
    aggregated_impacts = state.get("aggregated_impacts", {})

    response = {
        "kpi_deltas": aggregated_impacts.get("kpi_rollup", {}),
        "persona_reactions": persona_results,
        "scenario_branches": state.get("scenario_branches", []),
        "ranked_risks": aggregated_impacts.get("top_risks", []),
        "ranked_opportunities": aggregated_impacts.get("top_opportunities", []),
        "recommendation": state.get("recommendation", ""),
        "recommendation_details": state.get("recommendation_details", {}),
    }

    return {"response": response}
