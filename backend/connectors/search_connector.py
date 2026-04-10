"""
Web Search Connector
- Uses self-hosted SearXNG for sovereign web search
"""

import requests
import os

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8888")


def search(query, categories=None, language="de", limit=10):
    """Search the web using SearXNG.
    
    Args:
        query: Search query string (pass user input directly)
        categories: Optional categories filter (general, news, images, videos, it, science, files, social media)
        language: Language code (de, en, fr, it)
        limit: Max number of results
    """
    try:
        params = {
            "q": query,
            "format": "json",
            "language": language,
        }
        
        if categories:
            if isinstance(categories, str):
                categories = [categories]
            params["categories"] = ",".join(categories)
        
        resp = requests.get(
            f"{SEARXNG_URL}/search",
            params=params,
            timeout=10,
            headers={"User-Agent": "ZuriBot/1.0", "Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        
        results = []
        for item in data.get("results", [])[:limit]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "engine": item.get("engine", ""),
                "engines": item.get("engines", []),
                "category": item.get("category", "general"),
                "score": item.get("score", 0),
                "publishedDate": item.get("publishedDate"),
            })
        
        return {
            "success": True,
            "data": {
                "query": query,
                "results": results,
                "total_results": data.get("number_of_results", 0),
            },
            "source": {"name": "SearXNG", "type": "self-hosted"},
            "error": None,
        }
    except requests.exceptions.ConnectionError:
        return {"success": False, "data": None, "source": {"name": "SearXNG", "type": "self-hosted"}, "error": "SearXNG is not running. Start it with: docker start searxng"}
    except Exception as e:
        return {"success": False, "data": None, "source": {"name": "SearXNG", "type": "self-hosted"}, "error": str(e)}