"""Manifest for the water (lake temps + Badi status) connector."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="water",
    version=1,
    enabled=True,
    category="environment",
    pod="app",

    source=Source(
        name="Stadt Zürich (OGD)",
        type="official",
        url="https://data.stadt-zuerich.ch",
        refresh="realtime",
    ),

    runtime=Runtime(
        timeout_s=10,
        cache_ttl_s=60,
    ),

    tools=[
        Tool(
            name="get_water_temps",
            handler="get_water_temps",
            description="Get current water temperatures for swimming spots in and around Zürich (Limmat, Lake Zürich, etc.).",
            retrieval=Retrieval(
                summary=(
                    "Live water temperature, air temperature, wind and water level "
                    "readings from the WAPO/tecdottir stations on Lake Zürich "
                    "(Tiefenbrunnen, Mythenquai). Use when the user asks how warm "
                    "the lake is or whether it's warm enough to swim."
                ),
                example_queries=[
                    "Wie warm isch de Zürisee?",
                    "Water temperature Lake Zurich",
                    "Wassertemperatur Tiefenbrunnen",
                    "Chan mer scho go bade?",
                    "Is the Limmat warm enough to swim?",
                ],
                keywords=[
                    "wassertemperatur", "water temperature", "zürisee", "lake",
                    "limmat", "baden", "schwimmen", "swim", "tiefenbrunnen",
                    "mythenquai", "see",
                ],
                not_for=[
                    "river flow rates or pollution",
                    "indoor pool temperatures",
                    "drinking water quality",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_badi_info",
            handler="get_badi_info",
            description="Get current status, opening hours and water temperature for Zürich Badis (swimming pools and outdoor areas). Use when the user asks if a specific Badi is open, e.g. 'Ist der Letten offen?', 'Wann hat die Badi Mythenquai auf?'. Includes Letten, Oberer Letten, Unterer Letten, Mythenquai, Tiefenbrunnen, Enge, Utoquai, Wollishofen, Allenmoos, Heuried, Letzigraben, Frauenbad, Männerbad and more. Outdoor Freibäder are seasonal (May–September) — this tool will say so when they are closed.",
            retrieval=Retrieval(
                summary=(
                    "Current open/closed status, opening hours and water "
                    "temperature for every Zürich Badi (public swimming spot). "
                    "Use when the user names a specific Badi and wants to know "
                    "if it is open today, or asks which Badis are currently open."
                ),
                example_queries=[
                    "Isch de Letten offen?",
                    "Hat die Badi Mythenquai auf?",
                    "Opening hours Frauenbad",
                    "Wänn macht s Strandbad Tiefenbrunnen zue?",
                    "Which outdoor pools are open right now?",
                ],
                keywords=[
                    "badi", "freibad", "hallenbad", "schwimmbad", "pool",
                    "letten", "mythenquai", "tiefenbrunnen", "frauenbad",
                    "männerbad", "utoquai", "öffnungszeiten", "open",
                ],
                not_for=[
                    "private swimming pools",
                    "swimming lessons or courses",
                    "historical season data",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "badi_name": {
                        "type": "string",
                        "description": "Name of the badi (e.g. 'Letten', 'Mythenquai', 'Tiefenbrunnen'). Leave empty to get all badis.",
                        "default": "",
                    },
                },
                "required": [],
            },
        ),
    ],
)
