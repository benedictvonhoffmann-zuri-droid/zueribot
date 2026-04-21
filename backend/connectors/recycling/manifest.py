"""Manifest for the recycling/waste connector."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="recycling",
    version=1,
    enabled=True,
    category="civic",
    pod="app",

    source=Source(
        name="ERZ Entsorgung + Recycling Zürich",
        type="official",
        url="https://data.stadt-zuerich.ch",
        refresh="weekly",
    ),

    runtime=Runtime(
        timeout_s=15,
        cache_ttl_s=86400,
    ),

    tools=[
        Tool(
            name="get_waste_schedule",
            handler="get_waste_schedule",
            description="Get waste collection schedule for a Zürich zip code (garbage, bio waste, paper, cardboard).",
            retrieval=Retrieval(
                summary=(
                    "Upcoming collection dates for a single waste stream (kehricht, "
                    "bioabfall, papier, karton) at a Zürich zip code. Use when the "
                    "user asks when garbage, bio, paper or cardboard is picked up "
                    "on their street."
                ),
                example_queries=[
                    "Wänn chunt d Kehrichtabfuhr in 8004?",
                    "Next paper collection 8032",
                    "Wänn isch d Bioabfall-Abholig?",
                    "Cardboard pickup date Kreis 4",
                    "Garbage schedule 8001",
                ],
                keywords=[
                    "kehricht", "müll", "garbage", "abfall", "bioabfall",
                    "papier", "paper", "karton", "cardboard", "abfuhr",
                    "entsorgung", "erz", "plz", "zip",
                ],
                not_for=[
                    "glass, metal or oil collection (use get_collection_points)",
                    "mobile recycling dates (use get_mobile_recycling)",
                    "special waste disposal",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "zip_code": {
                        "type": "string",
                        "description": "Zürich zip code (e.g. 8001, 8002, 8032)",
                        "default": "",
                    },
                    "waste_type": {
                        "type": "string",
                        "description": "Type of waste: kehricht (garbage), bioabfall (bio waste), papier (paper), karton (cardboard)",
                        "enum": ["kehricht", "bioabfall", "papier", "karton"],
                        "default": "kehricht",
                    },
                    "upcoming_days": {
                        "type": "integer",
                        "description": "Number of days to look ahead (default: 30)",
                        "default": 30,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_collection_points",
            handler="get_collection_points",
            description="Get recycling collection points in Zürich (glass, metal, oil, textiles).",
            retrieval=Retrieval(
                summary=(
                    "Permanent recycling drop-off points (Sammelstellen) in Zürich "
                    "for glass, metal, oil and textiles, filtered by zip code and "
                    "material. Use when the user wants to know where they can "
                    "drop off bottles, cans, used oil or old clothes."
                ),
                example_queries=[
                    "Wo chan i Glas entsorge in 8004?",
                    "Glass recycling near me",
                    "Altkleider-Sammelstelle 8032",
                    "Where do I throw away used oil?",
                    "Metal recycling point Kreis 4",
                ],
                keywords=[
                    "sammelstelle", "recycling", "glas", "glass", "metall",
                    "metal", "öl", "oel", "oil", "textilien", "textiles",
                    "altkleider", "drop-off",
                ],
                not_for=[
                    "weekly garbage/paper pickup (use get_waste_schedule)",
                    "electronics recycling",
                    "hazardous waste",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "zip_code": {
                        "type": "string",
                        "description": "Zürich zip code (e.g. 8001, 8002)",
                        "default": "",
                    },
                    "material": {
                        "type": "string",
                        "description": "Material to recycle: glas, metall, oel, textilien",
                        "enum": ["glas", "metall", "oel", "textilien"],
                        "default": "",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_mobile_recycling",
            handler="get_mobile_recycling",
            description="Get upcoming dates for mobile recycling centers in Zürich.",
            retrieval=Retrieval(
                summary=(
                    "Dates and locations where ERZ's mobile recycling truck "
                    "(Mobiler Recyclinghof) stops in the coming weeks. Use when "
                    "the user asks when the recycling truck is next in their "
                    "neighbourhood."
                ),
                example_queries=[
                    "Wänn chunt de mobili Recyclinghof in Wipkingen?",
                    "Next mobile recycling 8032",
                    "Mobiler Recyclinghof nöchsti Daten",
                    "When does the recycling truck come?",
                ],
                keywords=[
                    "mobil", "recyclinghof", "mobile recycling", "truck",
                    "entsorgungsfahrzeug", "erz", "termin",
                ],
                not_for=[
                    "permanent recycling points (use get_collection_points)",
                    "regular garbage pickup",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "zip_code": {
                        "type": "string",
                        "description": "Zürich zip code (e.g. 8001, 8002)",
                        "default": "",
                    },
                    "upcoming_days": {
                        "type": "integer",
                        "description": "Number of days to look ahead (default: 60)",
                        "default": 60,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_all_schedules",
            handler="get_all_schedules",
            description="Get all waste collection schedules (garbage, bio, paper, cardboard, mobile recycling) for a Zürich zip code.",
            retrieval=Retrieval(
                summary=(
                    "Combined overview of all upcoming waste pickups (garbage, "
                    "bio, paper, cardboard) and the mobile recycling truck for "
                    "a given Zürich zip code. Use when the user wants everything "
                    "at once, not just one waste stream."
                ),
                example_queries=[
                    "Wänn isch was für Abfuhr in 8004?",
                    "All waste collections 8032",
                    "Nöchschti Abfuhr-Termine Kreis 4",
                    "What's picked up this week at my address?",
                ],
                keywords=[
                    "abfuhr", "übersicht", "alle", "schedule", "waste",
                    "kehricht", "bioabfall", "papier", "karton", "all",
                ],
                not_for=[
                    "glass or textile recycling points",
                    "household appliance disposal",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "zip_code": {
                        "type": "string",
                        "description": "Zürich zip code (e.g. 8001, 8002)",
                        "default": "",
                    },
                    "upcoming_days": {
                        "type": "integer",
                        "description": "Number of days to look ahead (default: 14)",
                        "default": 14,
                    },
                },
                "required": [],
            },
        ),
    ],
)
