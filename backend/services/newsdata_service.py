import os
import httpx
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class NewsDataService:
    """
    Service to interact with NewsData.io API for tracking news and competitor mentions.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("NEWSDATA_API_KEY")
        self.base_url = "https://newsdata.io/api/1/news"

    async def get_latest_news(self, query: str, language: str = "en") -> List[Dict[str, Any]]:
        """
        Fetch latest news articles based on a query.
        """
        if not self.api_key:
            logger.warning("NEWSDATA_API_KEY not set. Skipping news search.")
            return []

        params = {
            "apikey": self.api_key,
            "q": query,
            "language": language,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                
                # Format results consistently for the agent
                formatted_results = []
                for article in results:
                    formatted_results.append({
                        "title": article.get("title"),
                        "link": article.get("link"),
                        "description": article.get("description") or article.get("content", "")[:500],
                        "pubDate": article.get("pubDate"),
                        "source_id": article.get("source_id"),
                        "sentiment": article.get("sentiment") # Some plans include sentiment
                    })
                
                return formatted_results
            except Exception as e:
                logger.error(f"NewsData search failed: {str(e)}")
                return []

    async def search_competitor_news(self, competitors: List[str]) -> List[Dict[str, Any]]:
        """
        Search for news specifically about a list of competitors.
        """
        if not competitors:
            return []
        
        query = " OR ".join([f'"{c}"' for c in competitors[:5]])
        return await self.get_latest_news(query)
