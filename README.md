# Bünzli.Space

**A sovereign, open-source AI assistant for Zürich.** Swiss models, Swiss servers, Swiss law, live local data, privacy you can verify from your browser's network tab.

Live at **[buenzli.space](https://buenzli.space)** — landing page + closed beta. Chat lives at `/chat/`.

> Built solo by a non-engineer PM, with Claude as a pair programmer. Disclosure rather than disclaimer: the tooling is American, the product is Swiss. Inference, storage, jurisdiction, and every byte of user data stay inside `.ch`.

---

## Status — April 2026

| Area | State |
|---|---|
| Landing site (DE / CH-DE) | **Live** at [buenzli.space](https://buenzli.space) |
| Closed beta sign-up | **Live** — email-gated, ~50 seats |
| Production VPS + edge proxy | **Live** — Caddy + FastAPI + Astro on a single Infomaniak Zürich VPS |
| Pod-based Docker deployment | **Live** — `bunzli-app`, `bunzli-app-iam`, `bunzli-gpu` |
| Knowledge base — Phase 1 ingest | **Sealed** — 41,714 chunks across 10 categories (federal + cantonal law, city services, transport, history, culture, …) |
| Knowledge base — embeddings + retrieval | **In progress** — GPU pod provisioning, EmbeddingGemma + BGE reranker + Qdrant |
| Self-hosted auth (Zitadel) | **Staged** — pod ready, not yet wired into the SPA |
| Orchestration v1 (Apertus voice + Mistral tools) | **Designed**, build pending GPU pod |
| Public beta | **Target:** summer 2026 |

Recent shipped work: see [CHANGELOG.md](CHANGELOG.md).

---

## Why

Four constraints shape every technical decision:

1. **Affordable.** Free during beta; modest subscription at worst long-term. Never ad-supported.
2. **Locally competent.** Trained for Swiss German, grounded in live Zürich APIs — not Switzerland-in-general.
3. **Privacy-by-default.** Swiss jurisdiction end-to-end, encrypted client-side, anonymised, no training on user data.
4. **Open.** MIT-licensed code, auditable infrastructure, zero telemetry.

For every layer there was a cheaper US-hosted alternative. They were rejected on principle.

---

## Architecture

Bünzli runs across **two physical machines** in Infomaniak's Zürich datacentre, organised as **pods** — one Docker Compose project per coherent slice of functionality.

```
   ┌───────────────────────────────────────────┐         ┌─────────────────────────────┐
   │  Infomaniak VPS  (buenzli.space)          │         │  Infomaniak GPU instance    │
   │                                           │         │  (gpu.buenzli.space, A2)    │
   │  ┌─────────────────────────────────────┐  │  HTTPS  │                             │
   │  │  bunzli-app pod                     │──┼─────────┼─▶ bunzli-gpu pod            │
   │  │   • bunzli-app-edge   (Caddy/TLS)   │  │         │   • bunzli-gpu-edge         │
   │  │   • bunzli-app-api    (FastAPI)     │  │         │   • bunzli-gpu-embed        │
   │  │   • bunzli-app-landing (Astro)      │  │         │   • bunzli-gpu-rerank       │
   │  └─────────────────────────────────────┘  │         │   • bunzli-gpu-qdrant       │
   │                                           │         │   • bunzli-gpu-llm (staging)│
   │  ┌─────────────────────────────────────┐  │         │                             │
   │  │  bunzli-app-iam pod (Zitadel SSO)   │  │         └─────────────────────────────┘
   │  └─────────────────────────────────────┘  │
   └───────────────────────────────────────────┘
```

Full operational write-up: [docs/infrastructure.md](docs/infrastructure.md).

### Pods

| Pod | Host | Purpose |
|---|---|---|
| [`bunzli-app`](deploy/pods/app/) | VPS | Edge proxy + FastAPI backend + static landing site |
| [`bunzli-app-iam`](deploy/pods/app-iam/) | VPS | Self-hosted Zitadel for OIDC auth |
| [`bunzli-gpu`](deploy/pods/gpu/) | GPU instance | Embeddings, reranker, vector store, staging LLM |

### Stack

| Layer | Choice | Rationale |
|---|---|---|
| Production LLM (chat voice) | Apertus 70B via Infomaniak AI Tools | Open-weight, Swiss-trained (ETH + EPFL), strong CH-DE |
| Production LLM (tool use) | Mistral 7B via Infomaniak | Lower-latency, function-calling-tuned |
| Staging LLM | Qwen 2.5 7B Instruct (Q4_K_M) on llama.cpp | Self-hosted on the GPU pod for free iteration |
| Embeddings | EmbeddingGemma | Multilingual, fits on the A2 |
| Reranker | BGE-reranker-base | Quality boost on top-k retrieval |
| Vector store | Qdrant | Self-hosted, single-node |
| Orchestration | Plain Python — **no LangChain** | Code-orchestrated, browser-local state, easier to reason about and ship |
| Backend | FastAPI (Python 3.11) | Async, OpenAI-compatible endpoints |
| Auth | Zitadel (self-hosted) | OIDC + PKCE, Swiss, open source |
| Chat UI | Astro · React · assistant-ui · Vercel AI SDK | Static shell, React islands at `/chat/` |
| Landing | Astro · Tailwind v4 · two locales (DE / CH-DE) | Static, SEO-friendly, cheap to host |
| Edge / TLS | Caddy 2 | Auto-TLS via Let's Encrypt, minimal config |
| Compute | Infomaniak Public Cloud, Zürich (dc4-a) | Ubuntu 24.04 — VPS 4 vCPU / 8 GB; GPU instance with NVIDIA A2 |
| Orchestration runtime | Docker Compose | Single-host pods, reproducible, auditable |

No piece of the runtime stack is physically outside Switzerland.

---

## Privacy, concretely

The promise "your data stays safe" is cheap. Here's what it actually means on Bünzli:

- **Client-side encryption.** Chat history is AES-256-encrypted in the browser before it touches the network. The server persists ciphertext only.
- **Pseudonymous identity.** Sessions are tied to an opaque Zitadel user ID, not an email or IP in request logs.
- **No cross-border egress.** Every request terminates in `.ch`. Verify it yourself — DevTools → Network tab while chatting.
- **No analytics, no telemetry, no tracking pixels.** The only per-session log entry is a token count for billing reconciliation.
- **No training on user data.** Ever.
- **Open source.** The claim is only as good as the code backing it. Read it. Break it. Open an issue.

---

## Security posture

- **Network** — Infomaniak anti-DDoS, OpenStack security groups (22/80/443 only), key-only SSH, no root login.
- **Application** — JWT bearer auth on `/v1/chat/completions`, ModSecurity + OWASP CRS planned, 10 req/s rate limit on backend routes.
- **Auth** — Zitadel brute-force protection, OIDC + PKCE from the SPA.
- **Monitoring** — weekly OWASP ZAP baseline scan via GitHub Action.
- **No CDN.** Cloudflare et al. were rejected to keep the Swiss-jurisdiction story clean.

---

## Connectors

Each connector is a small Python module in `backend/connectors/` mapping a public Swiss/Zürich data source into a tool the agent can call.

| Domain | Sources |
|---|---|
| Weather / environment | Open-Meteo, AWEL (water), Ostluft (air), Stadt Zürich (badi temps) |
| Mobility | ZVV / opendata.ch (transit), Zürich Parkleitsystem |
| City services | Stadt Zürich (services, stats), ERZ (waste), Statistik Stadt Zürich |
| Civic / legal | Fedlex, ZMV, Swissvotes, Kapo Zürich |
| Culture | OSM Overpass (POIs), Eventfrog, zuerich.com, SRF |
| Knowledge | Local Qdrant vector store (federal + cantonal law, city handbooks, history) |
| Web fallback | SearXNG (self-hosted, when re-enabled) |

Missing a source? Open an issue or PR.

---

## Knowledge base

A from-scratch rebuild of Bünzli's RAG corpus is in flight. Phase 1 (ingest, normalise, chunk) finished April 2026 with **41,714 chunks** across a 10-category taxonomy — federal/cantonal law, city services, transport, history, culture, civic life. Phase 2 (embedding + retrieval acceptance on the GPU pod) is the current sprint. Spec lives in [docs/knowledge_base.md](docs/knowledge_base.md).

History sources are deliberately curated for Bünzli's *voice* (turns of phrase, local references), not as a Q&A reference — the model is meant to feel like it grew up here, not parrot Wikipedia.

---

## Roadmap

Near term (next ~6 weeks):

- **Retrieval online.** Embed Phase 1 chunks, stand up Qdrant + reranker on `bunzli-gpu`, pass acceptance evals.
- **Orchestrator v1.** Code-orchestrated chitchat / RAG / tool-call routing — Apertus voice + Mistral tool-call, browser-local state. See [docs/orchestration_architecture.md](docs/orchestration_architecture.md).
- **Self-hosted auth live.** Zitadel pod surfaced at `auth.buenzli.space`, wired into the SPA.

Medium term:

- **Action-taking agents.** Three first-party tools beyond Q&A: restaurant booking (Quandoo), waste-pickup scheduling (ERZ), street-defect filing (Züri-wie-neu).
- **Multi-language output.** Full CH-DE / DE / EN / FR / IT via Supertext API.
- **Public beta.** Summer 2026, opening with 50 seats.

Longer term:

- **Swiss-German fine-tune** once we have enough labelled in-domain data. Until then: glossary in the system prompt, no runtime translation.
- **Native mobile** if the web app finds product-market fit.

---

## Repository layout

```
zuribot/
├── api_server.py              # FastAPI entry point (OpenAI-compatible)
├── backend/
│   ├── agent.py               # Plain-Python orchestrator
│   ├── tools/                 # Tool definitions + dispatch
│   ├── connectors/            # Zürich data source adapters
│   └── models/                # Pydantic schemas
├── frontend/
│   ├── landing/               # Astro site (landing + /chat/ shell)
│   └── chat/                  # React + assistant-ui chat island
├── deploy/
│   └── pods/
│       ├── app/               # bunzli-app — edge + api + landing
│       ├── app-iam/           # bunzli-app-iam — Zitadel
│       └── gpu/               # bunzli-gpu — embed + rerank + qdrant + staging LLM
├── kb/                        # Knowledge base ingest pipeline + Phase 1 output
├── docs/                      # Infrastructure, KB, orchestration, staging spec
├── evals/                     # Eval suites
└── scripts/                   # One-shot tooling (embed, audits, …)
```

---

## Running locally

### Prerequisites

- Python 3.11+, Node.js 20+, Docker
- Infomaniak AI Tools API key (or any OpenAI-compatible endpoint)

### Backend

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt          # core
pip install -r requirements-heavy.txt    # torch, sentence-transformers, chromadb (only if running KB locally)
cp .env.example .env                     # fill secrets locally; never commit
python3 api_server.py
```

API listens on `:8000` (OpenAI-compatible `/v1/chat/completions`).

### Frontend

```bash
cd frontend/landing && npm install && npm run dev
```

Astro serves on `:4321`. The `/chat/` route proxies to the API.

### Full pod stack (TLS + reverse proxy)

```bash
docker compose -f deploy/pods/app/docker-compose.yml up -d --build
```

Caddy can't issue real Let's Encrypt certs locally — that's expected; hit `http://localhost:80`.

---

## Deployment

Production pods run on an Infomaniak VPS in Zürich, managed via Docker Compose. The `bunzli-app` pod is the public-facing one.

```bash
# Ship .env if it changed:
scp .env bunzli@<vps>:/home/bunzli/zueribot/.env

# Pull + rebuild:
ssh bunzli@<vps> 'cd ~/zueribot && git pull && cd deploy/pods/app && docker compose up -d --build'

# Smoke-test:
curl -sS -o /dev/null -w "site: %{http_code}\n" https://buenzli.space/
curl -sS -o /dev/null -w "api:  %{http_code}\n" https://buenzli.space/zuribot/health
```

Secrets live in the repo-root `.env`, never committed. See [`.env.example`](.env.example) for required keys, [docs/infrastructure.md](docs/infrastructure.md) for the full operational picture, and per-pod READMEs under [`deploy/pods/`](deploy/pods/) for pod-specific deploy notes.

Pre-deploy rule: any change to a pod's compose / Caddyfile / Dockerfile / env layout must be brought up on Docker Desktop locally first. Reason: we shipped the pod restructure straight to prod once and took the site down for five minutes.

---

## Cost model

- **Free tier** — casual use stays free during and after beta.
- **Subscription tier** — CHF-scale monthly fee for heavy users, only if someone opts in.
- **No ads. Ever.**

A 70B open-weight model served per-token via Infomaniak is cheap enough that current beta usage sits comfortably inside a personal budget. Serving cost analysis: [docs/token_cost_strategy.md](docs/token_cost_strategy.md).

---

## On using AI to build it

Most of Bünzli was written with Claude as a pair programmer. The tooling is Anthropic's; the product is Swiss. The inference, storage, jurisdiction, and live user data — the things that matter for the privacy claim — are Swiss-hosted end to end.

---

## Contributing

PRs welcome, especially:

- New connectors for public Zürich / Swiss data sources
- Swiss German / Züridütsch improvements
- Prompt + eval additions
- Security reviews

Please don't open PRs that add tracking, analytics, or cross-border data flows — they conflict with the design goals and will be closed.

---

## Contact

- Product: **[buenzli.space](https://buenzli.space)**
- Email: **sali@buenzli.space**

## License

MIT. See [`LICENSE`](LICENSE).
