import asyncio
import sys
import os
import traceback
from pathlib import Path

# Add current directory to path
sys.path.append(os.getcwd())

from services.local_knowledge_service import LocalKnowledgeService
from agents.hr_agent import HRAgent
from agents.sales_agent import SalesAgent
from agents.manager_agent import ManagerAgent

async def smoke_test():
    try:
        print("Initializing services and agents...")
        knowledge_service = LocalKnowledgeService()
        hr_agent = HRAgent(knowledge_service)
        sales_agent = SalesAgent(knowledge_service)
        manager = ManagerAgent([hr_agent, sales_agent])

        print("Creating decision case and orchestrating...")
        sample_query = "Should we hire a new salesperson?"
        # The prompt mentioned target_id, but the method takes query and context
        # I'll put target_id into the context
        context = {"target_id": "test_target_001"}
        
        result = await manager.orchestrate(sample_query, context)
        
        case_id = result.get('case_id', 'N/A')
        recommendation = result.get('recommendation', 'N/A')

        print(f"Success! Case ID: {case_id}")
        print(f"Recommendation: {recommendation}")
        return True
    except Exception as e:
        print("Smoke test failed!")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = asyncio.run(smoke_test())
    sys.exit(0 if success else 1)
