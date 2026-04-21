"""Manifest for the rent price connector."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="rent",
    version=1,
    enabled=True,
    category="civic",
    pod="app",

    source=Source(
        name="Stadt Zürich Statistik (MPE)",
        type="official",
        url="https://data.stadt-zuerich.ch",
        license="CC-BY-4.0",
        refresh="weekly",
    ),

    runtime=Runtime(
        timeout_s=30,
        cache_ttl_s=86400,
    ),

    tools=[
        Tool(
            name="get_rent_prices",
            handler="get_rent_prices",
            description="Get rent price statistics for Zürich from the official Mietpreiserhebung (MPE). Shows median, mean and quartile rents by neighbourhood (Quartier/Stadtkreis) and number of rooms. Use when asked about rent costs, housing prices, or how expensive it is to live in a specific area.",
            retrieval=Retrieval(
                summary=(
                    "Official net rent statistics (median, mean, quartiles) for "
                    "Zürich by neighbourhood/Stadtkreis and apartment size, from "
                    "the biannual Mietpreiserhebung. Can also return cooperative "
                    "(gemeinnützige) housing prices."
                ),
                example_queries=[
                    "Was koschtet e 3-Zimmer-Wohnig im Kreis 4?",
                    "Average rent Wipkingen 2 rooms",
                    "Mietpreis Langstrasse",
                    "Wie tüür isch Züri zum Wohne?",
                    "Genossenschafts-Miete Zürich",
                ],
                keywords=[
                    "miete", "rent", "mietpreis", "wohnung", "apartment",
                    "quartier", "kreis", "zimmer", "wohnen", "housing",
                    "gemeinnützig", "mpe",
                ],
                not_for=[
                    "rental listings or specific flats for rent",
                    "tenant law (use search_knowledge_base or search_law_knowledge_base)",
                    "buying property or mortgage rates",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "quartier": {
                        "type": "string",
                        "description": "Neighbourhood or Stadtkreis (e.g. 'Ganze Stadt', 'Kreis 4', 'Langstrasse', 'Wipkingen'). Leave empty for city-wide overview.",
                        "default": "",
                    },
                    "rooms": {
                        "type": "string",
                        "description": "Number of rooms (e.g. '2', '3', '3.5', '4'). Leave empty for all room sizes.",
                        "default": "",
                    },
                    "gemeinnuetzig": {
                        "type": "boolean",
                        "description": "If true, return cooperative/social housing prices only.",
                        "default": False,
                    },
                },
                "required": [],
            },
        ),
    ],
)
