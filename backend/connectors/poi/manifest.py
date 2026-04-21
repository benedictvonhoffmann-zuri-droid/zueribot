"""Manifest for the POI connector (OpenStreetMap)."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="poi",
    version=1,
    enabled=True,
    category="utility",
    pod="app",

    source=Source(
        name="OpenStreetMap",
        type="community",
        url="https://overpass-api.de",
        license="ODbL",
        refresh="weekly",
    ),

    runtime=Runtime(
        timeout_s=30,
        cache_ttl_s=86400,
    ),

    tools=[
        Tool(
            name="get_pois",
            handler="get_pois",
            description=(
                "Get points of interest in Zürich (shops, restaurants, pharmacies, supermarkets, etc.) from OpenStreetMap, "
                "sorted by distance from the given location. "
                "When the user asks for the 'nearest' or 'closest' place, ask for their address or current location first, "
                "then pass it as user_address. Results include opening_hours — always mention them in your answer."
            ),
            retrieval=Retrieval(
                summary=(
                    "Search OpenStreetMap for points of interest in Zürich "
                    "(supermarkets, pharmacies, restaurants, ATMs, playgrounds, "
                    "parks, etc.) and sort by distance from a user address or "
                    "coordinates. Use when the user asks for the nearest or "
                    "closest place of a given type."
                ),
                example_queries=[
                    "Wo isch di nöchsti Apotheke?",
                    "Nearest Migros to Bahnhofstrasse 10",
                    "Spielplatz in de Nöchi",
                    "Where is the closest ATM?",
                    "Coop in Kreis 4",
                    "Pharmacy near Hauptbahnhof",
                ],
                keywords=[
                    "poi", "nearest", "nöchsti", "closest", "apotheke", "pharmacy",
                    "migros", "coop", "supermarket", "restaurant", "cafe", "atm",
                    "bank", "spielplatz", "playground", "parkhaus", "osm",
                ],
                not_for=[
                    "detailed opening hours beyond what OSM has",
                    "real-time busyness or wait times",
                    "places outside the Zürich area",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category: restaurant, cafe, bar, hotel, museum, attraction, church, park, viewpoint, pharmacy, hospital, supermarket, bank, atm, post_office, library, cinema, theatre, swimming_pool, fitness_centre, bicycle_parking, bus_station, tram_stop, railway_station",
                        "default": "restaurant",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query — use the place type or brand name (e.g. 'Migros', 'pharmacy', 'restaurant')",
                        "default": "",
                    },
                    "user_address": {
                        "type": "string",
                        "description": "User's current address or location in Zürich (e.g. 'Bahnhofstrasse 10, Zürich'). Used to find nearest results. Leave empty to search city-wide.",
                    },
                    "user_latitude": {
                        "type": "number",
                        "description": "User's latitude (optional, use instead of user_address if coordinates are known)",
                    },
                    "user_longitude": {
                        "type": "number",
                        "description": "User's longitude (optional, use instead of user_address if coordinates are known)",
                    },
                    "radius_m": {
                        "type": "integer",
                        "description": "Search radius in metres around the user's location (default: 1500)",
                        "default": 1500,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default: 5)",
                        "default": 5,
                    },
                },
                "required": [],
            },
        ),
    ],
)
