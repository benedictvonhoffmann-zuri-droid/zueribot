"""Manifest for the voting connector."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="voting",
    version=1,
    enabled=True,
    category="civic",
    pod="app",

    source=Source(
        name="Swissvotes / Stadt Zürich",
        type="official",
        url="https://swissvotes.ch",
        refresh="weekly",
    ),

    runtime=Runtime(
        timeout_s=30,
        cache_ttl_s=86400,
    ),

    tools=[
        Tool(
            name="get_voting_results",
            handler="get_voting_results",
            description="Get Swiss/Zürich voting and referendum results since 1933.",
            retrieval=Retrieval(
                summary=(
                    "Historical Swiss federal, cantonal and City of Zürich voting "
                    "and referendum results since 1933, with turnout, yes/no "
                    "percentages and per-Wahlkreis breakdowns. Use for outcomes "
                    "of Abstimmungen or Initiativen."
                ),
                example_queries=[
                    "Abstimmigsergäbnis vo letztem Sunntig",
                    "Swiss referendum results 2024",
                    "Wie hat Züri zur AHV-Initiative gstimmt?",
                    "Federal vote results by year",
                    "Voting turnout Stadt Zürich",
                ],
                keywords=[
                    "abstimmung", "vote", "voting", "referendum", "initiative",
                    "wahlen", "ja", "nein", "swissvotes", "stimmbeteiligung",
                    "eidgenossenschaft", "kanton", "stadt zürich",
                ],
                not_for=[
                    "upcoming votes or pamphlets",
                    "party programmes",
                    "individual politician voting records",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "date_filter": {
                        "type": "string",
                        "description": "Date filter: YYYY for year, YYYY-MM for month, YYYY-MM-DD for exact date",
                        "default": "",
                    },
                    "level": {
                        "type": "string",
                        "description": "Political level: Eidgenossenschaft (federal), Kanton Zürich (cantonal), Stadt Zürich (city)",
                        "default": "",
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
