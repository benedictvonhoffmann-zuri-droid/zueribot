"""Manifest for the pedestrian-count connector."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="pedestrian",
    version=1,
    enabled=True,
    category="civic",
    pod="app",

    source=Source(
        name="Stadt Zürich Tiefbauamt",
        type="official",
        url="https://data.stadt-zuerich.ch",
        license="CC-BY-4.0",
        refresh="hourly",
    ),

    runtime=Runtime(
        timeout_s=60,
        cache_ttl_s=300,
    ),

    tools=[
        Tool(
            name="get_pedestrian_counts",
            handler="get_pedestrian_counts",
            description="Get current pedestrian frequency counts on the Zürich Bahnhofstrasse (Nord, Mitte, Süd) and Lintheschergasse. Updated hourly. Use when asked how busy/crowded Bahnhofstrasse is right now.",
            retrieval=Retrieval(
                summary=(
                    "Latest pedestrian counts from Hystreet sensors on "
                    "Bahnhofstrasse (Nord, Mitte, Süd) and Lintheschergasse, "
                    "updated hourly. Use when the user asks how busy or crowded "
                    "the Bahnhofstrasse is right now."
                ),
                example_queries=[
                    "Wie voll isch d Bahnhofstrass grad?",
                    "Pedestrian count Bahnhofstrasse",
                    "Is it crowded downtown Zurich?",
                    "Passanten Bahnhofstrass Mitti",
                    "How busy is Lintheschergasse?",
                ],
                keywords=[
                    "passanten", "pedestrian", "fussgänger", "crowd", "busy",
                    "voll", "bahnhofstrasse", "hystreet", "frequenz",
                ],
                not_for=[
                    "traffic congestion or car counts",
                    "historical trends over years",
                    "pedestrian counts outside the core streets",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "integer",
                        "description": "Look-back window in hours (1–24). Default 6.",
                        "default": 6,
                    },
                },
                "required": [],
            },
        ),
    ],
)
