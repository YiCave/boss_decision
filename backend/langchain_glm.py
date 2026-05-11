"""
LangChain + ZhipuAI GLM integration.
Provides LangChain-style chains and agents using GLM models.
"""
from langchain_community.chat_models import ChatZhipuAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain.chains import LLMChain
from pydantic import BaseModel, Field
from typing import List
from config import get_settings


def get_glm_langchain():
    """Get LangChain ChatZhipuAI instance."""
    settings = get_settings()
    return ChatZhipuAI(
        api_key=settings.zhipuai_api_key,
        model=settings.glm_model,
        temperature=settings.glm_temperature
    )


# ============================================
# Structured Output Models (for agents)
# ============================================

class AgentAnalysis(BaseModel):
    """Structured output for agent analysis."""
    findings: List[str] = Field(description="List of key findings (2-4 items)")
    risks: List[str] = Field(description="List of identified risks (1-3 items)")
    recommendation: str = Field(description="Clear, actionable recommendation (1-2 sentences)")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0", ge=0.0, le=1.0)


class ManagerDecision(BaseModel):
    """Structured output for manager decision."""
    recommendation: str = Field(description="Final decision recommendation")
    risk_level: str = Field(description="Risk level: Low, Medium, or High")
    confidence_score: float = Field(description="Confidence percentage 0-100", ge=0, le=100)
    rationale: str = Field(description="Detailed rationale for the decision")
    conservative_view: str = Field(description="Conservative perspective on the decision")
    aggressive_view: str = Field(description="Aggressive perspective on the decision")


# ============================================
# LangChain Chains for Agents
# ============================================

class HRAgentChain:
    """LangChain-powered HR Agent."""
    
    def __init__(self):
        self.llm = get_glm_langchain()
        self.parser = PydanticOutputParser(pydantic_object=AgentAnalysis)
        
        # Create prompt template
        system_template = """You are an HR specialist agent analyzing employee performance data.

Your task:
1. Analyze performance trends (improving/declining/stable)
2. Identify legal and compliance risks
3. Consider company policies (PIP requirements, termination procedures)
4. Provide clear, actionable recommendations

Be objective, fact-based, and focus on performance trends.

{format_instructions}
"""
        
        human_template = """Performance Data:
{hr_data}

Question: {query}

Provide your analysis:"""
        
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ])
        
        # Create chain
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            output_parser=self.parser
        )
    
    async def analyze(self, hr_data: str, query: str) -> AgentAnalysis:
        """
        Analyze HR data using LangChain.
        
        Args:
            hr_data: Formatted HR records as string
            query: Decision query
        
        Returns:
            AgentAnalysis with structured output
        """
        result = await self.chain.ainvoke({
            "hr_data": hr_data,
            "query": query,
            "format_instructions": self.parser.get_format_instructions()
        })
        
        return result['text']


class SalesAgentChain:
    """LangChain-powered Sales Agent."""
    
    def __init__(self):
        self.llm = get_glm_langchain()
        self.parser = PydanticOutputParser(pydantic_object=AgentAnalysis)
        
        system_template = """You are a Sales performance analyst.

Your task:
1. Analyze revenue trends and contribution
2. Compare performance against team benchmarks (good performers: RM 200k+ per quarter)
3. Assess pipeline health (active deals vs lost deals)
4. Identify revenue risks and opportunities

Be specific with numbers and percentiles.

{format_instructions}
"""
        
        human_template = """Sales Data:
{sales_data}

Question: {query}

Provide your analysis:"""
        
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ])
        
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            output_parser=self.parser
        )
    
    async def analyze(self, sales_data: str, query: str) -> AgentAnalysis:
        """Analyze sales data using LangChain."""
        result = await self.chain.ainvoke({
            "sales_data": sales_data,
            "query": query,
            "format_instructions": self.parser.get_format_instructions()
        })
        
        return result['text']


class ManagerDecisionChain:
    """LangChain-powered Manager Decision Synthesis."""
    
    def __init__(self, persona: str = 'balanced'):
        """
        Initialize manager chain with persona.
        
        Args:
            persona: 'conservative', 'balanced', or 'aggressive'
        """
        self.llm = get_glm_langchain()
        self.parser = PydanticOutputParser(pydantic_object=ManagerDecision)
        self.persona = persona
        
        persona_instructions = {
            'conservative': """Apply CONSERVATIVE decision-making:
- Prioritize risk mitigation over speed
- Consider legal compliance carefully
- Factor in replacement costs and transition periods
- Prefer phased approaches over immediate action
- When in doubt, choose the safer path""",
            
            'aggressive': """Apply AGGRESSIVE decision-making:
- Prioritize speed and decisiveness
- Consider opportunity cost of delay
- Focus on team morale and performance impact
- Accept calculated risks for better outcomes
- When in doubt, choose the bolder path""",
            
            'balanced': """Apply BALANCED decision-making:
- Weigh all perspectives equally
- Consider both short-term and long-term impacts
- Balance risk with opportunity
- Look for middle-ground solutions
- When in doubt, choose the most reasonable path"""
        }
        
        system_template = f"""You are a Manager Decision Agent synthesizing insights from specialist agents.

Your role:
- Review all agent recommendations objectively
- Identify consensus and conflicts
- Apply the {persona.upper()} decision-making persona
- Produce a clear, actionable final decision

{persona_instructions[persona]}

{{format_instructions}}
"""
        
        human_template = """Decision Query: {query}

Agent Insights:
{agent_insights}

Synthesize these insights into a final decision using the {persona} persona."""
        
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ])
        
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            output_parser=self.parser
        )
    
    async def synthesize(self, query: str, agent_insights: str) -> ManagerDecision:
        """
        Synthesize agent insights into final decision.
        
        Args:
            query: Original decision query
            agent_insights: Formatted string of all agent outputs
        
        Returns:
            ManagerDecision with structured output
        """
        result = await self.chain.ainvoke({
            "query": query,
            "agent_insights": agent_insights,
            "persona": self.persona,
            "format_instructions": self.parser.get_format_instructions()
        })
        
        return result['text']


# ============================================
# Example Usage
# ============================================

async def example_hr_agent_usage():
    """Example of using HR Agent with LangChain + GLM."""
    
    # Initialize chain
    hr_chain = HRAgentChain()
    
    # Prepare data
    hr_data = """
Period: 2025-Q3
Score: 2.8/5.0
Attendance: 62 days (absent: 3)
Warnings: 0
Summary: Performance below expectations. Missed sales target by 45%.

Period: 2025-Q4
Score: 2.1/5.0
Attendance: 58 days (absent: 7)
Warnings: 1
Summary: Declining performance. Zero deals closed. Multiple complaints.

Period: 2026-Q1
Score: 2.0/5.0
Attendance: 61 days (absent: 4)
Warnings: 2
PIP Status: Recommended but not initiated
Summary: No improvement. PIP required before termination per policy.
"""
    
    query = "Should we terminate this employee for performance reasons?"
    
    # Get analysis
    result = await hr_chain.analyze(hr_data, query)
    
    print("HR Agent Analysis (LangChain + GLM):")
    print(f"Findings: {result.findings}")
    print(f"Risks: {result.risks}")
    print(f"Recommendation: {result.recommendation}")
    print(f"Confidence: {result.confidence * 100:.0f}%")
    
    return result


async def example_manager_synthesis():
    """Example of using Manager Agent with LangChain + GLM."""
    
    # Initialize chain with conservative persona
    manager_chain = ManagerDecisionChain(persona='conservative')
    
    # Prepare agent insights
    agent_insights = """
**HR Agent:**
Findings: Performance declining from 2.8 to 2.0, 2 warnings issued
Risks: PIP not initiated - required by policy before termination
Recommendation: Initiate 60-day PIP before considering termination
Confidence: 90%

**Sales Agent:**
Findings: Total revenue RM 39,400 across 3 quarters, bottom 8% of team
Risks: Pipeline thin (1 active deal), revenue impact minimal
Recommendation: Performance below team standards
Confidence: 88%

**Legal Agent:**
Findings: Termination policy requires PIP completion
Risks: Wrongful termination claim if PIP skipped, severance RM 20k minimum
Recommendation: PIP mandatory per company policy
Confidence: 95%

**Finance Agent:**
Findings: Total termination cost RM 77k (severance + replacement + onboarding)
Risks: Break-even after 7.3 months, 3-month productivity gap
Recommendation: Replacement cost high relative to savings
Confidence: 85%
"""
    
    query = "Should we terminate employee John Tan (ID 1023)?"
    
    # Get decision
    result = await manager_chain.synthesize(query, agent_insights)
    
    print("\nManager Decision (LangChain + GLM):")
    print(f"Recommendation: {result.recommendation}")
    print(f"Risk Level: {result.risk_level}")
    print(f"Confidence: {result.confidence_score:.0f}%")
    print(f"\nRationale:\n{result.rationale}")
    print(f"\nConservative View: {result.conservative_view}")
    print(f"Aggressive View: {result.aggressive_view}")
    
    return result


# ============================================
# Run Examples
# ============================================

if __name__ == "__main__":
    import asyncio
    
    print("=" * 60)
    print("LangChain + ZhipuAI GLM Integration Examples")
    print("=" * 60)
    
    # Run HR agent example
    asyncio.run(example_hr_agent_usage())
    
    print("\n" + "=" * 60 + "\n")
    
    # Run manager synthesis example
    asyncio.run(example_manager_synthesis())
