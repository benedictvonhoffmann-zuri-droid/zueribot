"""Manifest for the city stats connector (ERZ recycling + EWZ electricity)."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="city_stats",
    version=1,
    enabled=True,
    category="civic",
    pod="app",

    source=Source(
        name="Stadt Zürich OGD",
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
            name="get_recycling_stats",
            handler="get_recycling_stats",
            description="Get latest recycling and waste statistics for Zürich from ERZ (Entsorgung + Recycling Zürich). Shows Zürisack sales, recycling quota percentage, and monthly waste tonnage. Use when asked about Zürich's recycling rate or waste volumes.",
            retrieval=Retrieval(
                summary=(
                    "Latest monthly operating numbers from ERZ: Zürisack sales, "
                    "recycling quota percentage, monthly waste tonnage, plus a "
                    "6-month quota trend. Use when the user asks about Zürich's "
                    "recycling rate or city-wide waste volumes."
                ),
                example_queries=[
                    "Wie hoch isch d Recyclingquote in Züri?",
                    "Zürisack sales last month",
                    "Müllmenge Stadt Zürich",
                    "Recycling rate Zurich",
                    "ERZ Kennzahlen",
                ],
                keywords=[
                    "recyclingquote", "recycling rate", "zürisack", "müll",
                    "waste", "tonnage", "erz", "abfall", "statistik",
                ],
                not_for=[
                    "personal pickup schedule (use get_waste_schedule)",
                    "collection points (use get_collection_points)",
                    "historical multi-year comparisons",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_electricity_load",
            handler="get_electricity_load",
            description="Get current electricity consumption (Bruttolastgang) for the city of Zürich from EWZ. Shows real-time power demand in megawatts with 15-minute resolution. Use when asked about Zürich's energy consumption or current power demand.",
            retrieval=Retrieval(
                summary=(
                    "EWZ Bruttolastgang: city-wide gross electricity load for "
                    "Zürich in megawatts, in 15-minute intervals, plus a 4-hour "
                    "trend. Use when the user asks about Zürich's current "
                    "electricity demand or power consumption."
                ),
                example_queries=[
                    "Wie viel Strom verbrucht Züri grad?",
                    "Current electricity load Zurich",
                    "EWZ Bruttolastgang",
                    "Power consumption Zurich now",
                    "MW Verbrauch Stadt Züri",
                ],
                keywords=[
                    "strom", "electricity", "bruttolastgang", "power", "load",
                    "mw", "megawatt", "ewz", "verbrauch", "energie",
                ],
                not_for=[
                    "electricity prices or tariffs",
                    "household-level consumption",
                    "renewable energy share breakdowns",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ],
)
