import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(os.getcwd())

from services.local_knowledge_service import LocalKnowledgeService
from agents.hr_agent import HRAgent
from agents.sales_agent import SalesAgent
from agents.marketing_agent import MarketingAgent
from agents.manager_agent import ManagerAgent

async def test_marketing_routing():
    print("Initializing services and agents...")
    knowledge_service = LocalKnowledgeService()
    hr_agent = HRAgent(knowledge_service)
    sales_agent = SalesAgent(knowledge_service)
    marketing_agent = MarketingAgent(knowledge_service)
    
    manager = ManagerAgent([hr_agent, sales_agent, marketing_agent])

    # Test query that should route to marketing
    query = "How to enhance my coffee business"
    context = {
        "force_simple_llm_subagents": False,
        "document_summary": "This is a report about increasing coffee sales and brand awareness."
    }
    
    print(f"Orchestrating query: {query}")
    result = await manager.orchestrate_dynamic(query, context)
    
    routing = result.get("routing", {})
    selected_agents = routing.get("selected_agents", [])
    print(f"Selected agents: {selected_agents}")
    
    insights = result.get("agent_insights", [])
    found_marketing = False
    for insight in insights:
        print(f"Agent: {insight.get('agent_name')}")
        if insight.get('agent_name') == "Marketing":
            found_marketing = True
            evidence = insight.get('evidence_used', [])
            sources = [e.get('source') for e in evidence]
            print(f"Evidence sources: {sources}")
            
            if "tavily_search" in sources or "newsdata_io" in sources:
                print("SUCCESS: Marketing tools WERE triggered!")
            else:
                print("FAILURE: Marketing tools were NOT triggered in evidence.")

    if "marketing" in selected_agents and found_marketing:
        print("PASS: Marketing agent was correctly selected and executed.")
    else:
        print("FAIL: Marketing agent was NOT selected or executed.")

if __name__ == '__main__':
    asyncio.run(test_marketing_routing())
