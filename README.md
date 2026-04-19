# Bünzli — The AI that knows Zürich

A sovereign, open-source AI assistant for the city of Zürich. Swiss model, Swiss servers, Swiss law — with real-time local data through a growing library of connectors.

> Live at [buenzli.space](https://buenzli.space) (landing + closed beta). Chat: `/chat/`.

---

## What it is

- **Swiss model.** Apertus 70B (open-weight LLM from EPFL + ETH Zürich), run locally via [Ollama](https://ollama.com/).
- **Swiss servers.** Hosted on [Infomaniak](https://www.infomaniak.com/) in Geneva.
- **Swiss law.** Subject to the Federal Act on Data Protection (FADP). No transfers to third countries.
- **Client-side encrypted chat.** Messages encrypted in your browser (AES-256) before hitting the server; nothing is stored server-side.
- **Open source from day one.** Everything you see is in this repo.

---

## Architecture

```
Browser  ──► Nginx  ──► FastAPI (zuribot)  ──► LangGraph agent
                                                │
                                                ├── Apertus 70B via Ollama
                                                ├── MCP tool server
                                                ├── Connectors (weather, transit, …)
                                                └── SearXNG (self-hosted web search)

Auth: Zitadel Cloud (CH region) — OIDC, validated as JWT by the API
Chat UI: Astro + React + assistant-ui, at /chat/
Landing: Astro + Tailwind, at /
```

### Stack

| Layer | Choice |
|---|---|
| LLM | Apertus 70B (Ollama) |
| Orchestration | LangGraph |
| Tool protocol | MCP (Model Context Protocol) |
| API | FastAPI (Python 3.11) |
| Web search | SearXNG (self-hosted) |
| Chat UI | Astro · React · assistant-ui · Vercel AI SDK |
| Landing | Astro · Tailwind v4 |
| Auth | Zitadel (OIDC) |
| Infra | Docker · Nginx · Infomaniak |

---

## Repository layout

```
zuribot/
├── api_server.py           # FastAPI entry point (OpenAI-compatible)
├── main.py                 # CLI chat loop (dev / debug)
├── requirements.txt
├── requirements-heavy.txt  # torch, sentence-transformers, chromadb
├── backend/
│   ├── agent.py            # LangGraph agent
│   ├── mcp_server.py       # MCP tool server
│   ├── tools/              # Tool definitions + dispatch
│   ├── connectors/         # Zürich data source adapters
│   └── models/             # Pydantic schemas
├── frontend/landing/       # Astro site (landing + /chat/)
├── deploy/                 # Dockerfile.web, nginx.conf, compose
└── evals/                  # Eval suites
```

---

## Running locally

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for SearXNG)
- [Ollama](https://ollama.com/) with an Apertus-compatible model pulled

### 1. Backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-heavy.txt
pip install -r requirements.txt
cp .env.example .env   # fill in secrets locally; never commit
python3 api_server.py
```

The API listens on `:8000` (OpenAI-compatible `/v1/chat/completions`).

### 2. Landing + chat frontend

```bash
cd frontend/landing
npm install
npm run dev
```

Astro serves on `:4321`. The `/chat/` route proxies to the API.

### 3. Supporting services

```bash
docker compose -f deploy/docker-compose.yml up -d searxng
ollama serve
```

---

## Available connectors

Each connector is a small Python module in `backend/connectors/` that maps a public Zürich data source into a tool the agent can call.

| Connector | Source |
|---|---|
| Weather | Open-Meteo |
| Transit (departures, connections) | ZVV / opendata.ch |
| Parking | Zürich Parkleitsystem |
| Water temperatures | Stadt Zürich (Badis) |
| Air quality | Ostluft |
| Points of interest | OpenStreetMap Overpass |
| Voting results | Swissvotes |
| Events | Eventfrog |
| Venues | zuerich.com |
| Recycling / waste schedule | ERZ Stadt Zürich |
| Web search | SearXNG (self-hosted) |

Missing a source? Open an issue or PR.

---

## Deployment

Production is a single VPS on Infomaniak running Docker Compose.

```bash
cd deploy
docker compose build
docker compose up -d
```

Nginx terminates TLS (Let's Encrypt), serves the static landing bundle, and proxies `/zuribot/` to the API and `/chat/` to the Astro output. Request paths stay on `.ch` infrastructure end-to-end.

Secrets (Apertus endpoint, Zitadel client IDs, API tokens) live in `.env` and are never committed. See `.env.example` for required variables.

---

## Contributing

This is a small, personal project. Issues and PRs are welcome, especially:

- New connectors for public Zürich/Swiss data sources
- Swiss German / Züridütsch improvements
- Prompt + eval additions

Please don't open PRs that add tracking, analytics, or cross-border data flows — those conflict with the design goals.

---

## License

MIT. See `LICENSE`.
