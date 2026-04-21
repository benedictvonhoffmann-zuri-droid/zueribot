"""Manifest for the crime statistics connector."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="crime",
    version=1,
    enabled=True,
    category="safety",
    pod="app",

    source=Source(
        name="Kantonspolizei Zürich",
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
            name="get_crime_stats",
            handler="get_crime_stats",
            description="Get crime statistics (Kriminalstatistik) for Zürich Stadtkreise from the Kantonspolizei. Shows number of offences by category and crime rate per 1,000 residents. Use when asked about safety, crime rates, or how safe a neighbourhood is.",
            retrieval=Retrieval(
                summary=(
                    "Annual police crime statistics (PKS) for Zürich Stadtkreise, "
                    "with offence counts by category and Häufigkeitszahl (crimes "
                    "per 1,000 residents). Use when the user asks how safe a "
                    "neighbourhood is or wants crime numbers by category."
                ),
                example_queries=[
                    "Wie sicher isch de Kreis 4?",
                    "Crime statistics Zurich",
                    "Einbrüche in Wipkingen",
                    "Is Kreis 5 safe at night?",
                    "Körperverletzung Zahlen Züri",
                ],
                keywords=[
                    "kriminalität", "crime", "sicher", "safe", "einbruch",
                    "diebstahl", "körperverletzung", "pks", "polizei",
                    "stadtkreis", "kreis", "häufigkeitszahl",
                ],
                not_for=[
                    "live police incident feeds",
                    "traffic violations",
                    "advice on personal safety",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "stadtkreis": {
                        "type": "string",
                        "description": "Kreis number or name (e.g. '4', 'Kreis 4'). Leave empty for all city districts.",
                        "default": "",
                    },
                    "category": {
                        "type": "string",
                        "description": "Crime category filter (e.g. 'Einbruch', 'Körperverletzung', 'Diebstahl'). Leave empty for all categories.",
                        "default": "",
                    },
                },
                "required": [],
            },
        ),
    ],
)
