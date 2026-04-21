"""Manifest for the web search connector (SearXNG)."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="search",
    version=1,
    enabled=True,
    category="utility",
    pod="app",

    source=Source(
        name="SearXNG (self-hosted)",
        type="internal",
        url="internal",
        refresh="realtime",
    ),

    runtime=Runtime(
        env=["SEARXNG_URL"],
        timeout_s=10,
        cache_ttl_s=60,
    ),

    tools=[
        Tool(
            name="web_search",
            handler="web_search",
            description="Search the web for information using SearXNG. Use this when other tools don't cover the topic.",
            retrieval=Retrieval(
                summary=(
                    "Fallback web search via the self-hosted SearXNG meta-search "
                    "engine. Use only when no other structured Zürich connector "
                    "covers the topic — for example breaking news, global "
                    "information, or long-tail questions."
                ),
                example_queries=[
                    "Aktuelle Schlagzeilen Schweiz",
                    "Wer het de Nobelpris für Physik 2024?",
                    "Latest news about Zurich Airport",
                    "Rezept für Zürcher Geschnetzeltes",
                    "What is the current exchange rate CHF to EUR?",
                ],
                keywords=[
                    "search", "suche", "web", "google", "searxng", "news",
                    "information", "internet", "recherche",
                ],
                not_for=[
                    "real-time Zürich public data already covered by other tools",
                    "private or intranet content",
                    "tasks requiring structured data (weather, transit, etc.)",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - pass the user's question directly",
                    },
                    "categories": {
                        "type": "string",
                        "description": "Optional category: general, news, images, videos, it, science, files, social media",
                        "default": "",
                    },
                    "language": {
                        "type": "string",
                        "description": "Language code: de, en, fr, it",
                        "default": "de",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
    ],
)
