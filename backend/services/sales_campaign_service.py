"""Sales campaign suggestor service powered by Tavily web search."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import re
from typing import Any
from urllib.parse import urlparse

import httpx

DEFAULT_PRODUCT_HINTS = [
    "Healthy snack box",
    "Hydration bottle",
    "Skincare starter kit",
    "Wireless earbuds",
    "Study desk lamp",
    "Productivity software subscription",
]

_STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "also",
    "among",
    "around",
    "because",
    "been",
    "being",
    "between",
    "could",
    "first",
    "from",
    "have",
    "into",
    "just",
    "latest",
    "many",
    "more",
    "most",
    "news",
    "next",
    "past",
    "recent",
    "said",
    "should",
    "since",
    "than",
    "that",
    "their",
    "there",
    "these",
    "they",
    "this",
    "those",
    "today",
    "trend",
    "trends",
    "using",
    "week",
    "weeks",
    "what",
    "when",
    "where",
    "which",
    "while",
    "will",
    "with",
    "would",
    "your",
}


class SalesCampaignService:
    """Searches for product news and creates practical weekly campaign suggestions."""

    def __init__(self, tavily_api_key: str):
        self._api_key = tavily_api_key

    async def suggest_campaigns(self, product: str, region: str = "Malaysia") -> dict[str, Any]:
        clean_product = product.strip()
        clean_region = (region or "Malaysia").strip() or "Malaysia"

        search_query = (
            f"Latest 7 day consumer news, market trends, and campaign opportunities for "
            f"{clean_product} in {clean_region}"
        )

        raw_results = await self._search_tavily(search_query)
        news_signals = self._normalize_news_results(raw_results)
        suggestions = self._build_suggestions(clean_product, clean_region, news_signals)

        return {
            "product": clean_product,
            "region": clean_region,
            "search_query": search_query,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "hints": DEFAULT_PRODUCT_HINTS,
            "news_signals": news_signals,
            "suggestions": suggestions,
        }

    async def _search_tavily(self, query: str) -> list[dict[str, Any]]:
        endpoint = "https://api.tavily.com/search"
        payload = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": "advanced",
            "topic": "news",
            "max_results": 8,
            "include_answer": False,
            "include_raw_content": True,
        }

        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(endpoint, json=payload)

            if response.status_code >= 400:
                fallback_payload = {
                    "api_key": self._api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": 8,
                }
                fallback_response = await client.post(endpoint, json=fallback_payload)
                fallback_response.raise_for_status()
                fallback_data = fallback_response.json()
                return fallback_data.get("results", [])

            data = response.json()
            return data.get("results", [])

    def _normalize_news_results(self, raw_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []

        for item in raw_results:
            title = self._clean_text(str(item.get("title") or ""))
            url = str(item.get("url") or "").strip()
            content = self._clean_text(str(item.get("content") or item.get("raw_content") or ""))

            if not title and not content:
                continue

            signals.append(
                {
                    "title": title or "Untitled source",
                    "url": url,
                    "source": str(item.get("source") or self._source_from_url(url)),
                    "published_date": str(item.get("published_date") or item.get("publishedDate") or ""),
                    "summary": self._summarize_content(content or title),
                    "score": float(item.get("score") or 0.0),
                }
            )

            if len(signals) >= 6:
                break

        return signals

    def _build_suggestions(
        self,
        product: str,
        region: str,
        news_signals: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        keywords = self._extract_keywords(product, news_signals)
        top_keyword = keywords[0] if keywords else "consumer demand"
        second_keyword = keywords[1] if len(keywords) > 1 else "value"

        reference_titles = [signal["title"] for signal in news_signals[:3]]
        reference_summary = "; ".join(reference_titles) if reference_titles else "No dominant headline cluster detected"
        source_links = [signal["url"] for signal in news_signals[:3] if signal.get("url")]

        return [
            {
                "type": "campaign",
                "title": f"{product} Trend Hook Campaign",
                "objective": (
                    f"Position {product} around the rising topic '{top_keyword}' and capture high-intent traffic in {region}."
                ),
                "why_now": f"Recent signals: {reference_summary}",
                "channels": ["TikTok/Reels", "Meta ads", "Email"],
                "next_week_plan": [
                    {"day": 1, "action": f"Publish a short trend insight post connecting {product} with {top_keyword}."},
                    {"day": 2, "action": "Launch two ad creatives with distinct hooks and split budget 60/40."},
                    {"day": 3, "action": "Activate retargeting for viewers who watched at least 50% of the video."},
                    {"day": 4, "action": "Drop customer social proof content and answer objections in comments."},
                    {"day": 5, "action": "Run a 24-hour promo code to convert high-intent users."},
                    {"day": 6, "action": "Optimize ads by pausing low CTR creatives and increasing winning audiences."},
                    {"day": 7, "action": "Publish final weekend recap offer and push checkout urgency."},
                ],
                "success_metric": "CTR > 2.0%, landing conversion > 3.5%",
                "sources": source_links,
            },
            {
                "type": "event",
                "title": f"Live Demo Event: {product} in 30 Minutes",
                "objective": (
                    f"Use an interactive event to educate buyers on {second_keyword}-driven benefits and shorten decision time."
                ),
                "why_now": "News coverage shows buyers seeking practical proof before purchase.",
                "channels": ["Instagram Live", "YouTube Live", "WhatsApp community"],
                "next_week_plan": [
                    {"day": 1, "action": "Announce event date and collect registrations through a simple form."},
                    {"day": 2, "action": "Release teaser clips showing product outcomes in real scenarios."},
                    {"day": 3, "action": "Send reminder sequence and gather top audience questions."},
                    {"day": 4, "action": "Run the live demo event with Q&A and a limited event-only voucher."},
                    {"day": 5, "action": "Share replay highlights and testimonials from event attendees."},
                    {"day": 6, "action": "Call warm leads directly or via chat for assisted conversion."},
                    {"day": 7, "action": "Close event offer and move unconverted leads into nurture flow."},
                ],
                "success_metric": "Attendance rate > 35%, event-to-order conversion > 8%",
                "sources": source_links,
            },
            {
                "type": "campaign",
                "title": f"Weekend Bundle Sprint for {product}",
                "objective": "Increase one-week revenue by packaging urgency and add-on value.",
                "why_now": "Top headlines indicate short attention cycles and stronger conversion under limited-time framing.",
                "channels": ["Website banner", "SMS", "Affiliate creators"],
                "next_week_plan": [
                    {"day": 1, "action": "Create a bundle offer and define margin-safe discount boundaries."},
                    {"day": 2, "action": "Prepare landing page with FAQ, comparison chart, and trust badges."},
                    {"day": 3, "action": "Recruit 3-5 micro creators for same-week quick content drops."},
                    {"day": 4, "action": "Launch bundle sprint and display social proof above the fold."},
                    {"day": 5, "action": "Retarget cart abandoners with countdown and bonus add-on."},
                    {"day": 6, "action": "Push a final 12-hour reminder through email and SMS."},
                    {"day": 7, "action": "Review sprint metrics and keep the best-performing bundle variant."},
                ],
                "success_metric": "Average order value +12%, week-over-week sales +18%",
                "sources": source_links,
            },
        ]

    @staticmethod
    def _clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _summarize_content(text: str, max_length: int = 220) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 3].rstrip() + "..."

    @staticmethod
    def _source_from_url(url: str) -> str:
        if not url:
            return "Unknown source"
        parsed = urlparse(url)
        host = parsed.netloc.replace("www.", "")
        return host or "Unknown source"

    def _extract_keywords(self, product: str, news_signals: list[dict[str, Any]]) -> list[str]:
        corpus = " ".join(
            f"{signal.get('title', '')} {signal.get('summary', '')}" for signal in news_signals
        ).lower()

        tokens = re.findall(r"[a-zA-Z]{4,}", corpus)
        product_tokens = {token for token in re.findall(r"[a-zA-Z]{3,}", product.lower())}

        usable_tokens = [
            token
            for token in tokens
            if token not in _STOPWORDS and token not in product_tokens
        ]

        return [word for word, _ in Counter(usable_tokens).most_common(5)]
