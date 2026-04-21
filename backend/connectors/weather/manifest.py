"""Manifest for the weather connector."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="weather",
    version=1,
    enabled=True,
    category="environment",
    pod="app",

    source=Source(
        name="Open-Meteo",
        type="official",
        url="https://open-meteo.com",
        license="CC-BY-4.0",
        refresh="realtime",
        attribution_required=True,
    ),

    runtime=Runtime(
        timeout_s=10,
        cache_ttl_s=300,
    ),

    tools=[
        Tool(
            name="get_weather",
            handler="get_weather",
            description=(
                "Get current weather forecast for Zürich. Returns temperature, "
                "conditions, wind, and humidity."
            ),
            retrieval=Retrieval(
                summary=(
                    "Current weather and 3-day forecast for the city of Zürich. "
                    "Use when the user asks about temperature, rain, snow, wind, "
                    "whether to bring an umbrella, or what the weather will be "
                    "like today, tomorrow, or this weekend."
                ),
                example_queries=[
                    "Wie wird das Wätter morn?",
                    "Regnet es heute Nachmittag?",
                    "Should I bring a jacket tomorrow?",
                    "Wetter am Wochenende",
                    "Wie warm wird es heute in Zürich?",
                ],
                keywords=[
                    "weather", "wetter", "wätter", "regen", "rain",
                    "sonne", "sun", "temperatur", "temperature",
                    "forecast", "prognose", "wind", "schnee", "snow",
                ],
                not_for=[
                    "historical climate data",
                    "weather outside the Zürich region",
                    "long-range seasonal forecasts beyond 3 days",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
            returns={
                "current": "temperature_c, humidity_pct, precipitation_mm, wind_speed_kmh, weather_description",
                "forecast": "list of { date, temp_max, temp_min, precipitation, weather_description }",
            },
        ),
    ],
)
