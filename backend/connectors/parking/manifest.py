"""Manifest for the parking connector."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="parking",
    version=1,
    enabled=True,
    category="mobility",
    pod="app",

    source=Source(
        name="Stadt Züri Tiefbauamt",
        type="official",
        url="https://api.parkendd.de/Zuerich",
        license="CC-BY-4.0",
        refresh="realtime",
        attribution_required=True,
    ),

    runtime=Runtime(
        timeout_s=10,
        cache_ttl_s=60,
    ),

    tools=[
        Tool(
            name="get_parking",
            handler="get_parking",
            description=(
                "Get current parking availability in Zürich. Shows free spaces, "
                "total capacity, and status for each parking garage."
            ),
            retrieval=Retrieval(
                summary=(
                    "Real-time availability of parking garages and lots in the city "
                    "of Zürich. Use when the user asks where they can park, how many "
                    "free spaces are left in a specific garage, or whether a parking "
                    "lot near a location is open and has capacity right now."
                ),
                example_queries=[
                    "Wo kann ich in Züri parkieren?",
                    "Ist das Parkhaus Opéra offen?",
                    "Free parking spots near Bellevue",
                    "Hat es no Platz im Parkhaus Hauptbahnhof?",
                    "Parking availability downtown Zurich",
                ],
                keywords=[
                    "parking", "parkieren", "parkhaus", "parkplatz",
                    "garage", "auto abstellen", "park",
                ],
                not_for=[
                    "street parking zones (blue/white zones)",
                    "parking fees or pricing",
                    "parking outside the city of Zürich",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
            returns={
                "lots": "list of { name, address, lot_type, state, free, total, occupancy_pct, coords }",
                "last_updated": "ISO timestamp of the upstream refresh",
            },
        ),
    ],
)
