"""Manifest for the venues connector (zuerich.com)."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="venues",
    version=1,
    enabled=True,
    category="culture",
    pod="app",

    source=Source(
        name="zuerich.com (Zürich Tourism)",
        type="official",
        url="https://zuerich.com",
        refresh="daily",
    ),

    runtime=Runtime(
        timeout_s=15,
        cache_ttl_s=3600,
    ),

    tools=[
        Tool(
            name="get_venues",
            handler="get_venues",
            description="Get venues in Zürich: restaurants, bars, cafes, hotels, attractions, museums, activities, shopping, etc. from zuerich.com. Supports filtering by name — use name_filter when looking for a specific restaurant or venue by name.",
            retrieval=Retrieval(
                summary=(
                    "Curated venues in Zürich (restaurants, bars, cafes, hotels, "
                    "museums, attractions, shopping, activities) from Zürich "
                    "Tourism's open data. Use for recommendations by category or "
                    "to look up a specific venue by name."
                ),
                example_queries=[
                    "Guets italienisches Restaurant in Züri",
                    "Best cafes in Zurich",
                    "Kronenhalle opening hours",
                    "Museen am See",
                    "Shopping Bahnhofstrasse recommendations",
                    "Hotel near Hauptbahnhof",
                ],
                keywords=[
                    "restaurant", "bar", "cafe", "hotel", "museum", "attraction",
                    "venue", "tourism", "zuerich.com", "gastronomy", "shopping",
                    "sightseeing", "activities",
                ],
                not_for=[
                    "real-time table availability",
                    "private venues or home addresses",
                    "venues outside the city of Zürich",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category: gastronomy, american, asian, swiss, italian, french, mediterranean, steakhouse, seafood, dinner, lunch, bar, cafe, breakfast, bars, nightlife, accommodation, hotel, attractions, museums, art, churches, nature, parks, viewpoints, activities, tours, shopping, fashion, souvenirs",
                        "default": "gastronomy",
                    },
                    "name_filter": {
                        "type": "string",
                        "description": "Optional: filter results to venues whose name contains this string (case-insensitive). Use when looking for a specific restaurant by name, e.g. 'Vallocaia', 'Kronenhalle'.",
                        "default": "",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default: 10)",
                        "default": 10,
                    },
                },
                "required": [],
            },
        ),
    ],
)
