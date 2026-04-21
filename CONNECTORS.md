# Connector catalogue

Reference list of every connector, its tools, its category, and its data source.
Generated from `backend/connectors/*/manifest.py`. **17 connectors, 24 tools.**

Update this file when connectors are added, removed, or recategorised —
`scripts/dump_connectors.py` (if we add one later) could regenerate it.

---

## Environment — 4 connectors, 5 tools

| Folder | Tool | Source | Pod |
|---|---|---|---|
| `weather` | `get_weather` | Open-Meteo | app |
| `air_quality` | `get_air_quality` | Stadt Zürich UGZ | app |
| `water` | `get_water_temps` | Stadt Zürich OGD | app |
| `water` | `get_badi_info` | Stadt Zürich OGD | app |
| `water_quality` | `get_water_quality` | Wasserversorgung Zürich | app |

## Mobility — 2 connectors, 3 tools

| Folder | Tool | Source | Pod |
|---|---|---|---|
| `transit` | `get_connections` | SBB / ÖV Schwiiz | app |
| `transit` | `get_departures` | SBB / ÖV Schwiiz | app |
| `parking` | `get_parking` | Stadt Züri Tiefbauamt | app |

## Civic — 5 connectors, 8 tools

| Folder | Tool | Source | Pod |
|---|---|---|---|
| `voting` | `get_voting_results` | Swissvotes / Stadt Zürich | app |
| `rent` | `get_rent_prices` | Stadt Zürich Statistik (MPE) | app |
| `pedestrian` | `get_pedestrian_counts` | Stadt Zürich Tiefbauamt | app |
| `recycling` | `get_waste_schedule` | ERZ | app |
| `recycling` | `get_collection_points` | ERZ | app |
| `recycling` | `get_mobile_recycling` | ERZ | app |
| `recycling` | `get_all_schedules` | ERZ | app |
| `city_stats` | `get_recycling_stats` | Stadt Zürich OGD | app |
| `city_stats` | `get_electricity_load` | Stadt Zürich OGD (EWZ) | app |

## Culture — 2 connectors, 2 tools

| Folder | Tool | Source | Pod |
|---|---|---|---|
| `events` | `get_events` | Eventfrog | app |
| `venues` | `get_venues` | zuerich.com (Zürich Tourism) | app |

## Safety — 1 connector, 1 tool

| Folder | Tool | Source | Pod |
|---|---|---|---|
| `crime` | `get_crime_stats` | Kantonspolizei Zürich | app |

## Knowledge — 1 connector, 2 tools

| Folder | Tool | Source | Pod |
|---|---|---|---|
| `knowledge` | `search_knowledge_base` | Bünzli Knowledge Base (RAG) | app |
| `knowledge` | `search_law_knowledge_base` | Bünzli Knowledge Base (RAG) | app |

> **Note — to revisit when AI pod lands.** Both knowledge tools are candidates
> for replacement by automatic RAG wired into the agent's context-build step,
> rather than explicit LLM tool calls. `search_law_knowledge_base` may stay
> as a tool (law lookups are often explicit). When migrated, set `pod: ai`
> here in the meantime.

## Utility — 2 connectors, 2 tools

| Folder | Tool | Source | Pod |
|---|---|---|---|
| `poi` | `get_pois` | OpenStreetMap | app |
| `search` | `web_search` | SearXNG (self-hosted) | app |

---

## Categories at a glance

| Category | Purpose | Connectors |
|---|---|---|
| `environment` | Weather, water, air, swimming | 4 |
| `mobility` | Transit, parking | 2 |
| `civic` | Housing, voting, waste, city statistics, pedestrian flow | 5 |
| `culture` | Events, venues, tourism | 2 |
| `safety` | Crime statistics | 1 |
| `knowledge` | Local + legal RAG | 1 |
| `utility` | General-purpose lookup (POI, web search) | 2 |

## Legend

- **Folder** — path under `backend/connectors/`, also the manifest `id`
  and what the registry uses to route.
- **Tool** — the LLM-facing name sent in `TOOL_DEFINITIONS`.
- **Source** — provenance string returned in every response envelope.
- **Pod** — where the handler runs. Today all `app`; `ai` reserved for
  connectors that require the (not-yet-provisioned) AI pod with
  embedding/reranker/vector store.
