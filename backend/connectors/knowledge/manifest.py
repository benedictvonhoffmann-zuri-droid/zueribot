"""Manifest for the knowledge-base connector (RAG)."""

from backend.connectors.base import Manifest, Retrieval, Runtime, Source, Tool

manifest = Manifest(
    id="knowledge",
    version=1,
    enabled=True,
    category="knowledge",
    pod="app",

    source=Source(
        name="Bünzli Knowledge Base (RAG)",
        type="internal",
        url="internal",
        refresh="weekly",
    ),

    runtime=Runtime(
        timeout_s=30,
        cache_ttl_s=86400,
    ),

    tools=[
        Tool(
            name="search_knowledge_base",
            handler="search_knowledge_base",
            description=(
                "Search the Zürich knowledge base for local, cultural, and legal knowledge. "
                "Use for: neighborhood character and recommendations (Kreis 1-12), Swiss customs "
                "and etiquette, tenancy and housing law, government services, local news, "
                "restaurant and food recommendations, recycling rules, history, hidden gems. "
                "Works in German, English, French, Italian, and Swiss German. "
                "For questions about specific places, combine this with get_pois or get_venues "
                "to also get real-time addresses and opening hours."
            ),
            retrieval=Retrieval(
                summary=(
                    "Semantic RAG search over a curated Zürich knowledge base "
                    "covering neighbourhoods, Swiss customs and etiquette, "
                    "tenancy basics, government services, recycling rules, "
                    "history and hidden gems. Multilingual (DE/CH-DE/EN/FR/IT)."
                ),
                example_queries=[
                    "Wie funktionierts mit de Kündigung vo der Wohnig?",
                    "What's the vibe in Kreis 4?",
                    "Tenant rights in Switzerland",
                    "Schweizer Benimmregle am Tisch",
                    "Recycling rules for PET bottles",
                    "Hidden gems in Wipkingen",
                ],
                keywords=[
                    "knowledge", "wissen", "rag", "neighbourhood", "quartier",
                    "kreis", "tenancy", "mietrecht", "etiquette", "customs",
                    "culture", "history", "local",
                ],
                not_for=[
                    "exact legal article text (use search_law_knowledge_base)",
                    "real-time data (weather, transit, air quality)",
                    "web-wide news search",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language question or topic to search for",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of knowledge chunks to retrieve (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_law_knowledge_base",
            handler="search_law_knowledge_base",
            description=(
                "Search the Swiss federal law collection (Bundesverfassung, OR, ZGB, StGB, StPO, ZPO, VRV). "
                "Use ONLY when the user explicitly asks for statutory text, specific article numbers, "
                "or legal citations (e.g. 'Was steht in OR Art. 271?', 'Zeig mir den Gesetzestext zur Kündigung'). "
                "Do NOT use for general advice or questions — use search_knowledge_base for those."
            ),
            retrieval=Retrieval(
                summary=(
                    "Targeted search over Swiss federal law PDFs (BV, OR, ZGB, "
                    "StGB, StPO, ZPO, VRV). Use only when the user asks for "
                    "literal statutory text or a specific article number — not "
                    "for general legal advice."
                ),
                example_queries=[
                    "Was steht in OR Art. 271?",
                    "ZGB Eigentumsrecht Artikel",
                    "Zeig mir den Gesetzestext zur Kündigung",
                    "Swiss law on self-defence StGB",
                    "Bundesverfassung Grundrechte Artikel",
                ],
                keywords=[
                    "gesetz", "law", "artikel", "article", "or", "zgb", "stgb",
                    "bundesverfassung", "fedlex", "statut", "paragraph",
                ],
                not_for=[
                    "general tenant/consumer advice (use search_knowledge_base)",
                    "cantonal or municipal laws",
                    "case law or jurisprudence",
                ],
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Legal question or article reference, e.g. 'OR Art. 271 Kündigung', 'ZGB Eigentumsrecht Artikel'",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of law chunks to retrieve (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
    ],
)
