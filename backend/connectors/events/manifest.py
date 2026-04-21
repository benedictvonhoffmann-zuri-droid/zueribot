"""Manifest for the events connector."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="events",
    version=1,
    enabled=True,
    category="culture",
    pod="app",

    source=Source(
        name="Eventfrog",
        type="community",
        url="https://eventfrog.ch",
        refresh="daily",
    ),

    runtime=Runtime(
        env=["EVENTFROG_KEY"],
        timeout_s=15,
        cache_ttl_s=3600,
    ),

    tools=[
        Tool(
            name="get_events",
            handler="get_events",
            description="Get upcoming events in and around Zürich from Eventfrog.",
            retrieval=Retrieval(
                summary=(
                    "Upcoming events (concerts, festivals, exhibitions, parties, "
                    "workshops, sports) in and around Zürich, pulled from the "
                    "Eventfrog aggregator. Use when the user asks what is "
                    "happening this week, today, this weekend."
                ),
                example_queries=[
                    "Was isch hüt abig los in Züri?",
                    "Konzerte am Wuchenänd",
                    "Events in Zurich this weekend",
                    "Ausstellige im September",
                    "Festival near me tonight",
                ],
                keywords=[
                    "events", "veranstaltigen", "konzert", "festival", "party",
                    "ausstellung", "exhibition", "concert", "theatre", "comedy",
                    "workshop", "weekend", "wuchenänd",
                ],
                not_for=[
                    "ticket prices or seat bookings",
                    "events outside Switzerland",
                    "past events",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for events (e.g. 'concert', 'exhibition', 'festival')",
                        "default": "",
                    },
                    "category": {
                        "type": "string",
                        "description": "Event category filter",
                        "default": "",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default: 10)",
                        "default": 10,
                    },
                },
                "required": [],
            },
        ),
    ],
)
