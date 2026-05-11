import os
import httpx
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class TavilyService:
    """
    Service to interact with Tavily Search API for competitor and market research.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.base_url = "https://api.tavily.com/search"

    async def search(self, query: str, search_depth: str = "basic", max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Perform a search using Tavily.
        """
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not set. Skipping search.")
            return []

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "include_answer": True,
            "include_raw_content": False,
            "max_results": max_results,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.base_url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                # Add the 'answer' if provided by Tavily as a separate entry or context
                answer = data.get("answer")
                if answer:
                    results.insert(0, {
                        "title": "Tavily AI Summary",
                        "content": answer,
                        "url": "https://tavily.com",
                        "score": 1.0
                    })
                
                return results
            except Exception as e:
                logger.error(f"Tavily search failed: {str(e)}")
                return []

    async def search_competitors(self, product_context: str) -> List[Dict[str, Any]]:
        """
        Specifically search for competitors based on product/document context.
        """
        query = f"top competitors and market alternatives for: {product_context}"
        return await self.search(query)
