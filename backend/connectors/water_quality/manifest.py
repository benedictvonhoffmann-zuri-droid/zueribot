"""Manifest for the drinking water quality connector."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="water_quality",
    version=1,
    enabled=True,
    category="environment",
    pod="app",

    source=Source(
        name="Wasserversorgung Zürich",
        type="official",
        url="https://data.stadt-zuerich.ch",
        license="CC-BY-4.0",
        refresh="daily",
    ),

    runtime=Runtime(
        timeout_s=30,
        cache_ttl_s=3600,
    ),

    tools=[
        Tool(
            name="get_water_quality",
            handler="get_water_quality",
            description="Get drinking water quality measurements for Zürich from Wasserversorgung Zürich. Shows key parameters (E. coli, pH, nitrate, turbidity) and whether all values comply with legal limits. Use when asked if tap water in Zürich is safe to drink.",
            retrieval=Retrieval(
                summary=(
                    "Drinking water quality measurements (E. coli, pH, nitrate, "
                    "turbidity, chlorine, temperature) from Wasserversorgung "
                    "Zürich, compared against legal limits. Use when the user "
                    "asks if Zürich tap water is safe to drink."
                ),
                example_queries=[
                    "Cha me s Hahnewasser in Züri tränke?",
                    "Is tap water in Zurich safe?",
                    "Trinkwasserqualität Hardhof",
                    "Nitrat im Wasser Züri",
                    "pH value drinking water Zurich",
                ],
                keywords=[
                    "trinkwasser", "drinking water", "hahnewasser", "tap water",
                    "e. coli", "nitrat", "ph", "trübung", "qualität", "safe",
                ],
                not_for=[
                    "lake or river water quality for swimming",
                    "bottled water comparisons",
                    "water supply outages",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "standort": {
                        "type": "string",
                        "description": "Measurement location (e.g. 'Moos', 'Hardhof', 'Lengg'). Leave empty for all locations.",
                        "default": "",
                    },
                },
                "required": [],
            },
        ),
    ],
)
