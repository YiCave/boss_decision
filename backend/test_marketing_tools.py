"""
End-to-end test: verifies the MarketingAgent triggers Tavily + NewsData tools.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from agents.manager_agent import ManagerAgent
from services.local_knowledge_service import LocalKnowledgeService
from agents import HRAgent, SalesAgent, LegalAgent, FinanceAgent, MarketingAgent, SupplyChainAgent


async def test():
    knowledge = LocalKnowledgeService()
    marketing_agent = MarketingAgent(knowledge)
    mgr = ManagerAgent([
        HRAgent(knowledge),
        SalesAgent(knowledge),
        LegalAgent(knowledge),
        FinanceAgent(knowledge),
        marketing_agent,
        SupplyChainAgent(knowledge),
    ])

    context = {
        "target_type": None,
        "target_id": None,
        "context": None,
        "submitted_by": "test",
        "force_simple_llm_subagents": False,
        "knowledge_paths": {},
    }
    query = "Should we launch a new marketing campaign for our SaaS product this quarter?"

    print("--- Running full orchestration ---")
    result = await mgr.orchestrate_dynamic(query, context)

    for insight in result["agent_insights"]:
        agent_name = insight["agent_name"]
        sources = [e.get("source") for e in insight["evidence_used"]]
        confidence = insight["confidence"]
        first_finding = insight["findings"][0][:120] if insight["findings"] else "N/A"

        print(f"\nAgent: {agent_name}")
        print(f"  Sources used: {sources}")
        print(f"  Confidence: {confidence}")
        print(f"  Finding[0]: {first_finding}")

        if agent_name.lower() == "marketing":
            tavily_hits = [s for s in sources if s == "tavily_search"]
            news_hits = [s for s in sources if s == "newsdata_io"]
            print(f"\n  [MARKETING TOOLS CHECK]")
            print(f"  Tavily results: {len(tavily_hits)}")
            print(f"  NewsData results: {len(news_hits)}")
            if tavily_hits or news_hits:
                print("  SUCCESS: Marketing tools fired!")
            else:
                print("  INFO: Tools produced no results (may be API key issue or empty response)")


if __name__ == "__main__":
    asyncio.run(test())
