"""Web search connector — self-hosted SearXNG."""

import os

import requests

from backend.connectors.base import BaseConnector

from .manifest import manifest

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8888")


class SearchConnector(BaseConnector):
    manifest = manifest

    def web_search(self, query: str, categories: str | list[str] | None = None, language: str = "de", limit: int = 10) -> dict:
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
                timeout=self.manifest.runtime.timeout_s,
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

            return self.ok({
                "query": query,
                "results": results,
                "total_results": data.get("number_of_results", 0),
            })
        except requests.exceptions.ConnectionError:
            return self.err("Search backend unavailable.")
        except Exception as e:
            return self.err(e)
