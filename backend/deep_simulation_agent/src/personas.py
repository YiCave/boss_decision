from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from .schema import PersonaProfile


class PersonaProposal(BaseModel):
    id: str
    name: str
    role: str
    objective: str
    system_prompt: str
    preferred_paths: list[str] = Field(default_factory=list)
    weight: float = 1.0


class PersonaProposalBatch(BaseModel):
    personas: list[PersonaProposal] = Field(default_factory=list)


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized or "persona"


def _to_model_json(model: type[BaseModel]) -> str:
    schema = model.model_json_schema()
    schema.pop("$schema", None)
    schema.pop("title", None)
    return json.dumps(schema, separators=(",", ":"), ensure_ascii=True)


def _safe_validate_personas(raw: Any) -> list[PersonaProposal]:
    if isinstance(raw, PersonaProposalBatch):
        return raw.personas
    if isinstance(raw, dict):
        return PersonaProposalBatch.model_validate(raw).personas
    return []


def _build_fallback_personas(query: str, rng: random.Random, count: int) -> list[PersonaProposal]:
    domain_hints = [
        ("Market Economist", "price elasticity and margin durability"),
        ("Consumer Psychologist", "demand reaction and churn signal"),
        ("Ops Strategist", "execution risk and rollout sequencing"),
        ("Competitive Analyst", "retaliation probability and moat defense"),
        ("Brand Strategist", "positioning, messaging, and perception risk"),
        ("Finance Controller", "unit economics and downside limits"),
        ("Growth Lead", "acquisition channel impact and CAC payback"),
        ("Risk Officer", "control guardrails and failure modes"),
    ]
    rng.shuffle(domain_hints)
    selected = domain_hints[:count]
    personas: list[PersonaProposal] = []
    for idx, (name, objective) in enumerate(selected, start=1):
        pid = f"{_slug(name)}_{idx:03d}"
        personas.append(
            PersonaProposal(
                id=pid,
                name=f"{name} {idx:03d}",
                role=name.lower(),
                objective=objective,
                system_prompt=(
                    "You are a strategic persona in a 2D market simulation. "
                    "React to the scenario in concise markdown with evidence, assumptions, and actionable advice. "
                    "If a world-changing move is justified, call `submit_action_intent` with concrete args."
                ),
                preferred_paths=["companies", "market", "reports"],
                weight=1.0,
            )
        )
    if query and "student" in query.lower() and personas:
        personas[0].objective = "student segment behavior under price pressure"
    return personas


def _resolve_allowlist_roots(base_docs_dir: Path, preferred_paths: list[str]) -> list[str]:
    roots: list[str] = []
    for path_name in preferred_paths:
        candidate = (base_docs_dir / path_name).resolve()
        if candidate.exists() and candidate.is_dir():
            roots.append(str(candidate))
    if not roots and base_docs_dir.exists():
        roots.append(str(base_docs_dir.resolve()))
    return roots


def propose_personas(
    query: str,
    scenario: dict[str, Any],
    min_personas: int,
    max_personas: int,
    rng: random.Random,
    selector_model: Any | None,
    base_docs_dir: Path,
) -> list[PersonaProfile]:
    min_count = max(1, min_personas)
    max_count = max(min_count, max_personas)
    target_count = min(max_count, max(min_count, 4))

    raw_personas: list[PersonaProposal] = []
    if selector_model is not None:
        prompt = (
            "Design simulation personas dynamically for a business scenario. "
            "Do not use a fixed catalog; choose specialized roles for this query. "
            "Return only JSON. "
            f"JSON schema: {_to_model_json(PersonaProposalBatch)} "
            f"Constraints: min_personas={min_count}, max_personas={max_count}. "
            "Each persona must include concrete objective and system_prompt. "
            "preferred_paths should reference likely folders like companies, market, reports, finance, operations. "
            f"Query: {json.dumps(query)} "
            f"Scenario: {json.dumps(scenario)}"
        )
        try:
            if hasattr(selector_model, "with_structured_output"):
                structured = selector_model.with_structured_output(PersonaProposalBatch)
                data = structured.invoke(prompt)
                raw_personas = _safe_validate_personas(data)
            else:
                response = selector_model.invoke(prompt)
                text = str(getattr(response, "content", response))
                parsed = json.loads(text) if text.strip().startswith("{") else {}
                raw_personas = _safe_validate_personas(parsed)
        except Exception:
            raw_personas = []

    if not raw_personas:
        raw_personas = _build_fallback_personas(query, rng, target_count)

    selected = raw_personas[:max_count]
    if len(selected) < min_count:
        supplement = _build_fallback_personas(query, rng, min_count - len(selected))
        selected.extend(supplement)

    seen_ids: set[str] = set()
    profiles: list[PersonaProfile] = []
    for idx, persona in enumerate(selected, start=1):
        candidate_id = _slug(persona.id or persona.name or f"persona_{idx}")
        if candidate_id in seen_ids:
            candidate_id = f"{candidate_id}_{idx:03d}"
        seen_ids.add(candidate_id)
        allow_roots = _resolve_allowlist_roots(base_docs_dir, persona.preferred_paths)
        profiles.append(
            PersonaProfile(
                id=candidate_id,
                name=persona.name or f"Persona {idx:03d}",
                role=persona.role or "analyst",
                objective=persona.objective or "evaluate scenario impact",
                system_prompt=persona.system_prompt,
                allowed_paths=allow_roots,
                weight=max(0.1, min(4.0, float(persona.weight or 1.0))),
            )
        )
    return profiles
