"""
Terminal validator for ManagerAgent dynamic routing.

Usage:
  python validate_manager_routing.py

What it validates:
- Manager can route based on free-text input.
- Manager can incorporate optional document/image extraction via DocumentIngestor.
- Manager can route to one or more real subagents and produce a manager TLDR.
"""
import asyncio
import json
from pathlib import Path

from agents import (
    HRAgent,
    SalesAgent,
    LegalAgent,
    FinanceAgent,
    MarketingAgent,
    SupplyChainAgent,
    ManagerAgent,
)
from services.document_service import DocumentIngestor
from services.local_knowledge_service import LocalKnowledgeService


def _try_extract_document(file_path: str | None) -> dict:
    if not file_path:
        return {}

    path = Path(file_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        print(f"[WARN] File not found: {path}")
        return {}

    try:
        ingestor = DocumentIngestor()
        extracted = ingestor.process(str(path))
        print("[INFO] Document extraction completed.")
        print(json.dumps(extracted, indent=2))
        return extracted
    except Exception as exc:
        print(f"[WARN] Document extraction failed: {exc}")
        return {}


async def _run_once(manager: ManagerAgent):
    print("\n=== Manager Routing Validation ===")
    query = input("Enter your business question (or 'exit'): ").strip()
    if query.lower() in {"exit", "quit", "q"}:
        return False

    file_path = input("Optional file path (image/doc/md), press Enter to skip: ").strip()
    extracted = await DocumentIngestor().aprocess(file_path) if file_path else {}

    context = {
        "target_type": input("Optional target_type (e.g., employee), Enter to skip: ").strip() or None,
        "target_id": None,
        "context": input("Optional additional context, Enter to skip: ").strip() or None,
        "submitted_by": "terminal-validator",
        "document_path": file_path if file_path else None,
        "document_department": extracted.get("department"),
        "document_summary": extracted.get("summary"),
        "document_entities": extracted.get("entities", []),
        "document_tags": extracted.get("tags", []),
    }

    target_id_raw = input("Optional target_id (integer), Enter to skip: ").strip()
    if target_id_raw:
        try:
            context["target_id"] = int(target_id_raw)
        except ValueError:
            print("[WARN] target_id ignored (not an integer)")

    result = await manager.orchestrate_dynamic(query=query, context=context)

    routing = result.get("routing", {})
    selected = routing.get("selected_agents", [])
    route_source = routing.get("route_source")

    # Strict mode for valid chatbot routing verification.
    if route_source != "llm":
        print("\n[VALIDATION-FAIL] route_source is not 'llm'.")
        print("This run is not accepted for intelligent-routing validation.")
        if routing.get("route_error"):
            print(f"Router error: {routing.get('route_error')}")
        print(json.dumps(routing, indent=2))
        return True

    print("\n--- Routing Result ---")
    print(json.dumps(routing, indent=2))

    print("\n=== Group Chat Transcript ===")
    print(f"[User]: {query}")
    if extracted:
        print(
            "[Document Extractor]: "
            f"department={extracted.get('department')} | "
            f"summary={extracted.get('summary')}"
        )

    print(f"[Manager Router]: Selected agents -> {selected}")

    for insight in result.get("agent_insights", []):
        label = insight.get("agent_name", "Unknown")
        findings = insight.get("findings", [])
        top_finding = findings[0] if findings else "No finding"
        recommendation = insight.get("recommendation", "No recommendation")
        print(f"[{label} Agent]: {top_finding}")
        print(f"[{label} Agent]: Recommendation -> {recommendation}")

    decision = result.get("final_decision", {})
    print("\n--- Manager TLDR ---")
    print(
        "[Manager Agent]: "
        f"{decision.get('recommendation', 'No recommendation')} | "
        f"Risk={decision.get('risk_level', 'unknown')} | "
        f"Confidence={decision.get('confidence_score', 0)}"
    )

    return True


async def main():
    knowledge = LocalKnowledgeService()

    # Implemented agents
    hr_agent = HRAgent(knowledge)
    sales_agent = SalesAgent(knowledge)
    legal_agent = LegalAgent(knowledge)
    finance_agent = FinanceAgent(knowledge)
    marketing_agent = MarketingAgent(knowledge)
    supply_chain_agent = SupplyChainAgent(knowledge)

    manager = ManagerAgent([
        hr_agent,
        sales_agent,
        legal_agent,
        finance_agent,
        marketing_agent,
        supply_chain_agent,
    ])

    print("Manager routing validator started.")
    print("Type 'exit' as query to stop.")

    keep_running = True
    while keep_running:
        keep_running = await _run_once(manager)

    print("Validator stopped.")


if __name__ == "__main__":
    asyncio.run(main())

