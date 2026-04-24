import json

from src import agent as agent_module
from src import nodes as node_module


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeModel:
    def __init__(self, content):
        self._content = content

    def invoke(self, _prompt):
        return FakeResponse(self._content)


def test_generate_recommendation_uses_fallback_when_model_unavailable(monkeypatch):
    monkeypatch.setattr(node_module, "get_recommendation_model", lambda: None)

    result = node_module.generate_recommendation_node(
        {
            "aggregated_impacts": {
                "weighted_revenue_pct": 2.0,
                "risk_count": 1,
                "opportunity_count": 2,
            },
            "scenario_branches": [
                {"branch_name": "optimistic", "revenue_pct": 4.0, "risk_level": "low", "summary": "upside"},
                {"branch_name": "base", "revenue_pct": 2.0, "risk_level": "low", "summary": "base"},
                {"branch_name": "pessimistic", "revenue_pct": 0.5, "risk_level": "medium", "summary": "downside"},
            ],
        }
    )

    assert result["recommendation"] == "Proceed with a controlled rollout and weekly KPI checkpoints."
    assert result["recommendation_details"]["assumptions"]


def test_parse_decision_fallback_on_invalid_json(monkeypatch):
    monkeypatch.setattr(node_module, "_parse_with_llm", lambda _query: None)

    result = node_module.parse_decision_node({"query": "Lower price by 5% for enterprise users in 2 months"})

    assert result["decision"]["decision_type"] == "price_decrease"
    assert result["decision"]["delta_value"] == 5.0
    assert result["decision"]["delta_unit"] == "percent"
    assert result["decision"]["time_horizon"] == "in 2 months"


def test_select_personas_uses_llm_defined_dynamic_personas(monkeypatch):
    monkeypatch.setattr(
        node_module,
        "get_selector_model",
        lambda: FakeModel(
            json.dumps(
                {
                    "selected_personas": [
                        {
                            "id": "pricing_strategist",
                            "name": "Pricing Strategist",
                            "role": "pricing decision evaluator",
                            "focus": "elasticity, margins, and willingness to pay",
                            "system_prompt": "You are a pricing strategist focused on elasticity and margin tradeoffs.",
                            "tools": [],
                            "temperature": 0.2,
                            "expected_outputs": ["kpi_deltas", "risks", "opportunities", "rationale"],
                        },
                        {
                            "id": "enterprise_account_lead",
                            "name": "Enterprise Account Lead",
                            "role": "enterprise buyer evaluator",
                            "focus": "deal friction, renewal risk, and procurement response",
                            "system_prompt": "You evaluate enterprise buyer reactions and procurement friction.",
                            "tools": [],
                            "temperature": 0.3,
                            "expected_outputs": ["kpi_deltas", "risks", "opportunities", "rationale"],
                        },
                    ]
                }
            )
        ),
    )

    result = node_module.select_personas_node(
        {
            "query": "Increase enterprise pricing by 10% and evaluate buyer response",
            "decision": {
                "decision_type": "price_increase",
                "target_segments": ["enterprise"],
            },
            "documents": [],
            "structured_data": {"recent_win_rate": [0.42]},
            "business_context": {"go_to_market": "sales-led enterprise"},
            "scenario": {"query": "Increase enterprise pricing by 10% and evaluate buyer response"},
        }
    )

    personas = result["selected_personas"]

    assert personas[0]["id"] == "pricing_strategist"
    assert personas[0]["role"] == "pricing decision evaluator"
    assert personas[1]["id"] == "enterprise_account_lead"
    assert personas[1]["system_prompt"]
    assert personas[1]["expected_outputs"] == ["kpi_deltas", "risks", "opportunities", "rationale"]


def test_select_personas_falls_back_when_selector_model_unavailable(monkeypatch):
    monkeypatch.setattr(node_module, "get_selector_model", lambda: None)

    result = node_module.select_personas_node(
        {
            "query": "Launch a new product for student users",
            "decision": {
                "decision_type": "product_launch",
                "target_segments": ["student"],
            },
            "scenario": {"query": "Launch a new product for student users"},
        }
    )

    personas = result["selected_personas"]

    assert len(personas) >= 2
    assert all("system_prompt" in persona for persona in personas)
    assert all("role" in persona for persona in personas)


def test_langgraph_simulation_flow(monkeypatch):
    monkeypatch.setattr(
        node_module,
        "_parse_with_llm",
        lambda _query: {
            "decision_type": "price_increase",
            "delta_value": 10,
            "delta_unit": "percent",
            "time_horizon": "next quarter",
            "target_segments": ["student"],
            "confidence": 0.91,
            "assumptions": ["Demand remains stable"],
        },
    )
    monkeypatch.setattr(
        node_module,
        "_run_persona_subagent",
        lambda _persona, _scenario: {
            "persona_id": "finance_lead",
            "confidence": 0.9,
            "kpi_deltas": {"revenue_pct": 3.0},
            "risks": ["churn spike"],
            "opportunities": ["margin expansion"],
            "rationale": "Price lift likely improves margin.",
        },
    )

    out = agent_module.run_simulation("Increase prices by 10% for student segment next quarter")

    assert out["decision"]["decision_type"] == "price_increase"
    assert out["scenario"]["decision"]["delta_value"] == 10.0
    assert out["aggregated_impacts"]["total_personas"] == 3
    assert len(out["scenario_branches"]) == 3
    assert out["response"]["scenario_branches"][0]["branch_name"] in {"optimistic", "base", "pessimistic"}
    assert "recommendation_details" in out["response"]
    assert "recommendation" in out["response"]


def test_aggregate_impacts_rolls_up_multiple_kpis_and_ranks_signals():
    result = node_module.aggregate_impacts_node(
        {
            "persona_results": [
                {
                    "persona_id": "finance_lead",
                    "confidence": 0.9,
                    "kpi_deltas": {"revenue_pct": 3.0, "conversion_pct": 1.0, "churn_pct": -0.5},
                    "risks": ["churn spike", "brand confusion"],
                    "opportunities": ["margin expansion"],
                },
                {
                    "persona_id": "customer_advocate",
                    "confidence": 0.6,
                    "kpi_deltas": {"revenue_pct": 1.0, "conversion_pct": 2.0, "churn_pct": -1.5},
                    "risks": ["churn spike"],
                    "opportunities": ["margin expansion", "segment growth"],
                },
            ]
        }
    )

    impacts = result["aggregated_impacts"]

    assert round(impacts["weighted_revenue_pct"], 2) == 2.2
    assert round(impacts["kpi_rollup"]["conversion_pct"], 2) == 1.4
    assert round(impacts["kpi_rollup"]["churn_pct"], 2) == -0.9
    assert impacts["top_risks"][0] == "churn spike"
    assert impacts["top_opportunities"][0] == "margin expansion"


def test_format_response_uses_ranked_outputs_from_aggregation():
    result = node_module.format_response_node(
        {
            "aggregated_impacts": {
                "kpi_rollup": {"revenue_pct": 2.5, "conversion_pct": 1.2},
                "top_risks": ["churn spike", "brand confusion"],
                "top_opportunities": ["margin expansion", "segment growth"],
            },
            "persona_results": [],
            "scenario_branches": [],
            "recommendation": "Proceed cautiously.",
            "recommendation_details": {"summary": "Proceed cautiously."},
        }
    )

    response = result["response"]

    assert response["kpi_deltas"]["revenue_pct"] == 2.5
    assert response["ranked_risks"] == ["churn spike", "brand confusion"]
    assert response["ranked_opportunities"] == ["margin expansion", "segment growth"]
