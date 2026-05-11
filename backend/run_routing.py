import asyncio
import json
from agents import (
    HRAgent,
    SalesAgent,
    LegalAgent,
    FinanceAgent,
    MarketingAgent,
    SupplyChainAgent,
    ManagerAgent,
)
from services.local_knowledge_service import LocalKnowledgeService

async def main():
    knowledge = LocalKnowledgeService()
    agents = [
        HRAgent(knowledge),
        SalesAgent(knowledge),
        LegalAgent(knowledge),
        FinanceAgent(knowledge),
        MarketingAgent(knowledge),
        SupplyChainAgent(knowledge),
    ]
    manager = ManagerAgent(agents)
    
    query = "Should we terminate employee 102 now or run PIP first?"
    context = {
        "target_type": "employee",
        "target_id": 102,
        "context": "repeated KPI misses across two quarters",
        "submitted_by": "direct-execution",
        "document_path": "./workplaces/documents/hr_termination_case_employee_102.md",
    }
    
    result = await manager.orchestrate_dynamic(query=query, context=context)
    print("ROUTING_START")
    print(json.dumps(result.get("routing", {}), indent=2))
    print("ROUTING_END")

if __name__ == "__main__":
    asyncio.run(main())
