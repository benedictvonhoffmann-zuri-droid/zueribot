"""Manifest for the air quality connector."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="air_quality",
    version=1,
    enabled=True,
    category="environment",
    pod="app",

    source=Source(
        name="Stadt Zürich UGZ",
        type="official",
        url="https://data.stadt-zuerich.ch",
        refresh="hourly",
    ),

    runtime=Runtime(
        timeout_s=30,
        cache_ttl_s=300,
    ),

    tools=[
        Tool(
            name="get_air_quality",
            handler="get_air_quality",
            description="Get current air quality measurements in Zürich (PM2.5, PM10, NO2, O3).",
            retrieval=Retrieval(
                summary=(
                    "Latest daily air pollution readings (PM10, PM2.5, NO2, O3, CO, "
                    "SO2) from UGZ monitoring stations across Zürich. Use when the "
                    "user asks about air quality, Feinstaub, smog, or if the air "
                    "is clean today."
                ),
                example_queries=[
                    "Wie isch d Luftqualität hüt in Züri?",
                    "Feinstaub Rosengartenstrasse",
                    "Air quality Zurich today",
                    "Is the air clean near Stampfenbach?",
                    "NO2 Messwerte Züri",
                ],
                keywords=[
                    "luftqualität", "air quality", "feinstaub", "pm2.5", "pm10",
                    "no2", "ozon", "smog", "schadstoff", "ugz",
                ],
                not_for=[
                    "pollen forecasts",
                    "indoor air quality",
                    "long-term climate trends",
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
