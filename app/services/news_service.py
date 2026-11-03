import re
import logging
import requests
from typing import Dict, Any, List, Optional
from app.config import NEWSAPI_KEY

logger = logging.getLogger(__name__)

STOPWORDS = {
    "what", "happened", "between", "was", "were", "is", "are", "tell", "me", "about",
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "did", "do",
    "does", "why", "how", "when", "where", "who", "which", "there", "any", "please",
    "explain", "can", "you", "know", "news", "latest", "update", "updates"
}

class NewsService:
    def __init__(self, api_key: Optional[str] = None):
        key = api_key or NEWSAPI_KEY
        if not key:
            raise ValueError("NEWSAPI_KEY is not set.")
        self.api_key = key
        self.base_url = "https://newsapi.org/v2"

    def extract_keywords(self, text: str) -> List[str]:
        """Extract key topical words/phrases from a conversational query."""
        # Find quoted phrases first if any
        quotes = re.findall(r'"([^"]+)"', text)
        cleaned = re.sub(r'[^\w\s]', ' ', text)
        words = cleaned.split()
        keywords = [w for w in words if w.lower() not in STOPWORDS and len(w) > 1]
        
        # Combine quotes and top keywords
        result = list(quotes)
        for kw in keywords:
            if kw not in result:
                result.append(kw)
        return result

    def search_news(
        self,
        query: str,
        keywords: Optional[List[str]] = None,
        page_size: int = 8,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Search news articles using NewsAPI based on the Sarvam LLM's query and keywords.
        """
        active_keywords = keywords if keywords and len(keywords) > 0 else self.extract_keywords(query)
        primary_query = query.strip()
        
        logger.info(f"LLM search query: '{primary_query}', Keywords: {active_keywords}")

        # Attempt 1: Search with LLM query
        articles = self._fetch_everything(primary_query, page_size=page_size, language=language)

        query_used = primary_query
        fallback_used = False

        # Attempt 2: If no articles found, search with keywords joined
        if not articles and active_keywords:
            kw_query = " ".join([f'"{k}"' if " " in k else k for k in active_keywords[:4]])
            logger.info(f"Keywords search query: '{kw_query}'")
            articles = self._fetch_everything(kw_query, page_size=page_size, language=language)
            if articles:
                query_used = kw_query
                fallback_used = True

        # Attempt 3: If no articles found, fallback to OR query
        if not articles and len(active_keywords) > 1:
            fallback_query = " OR ".join([f'"{k}"' if " " in k else k for k in active_keywords[:3]])
            logger.info(f"Fallback OR search query: '{fallback_query}'")
            articles = self._fetch_everything(fallback_query, page_size=page_size, language=language)
            if articles:
                query_used = fallback_query
                fallback_used = True

        # Attempt 4: If still nothing, search individual key terms
        if not articles and active_keywords:
            for kw in active_keywords[:2]:
                articles = self._fetch_everything(kw, page_size=page_size, language=language)
                if articles:
                    query_used = kw
                    fallback_used = True
                    break

        # Attempt 5: Last resort, top headlines
        if not articles:
            articles = self._fetch_top_headlines(page_size=page_size)
            query_used = "top-headlines"
            fallback_used = True

        formatted_articles = []
        for idx, art in enumerate(articles, start=1):
            source_name = art.get("source", {}).get("name", "Unknown Source")
            formatted_articles.append({
                "id": f"art_{idx}",
                "index": idx,
                "title": art.get("title") or "Untitled",
                "source": source_name,
                "author": art.get("author") or "Unknown Author",
                "description": art.get("description") or "",
                "url": art.get("url") or "#",
                "published_at": art.get("publishedAt") or "",
                "content": art.get("content") or art.get("description") or ""
            })

        return {
            "query_used": query_used,
            "original_query": query,
            "extracted_keywords": active_keywords,
            "total_found": len(formatted_articles),
            "fallback_used": fallback_used,
            "articles": formatted_articles
        }

    def _fetch_everything(self, query: str, page_size: int = 8, language: str = "en") -> List[Dict[str, Any]]:
        try:
            params = {
                "q": query,
                "pageSize": page_size,
                "sortBy": "relevancy",
                "apiKey": self.api_key
            }
            if language:
                params["language"] = language
                
            resp = requests.get(f"{self.base_url}/everything", params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("articles", [])
            else:
                logger.warning(f"NewsAPI error ({resp.status_code}): {resp.text}")
                return []
        except Exception as e:
            logger.error(f"NewsAPI fetch exception: {e}")
            return []

    def _fetch_top_headlines(self, page_size: int = 5) -> List[Dict[str, Any]]:
        try:
            params = {
                "category": "technology",
                "pageSize": page_size,
                "apiKey": self.api_key
            }
            resp = requests.get(f"{self.base_url}/top-headlines", params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("articles", [])
            return []
        except Exception as e:
            logger.error(f"Top headlines fetch error: {e}")
            return []

news_service = NewsService()
