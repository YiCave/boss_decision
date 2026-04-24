import operator
from typing import Any
from typing import Annotated
from typing import TypedDict

# parsed version of users decision
class DecisionSchema(TypedDict, total=False):
    decision_type: str
    delta_value: float | None
    delta_unit: str | None
    time_horizon: str
    target_segments: list[str]
    confidence: float
    assumptions: list[str]

# definition and config for each simulated persona subagent
class PersonaTemplate(TypedDict):
    id: str
    name: str
    role: str
    focus: str
    system_prompt: str
    tools: list[str]
    temperature: float
    expected_outputs: list[str]

# output from persona subagent
class PersonaResult(TypedDict, total=False):
    persona_id: str
    confidence: float
    kpi_deltas: dict[str, Any]
    risks: list[str]
    opportunities: list[str]
    rationale: str

# output from one forecast branch
class ScenarioBranchResult(TypedDict, total=False):
    branch_name: str
    revenue_pct: float
    risk_level: str
    assumptions: list[str]
    summary: str

# final recommendation payload
class RecommendationResult(TypedDict, total=False):
    summary: str
    reasoning: list[str]
    assumptions: list[str]

# full graph states
class SimulatorState(TypedDict, total=False):
    query: str
    structured_data: dict[str, Any]
    documents: list[str]
    business_context: dict[str, Any]
    decision: DecisionSchema
    scenario: dict[str, Any]
    selected_personas: list[PersonaTemplate]
    active_persona: PersonaTemplate
    # operator.add tells langgraph to merge the result from different personas , avoid merge conflict
    # so list[existing + new] when multiple nodes tries to update this persona_results key
    
    # Annotated allows to Annotated[actual data type , metadata]
    persona_results: Annotated[list[PersonaResult], operator.add]
    persona_stream_events: Annotated[list[dict[str, Any]], operator.add]
    aggregated_impacts: dict[str, Any]
    active_branch: str
    scenario_branches: Annotated[list[ScenarioBranchResult], operator.add]
    recommendation: str
    recommendation_details: RecommendationResult
    response: dict[str, Any]
