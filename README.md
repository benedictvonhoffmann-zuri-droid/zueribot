# Bünzli.Space

**A love letter to Zürich. Built by humans, with a lot of help from AI.**

A sovereign, open-source AI assistant for the city of Zürich. Swiss model, Swiss servers, Swiss law, live local data, and a privacy model you can verify from your browser's network tab.

Live at **[buenzli.space](https://buenzli.space)** (landing + closed beta). Chat: `/chat/`.

---

## Why

Four constraints shaped every technical decision:

1. **Affordable.** Free during beta; modest subscription at worst long-term. Never ad-supported.
2. **Locally competent.** Trained for Swiss German, grounded in live Zürich APIs — not Switzerland-in-general.
3. **Privacy-by-default.** Swiss jurisdiction end-to-end, encrypted client-side, anonymised, no training on user data.
4. **Open.** MIT-licensed code, auditable infrastructure, zero telemetry.

For every layer there was a cheaper US-hosted alternative. They were rejected on principle.

---

## Architecture

```
Browser  ──► Caddy (TLS)  ──► FastAPI (zuribot)  ──► LangGraph agent
                                                      │
                                                      ├── Apertus 70B via Infomaniak AI Tools
                                                      ├── MCP tool server
                                                      ├── Connectors (weather, transit, law, …)
                                                      └── SearXNG (self-hosted web search)

Auth:    Zitadel (self-hosted, same DC) — OIDC + PKCE, JWT-validated by the API
Chat UI: Astro + React + assistant-ui, at /chat/
Landing: Astro + Tailwind, at /
```

### Stack

| Layer | Choice | Rationale |
|---|---|---|
| Model | Apertus 70B | Open-weight, Swiss-trained (ETH + EPFL), fluent in DE / CH-DE |
| Inference | Infomaniak AI Tools | Swiss-hosted, token-billed, no data-retention clauses |
| Orchestration | LangGraph | Typed agent graph, tool-use patterns |
| Tool protocol | MCP (Model Context Protocol) | Clean tool-server boundary |
| Backend | FastAPI (Python 3.11) | Async, OpenAI-compatible endpoints |
| Web search | SearXNG (self-hosted) | Meta-search, no per-query tracking |
| Auth | Zitadel (self-hosted) | OIDC-compliant, Swiss, open source |
| Chat UI | Astro · React · assistant-ui · Vercel AI SDK | Static output + React islands |
| Landing | Astro · Tailwind v4 | Static, SEO-friendly, cheap to host |
| Translations (planned) | Supertext API | Best Swiss German output in internal evaluation |
| Proxy | Caddy | Auto-TLS via Let's Encrypt, minimal config |
| Compute | Infomaniak Public Cloud, Zürich DC (dc4-a) | Ubuntu 24.04, 4 vCPU / 8 GB / 40 GB SSD |
| Orchestration | Docker Compose | Single-host, reproducible, easy to reason about |

No piece of the stack is physically outside Switzerland.

---

## Privacy, concretely

The promise "your data stays safe" is cheap. Here's what it actually means on Bünzli:

- **Client-side encryption.** Your chat history is AES-256-encrypted in the browser before it ever touches the network. The server persists only ciphertext. Without your key, it is noise.
- **Pseudonymous identity.** Sessions are tied to an opaque Zitadel user ID, not an email or IP address in request logs.
- **No cross-border egress.** Every request terminates in `.ch`. Verify it yourself — DevTools → Network tab while chatting.
- **No analytics, no telemetry, no tracking pixels.** The only per-session log entry is a token count for billing reconciliation.
- **No training on user data.** Ever. The model was trained once, externally, on public data.
- **Open source.** The claim is only as good as the code backing it. Read it. Break it. Open an issue if something looks off.

---

## Security posture

- **Network** — Infomaniak anti-DDoS, OpenStack security groups (22/80/443 only), key-only SSH, no root login.
- **Application** — JWT bearer auth on `/v1/chat/completions`, ModSecurity + OWASP CRS in front of the API (planned), 10 req/s rate limit on backend routes.
- **Auth** — Zitadel brute-force protection, OIDC + PKCE from the SPA.
- **Monitoring** — weekly OWASP ZAP baseline scan via GitHub Action.
- **No CDN in front.** Cloudflare et al. were explicitly rejected to keep the Swiss-jurisdiction story clean.

---

## Data flow

1. Browser negotiates an AES-256 key on first login (derived from user secret, never sent to server).
2. Request → Caddy (TLS termination) → FastAPI backend (JWT verified against Zitadel).
3. Backend assembles system prompt + tool schema + decrypted context window.
4. Apertus invoked via Infomaniak; tools called as needed (see below).
5. Response streamed back along the same path.
6. Browser re-encrypts the new exchange before persisting.

---

## Connectors

Each connector is a small Python module in `backend/connectors/` that maps a public Swiss/Zürich data source into a tool the agent can call.

| Connector | Source |
|---|---|
| Weather | Open-Meteo |
| Transit (departures, connections) | ZVV / opendata.ch |
| Parking | Zürich Parkleitsystem |
| Water temperature (badis) | Stadt Zürich |
| Water quality | AWEL |
| Air quality | Ostluft |
| Points of interest | OpenStreetMap Overpass |
| Events | Eventfrog |
| Venues | zuerich.com |
| Recycling / waste schedule | ERZ Stadt Zürich |
| Voting results | Swissvotes |
| News | SRF |
| City services | Stadt Zürich |
| City stats | Statistik Stadt Zürich |
| Crime stats | Kapo Zürich |
| Pedestrian counts | Stadt Zürich |
| Rent law + rental market | Fedlex, ZMV |
| Web search | SearXNG (self-hosted) |
| Knowledge base | Local vector store (law + manuals) |

Missing a source? Open an issue or PR.

---

## Roadmap

- **Agents** — action-taking tools beyond Q&A. First three in development:
  - Restaurant booking (Quandoo)
  - ERZ pickup scheduling
  - Züri-wie-neu report filing
- **Multi-language output** — full CH-DE / DE / EN / FR / IT via Supertext.
- **Federated logins** — Zitadel-backed, surfacing in the SPA.
- **Public beta** — summer 2026, starting at 50 seats.

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
├── deploy/                 # Dockerfile.web, Caddyfile, compose
└── evals/                  # Eval suites
```

---

## Running locally

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for SearXNG, Caddy)
- Infomaniak AI Tools API key (or Ollama + an Apertus-compatible model locally)

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

### 2. Frontend

```bash
cd frontend/landing
npm install
npm run dev
```

Astro serves on `:4321`. The `/chat/` route proxies to the API.

### 3. Supporting services

```bash
docker compose -f deploy/docker-compose.yml up -d searxng
```

---

## Deployment

Production runs on a single Infomaniak VPS (Zürich DC) with Docker Compose.

```bash
cd deploy
docker compose up -d --build
```

Caddy terminates TLS via Let's Encrypt, serves the static landing bundle through nginx, and proxies `/zuribot/` to the API and `/chat/` to the Astro build. Request paths stay on `.ch` infrastructure end-to-end.

Secrets (Infomaniak AI Tools key, Zitadel client IDs, API tokens) live in `.env` and are never committed. See `.env.example` for required variables.

---

## Cost model

A 70B open-weight model served per-token via Infomaniak is cheap enough that beta usage sits comfortably within a personal budget. Long-term:

- **Free tier** — casual use stays free.
- **Subscription tier** — CHF-scale monthly fee for heavy users, only if someone opts in.
- **No ads. Ever.**

---

## On using AI to build it

Most of Bünzli was written with Claude as a pair programmer. Disclosure rather than disclaimer: the tooling is Anthropic's, the product is Swiss. The inference, the storage, the jurisdiction, and the data flowing through the running product are the parts that matter for the privacy claim — and none of those touch a non-Swiss provider.

---

## Contributing

Issues and PRs welcome, especially:

- New connectors for public Zürich / Swiss data sources
- Swiss German / Züridütsch improvements
- Prompt + eval additions
- Security reviews

Please don't open PRs that add tracking, analytics, or cross-border data flows — they conflict with the design goals and will be closed.

---

## Contact

- Product: **[buenzli.space](https://buenzli.space)**
- Email: sali@buenzli.space

---

## License

MIT. See `LICENSE`.
