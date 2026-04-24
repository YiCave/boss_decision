from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DecisionLLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision_type: str = "unknown"
    delta_value: float | None = None
    delta_unit: str | None = None
    time_horizon: str = "unspecified"
    target_segments: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    assumptions: list[str] = Field(default_factory=list)


class ScenarioFieldsOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = "Business Decision Scenario"
    summary: str = ""
    objectives: list[str] = Field(default_factory=list)
    key_questions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    primary_kpis: list[str] = Field(default_factory=list)
    target_segments: list[str] = Field(default_factory=list)


class PersonaTemplateOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = "dynamic_persona"
    name: str = "Dynamic Persona"
    role: str = "scenario evaluator"
    focus: str = "business impact analysis"
    system_prompt: str = "You are a business simulation persona."
    tools: list[str] = Field(default_factory=list)
    temperature: float = 0.2
    expected_outputs: list[str] = Field(
        default_factory=lambda: ["kpi_deltas", "risks", "opportunities", "rationale"]
    )


class PersonaSelectionOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    selected_personas: list[PersonaTemplateOutput] = Field(default_factory=list)


class PersonaResultOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    persona_id: str = "unknown"
    confidence: float = 0.5
    kpi_deltas: dict[str, Any] = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    rationale: str = ""


class ScenarioBranchOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    branch_name: str = "base"
    revenue_pct: float = 0.0
    risk_level: Literal["low", "medium", "high"] = "medium"
    assumptions: list[str] = Field(default_factory=list)
    summary: str = ""


class RecommendationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str = ""
    reasoning: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
