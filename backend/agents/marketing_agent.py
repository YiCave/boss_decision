"""
Marketing Agent - Evaluates campaign performance and market messaging impact.
Uses LangChain: Supabase (company tables) + Tavily (web) + NewsData (news).
"""
import logging
import os
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent, AgentInsight
from services.marketing_tools import TavilySearchTool, NewsDataTool
from services.supabase_agent_tools import build_marketing_supabase_tools
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

logger = logging.getLogger(__name__)

class MarketingAgent(BaseAgent):
    def __init__(self, db_service, llm=None, company_db: Optional[Any] = None):
        """
        db_service: LocalKnowledgeService (or compatible) for file-based context.
        company_db: optional DatabaseService (Supabase) for marketing_record and shallow cross-table reads.
        """
        super().__init__(db_service, llm)
        self._company_db = company_db
        self.tools: List[Any] = []
        supabase_tools = build_marketing_supabase_tools(company_db)
        if supabase_tools:
            self.tools.extend(supabase_tools)
            logger.info("MarketingAgent: %d Supabase read tool(s) enabled", len(supabase_tools))
        self.tools.extend([TavilySearchTool(), NewsDataTool()])

        # Initialize LangChain LLM
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables. Please check your .env file.")

        self.lc_llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=api_key,
            temperature=0.3
        )

        # Setup Agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a proactive Marketing Performance Analyst. "
             "You have read-only access to the company's Supabase/PostgreSQL data when company_db is enabled.\n"
             "1) For performance, spend, channel, campaign, ROI, or internal metrics — call read_marketing_database FIRST "
             "(table marketing_record). For light org/finance/sales context, use read_supporting_company_data with a valid scope. "
             "Do NOT deep-dive HR, legal, or supply; use those only for quick cross-checks. Specialist agents own those domains.\n"
             "2) REVIEW the 'Internal Context' in the user message (file-based KB and uploads).\n"
             "3) Use tavily_search and newsdata_search for external benchmarks, competitors, and news — after or alongside internal data.\n"
             "4) Synthesize: do not refuse with 'no data' if you can combine internal rows + search results."),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(self.lc_llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True, handle_parsing_errors=True)

    async def retrieve_evidence(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        In LangChain mode, tools are called during the agent run.
        We still pull internal KB documents as initial context.
        """
        evidence: List[Dict[str, Any]] = []

        # 1. Internal knowledge-base documents
        try:
            docs = await self.db.get_department_documents("marketing")
            if docs:
                evidence.extend(docs)
                logger.info("MarketingAgent: loaded %d internal KB documents", len(docs))
        except Exception as exc:
            logger.warning("MarketingAgent: failed to load internal KB documents: %s", exc)

        # 2. Uploaded document context
        doc_summary = context.get("document_summary")
        if doc_summary:
            evidence.append({
                "source": "uploaded_document",
                "summary": doc_summary,
                "department": context.get("document_department", "unknown"),
            })
        
        return evidence

    async def analyze(self, evidence: List[Dict[str, Any]], query: str) -> AgentInsight:
        """
        Run the LangChain agent to get insights using tools.
        """
        # Build initial context from evidence
        context_str = "\n".join([f"[{e.get('source')}]: {e.get('summary')}" for e in evidence])
        
        full_input = f"Query: {query}\n\nInternal Context:\n{context_str}\n\nPlease analyze and provide marketing insights."
        
        logger.info("\n[MarketingAgent] Executing LangChain agent for query: %s", query)
        try:
            # Note: LangChain's ainvoke is used for async execution
            response = await self.agent_executor.ainvoke({"input": full_input})
            output = response.get("output", "No output from agent.")
            logger.info("[MarketingAgent] LangChain execution completed.")
        except Exception as exc:
            logger.error(f"MarketingAgent LangChain execution failed: {exc}")
            output = f"Analysis failed: {str(exc)}"
            logger.error(f"[MarketingAgent] LangChain execution failed: {exc}")

        # We still need to return an AgentInsight object
        # We'll use our _llm_client to structure the final output from the LangChain agent's result
        
        return await self._llm_analyze(
            query=query,
            evidence_summary=output,
            domain_role="marketing performance and campaign strategy analyst",
            domain_focus="Campaign ROI, audience segmentation, competitor benchmarking, and market trends.",
            fallback_insight=AgentInsight(
                agent_name="Marketing",
                findings=[output[:200]] if output else ["No findings."],
                risks=["Analysis limited by execution error"] if not output else ["Risk identified during search."],
                recommendation="Review terminal logs for details" if not output else "Proceed with recommended strategy.",
                confidence=0.5,
                evidence_used=evidence
            )
        )
