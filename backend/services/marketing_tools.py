from typing import Type, Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from services.tavily_service import TavilyService
from services.newsdata_service import NewsDataService
import asyncio

class TavilySearchInput(BaseModel):
    query: str = Field(description="Search query for market trends, competitors, or sentiment")

class TavilySearchTool(BaseTool):
    name: str = "tavily_search"
    description: str = "Search the web for real-time market intelligence, competitor data, and industry trends."
    args_schema: Type[BaseModel] = TavilySearchInput
    service: TavilyService = Field(default_factory=TavilyService)

    def _run(self, query: str):
        # Sync wrapper if needed, but we prefer async
        return asyncio.run(self._arun(query))

    async def _arun(self, query: str):
        return await self.service.search(query, max_results=3)

class NewsDataInput(BaseModel):
    query: str = Field(description="Search query for latest news articles")

class NewsDataTool(BaseTool):
    name: str = "newsdata_search"
    description: str = "Search latest news articles and headlines for sentiment and current events."
    args_schema: Type[BaseModel] = NewsDataInput
    service: NewsDataService = Field(default_factory=NewsDataService)

    def _run(self, query: str):
        return asyncio.run(self._arun(query))

    async def _arun(self, query: str):
        return await self.service.get_latest_news(query)
