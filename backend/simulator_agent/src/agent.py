from typing import Any

from langgraph.graph import END
from langgraph.graph import START
from langgraph.graph import StateGraph

from src.nodes import aggregate_impacts_node
from src.nodes import build_scenario_node
from src.nodes import collect_results_node
from src.nodes import dispatch_subagents_route
from src.nodes import dispatch_scenario_branches_route
from src.nodes import format_response_node
from src.nodes import generate_recommendation_node
from src.nodes import parse_decision_node
from src.nodes import persona_worker_node
from src.nodes import scenario_branch_worker_node
from src.nodes import select_personas_node
from src.state import SimulatorState


def build_graph():
    # Keep the graph structure aligned with the phased flow in plan.md.
    builder = StateGraph(SimulatorState)

    # Phase 1
    builder.add_node("parse_decision", parse_decision_node)
    builder.add_node("build_scenario", build_scenario_node)
    builder.add_node("select_personas", select_personas_node)

    # Phase 2
    builder.add_node("persona_worker", persona_worker_node)

    # Phase 3 + 4
    builder.add_node("collect_results", collect_results_node)
    builder.add_node("aggregate_impacts", aggregate_impacts_node)
    builder.add_node("scenario_branch_worker", scenario_branch_worker_node)
    builder.add_node("generate_recommendation", generate_recommendation_node)
    builder.add_node("format_response", format_response_node)

    builder.add_edge(START, "parse_decision")
    builder.add_edge("parse_decision", "build_scenario")
    builder.add_edge("build_scenario", "select_personas")
    builder.add_conditional_edges("select_personas", dispatch_subagents_route, ["persona_worker", "collect_results"])
    builder.add_edge("persona_worker", "collect_results")
    builder.add_edge("collect_results", "aggregate_impacts")
    builder.add_conditional_edges("aggregate_impacts", dispatch_scenario_branches_route, ["scenario_branch_worker"])
    builder.add_edge("scenario_branch_worker", "generate_recommendation")
    builder.add_edge("aggregate_impacts", "generate_recommendation")
    builder.add_edge("generate_recommendation", "format_response")
    builder.add_edge("format_response", END)

    return builder.compile()


agent = build_graph()


def run_simulation(
    query: str,
    structured_data: dict[str, Any] | None = None,
    documents: list[str] | None = None,
    business_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # Normalize optional inputs so every node can read predictable shapes.
    initial_state: SimulatorState = {
        "query": query,
        "structured_data": structured_data or {},
        "documents": documents or [],
        "business_context": business_context or {},
        "persona_results": [],
        "persona_stream_events": [],
        "scenario_branches": [],
    }
    return agent.invoke(initial_state)
