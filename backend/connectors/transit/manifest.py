"""Manifest for the transit connector."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="transit",
    version=1,
    enabled=True,
    category="mobility",
    pod="app",

    source=Source(
        name="SBB / ÖV Schwiiz",
        type="official",
        url="https://transport.opendata.ch",
        refresh="realtime",
    ),

    runtime=Runtime(
        timeout_s=15,
        cache_ttl_s=60,
    ),

    tools=[
        Tool(
            name="get_connections",
            handler="get_connections",
            description="Get public transport connections between two stations in Zürich (tram, bus, train).",
            retrieval=Retrieval(
                summary=(
                    "Real-time public transport connections between any two Swiss "
                    "stations, including Zürich tram, bus and train. Use when the "
                    "user asks how to get from A to B, the next train/tram between "
                    "two stops, or how long a ride takes."
                ),
                example_queries=[
                    "Wie chum ich vom HB zum Bellevue?",
                    "Connection from Zürich HB to Oerlikon",
                    "Nöchsti Verbindig Stadelhofen – Enge",
                    "Wie lang dauerts vo Züri nach Winterthur?",
                    "ÖV-Route HB → Flughafen",
                ],
                keywords=[
                    "öv", "tram", "bus", "zug", "train", "sbb", "connection",
                    "verbindung", "route", "fahrplan", "timetable", "ride",
                ],
                not_for=[
                    "car or bike routing",
                    "walking directions",
                    "ticket prices or buying tickets",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "from_station": {
                        "type": "string",
                        "description": "Origin station name (e.g. 'Zürich HB', 'Bellevue')",
                    },
                    "to_station": {
                        "type": "string",
                        "description": "Destination station name (e.g. 'Zürich HB', 'Oerlikon')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of connections to return (default: 3)",
                        "default": 3,
                    },
                },
                "required": ["from_station", "to_station"],
            },
        ),
        Tool(
            name="get_departures",
            handler="get_departures",
            description="Get next departures from a Zürich transit station (tram, bus, train).",
            retrieval=Retrieval(
                summary=(
                    "Next departures from a Zürich transit stop (tram, bus, train). "
                    "Use when the user asks when the next tram/bus leaves from a "
                    "specific stop, or wants a departure board for a station."
                ),
                example_queries=[
                    "Wänn fahrt s nöchste Tram am Bellevue?",
                    "Next departures from Zürich HB",
                    "Abfahrten Stadelhofen",
                    "Wänn chunt de 4er am Paradeplatz?",
                    "Departure board Hardbrücke",
                ],
                keywords=[
                    "abfahrt", "departure", "tram", "bus", "zug", "stationboard",
                    "haltestelle", "stop", "nöchste", "next",
                ],
                not_for=[
                    "route planning from A to B",
                    "historical timetables",
                    "ticket prices",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "station": {
                        "type": "string",
                        "description": "Station name (e.g. 'Zürich HB', 'Bahnhofstrasse', 'Bellevue')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of departures to return (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["station"],
            },
        ),
    ],
)
