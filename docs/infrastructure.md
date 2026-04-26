# Infrastructure overview

How Bünzli's runtime is laid out across machines, what runs where, and
how the pieces talk to each other.

**Status:** Current as of 2026-04-26. Update when a pod is added,
removed, or moved between hosts.

---

## TL;DR

Bünzli runs on **two physical machines** (one VPS, one Public Cloud
GPU instance), each hosting one or more **pods**. A pod is a Docker
Compose stack that owns a coherent slice of functionality.

```
                                                        ┌─────────────────────────────┐
                                                        │  Infomaniak Public Cloud    │
   ┌──────────────────────────────────────────┐         │  GPU instance (A2, 8 GB)    │
   │  Infomaniak VPS (83.228.227.247)         │         │  gpu.buenzli.space          │
   │                                          │         │                             │
   │  ┌────────────────────────────────────┐  │ HTTPS   │  ┌───────────────────────┐  │
   │  │  bunzli-app pod                    │──┼─────────┼─▶│  bunzli-gpu pod       │  │
   │  │   - bunzli-app-edge (Caddy)        │  │         │  │   - bunzli-gpu-edge   │  │
   │  │   - bunzli-app-api (FastAPI)       │  │         │  │   - bunzli-gpu-embed  │  │
   │  │   - bunzli-app-landing (Astro)     │  │         │  │   - bunzli-gpu-rerank │  │
   │  └────────────────────────────────────┘  │         │  │   - bunzli-gpu-qdrant │  │
   │                                          │         │  │   - bunzli-gpu-llm *  │  │
   │  ┌────────────────────────────────────┐  │         │  └───────────────────────┘  │
   │  │  bunzli-app-iam pod (when live)    │  │         │   * staging traffic only    │
   │  │   - Traefik + Zitadel + Postgres   │  │         └─────────────────────────────┘
   │  └────────────────────────────────────┘  │
   └──────────────────────────────────────────┘
```

---

## Pods

A pod is **one Docker Compose project**. Naming: `bunzli-<pod>` for the
project and network, `bunzli-<pod>-<service>` for each container.

### `bunzli-app`

User-facing application stack.

- **Host:** Infomaniak VPS at `83.228.227.247`.
- **Domain:** `buenzli.space`, `www.buenzli.space`.
- **Path in repo:** [`deploy/pods/app/`](../deploy/pods/app/).
- **Why a pod:** Couples the things that have to be deployed together
  to ship a user-facing change: the edge proxy, the API, the landing
  site. Frontend changes rebuild `bunzli-app-landing`; API changes
  rebuild `bunzli-app-api`; both happen via the same `docker compose
  up -d --build`.

### `bunzli-app-iam`

Self-hosted authentication.

- **Host:** Same VPS as `bunzli-app`, separate Compose project.
- **Domain:** `auth.buenzli.space` (planned, not yet live).
- **Path in repo:** [`deploy/pods/app-iam/`](../deploy/pods/app-iam/).
- **Why separate from `bunzli-app`:** Zitadel ships its own Traefik,
  has its own database, and needs to be upgradeable independently.
  Bundling it into the app pod would couple unrelated lifecycles.

### `bunzli-gpu`

Retrieval stack and staging LLM.

- **Host:** Dedicated Infomaniak Public Cloud GPU instance (NVIDIA A2
  / 4 vCPU / 8 GB RAM / 50 GB disk).
- **Domain:** `gpu.buenzli.space`.
- **Path in repo:** [`deploy/pods/gpu/`](../deploy/pods/gpu/).
- **Why a separate machine:** The retrieval components (embeddings,
  reranker, Qdrant) need a GPU. Staging the LLM cheaply on the same
  box is a free side-benefit. Production LLM calls bypass this pod and
  go to Infomaniak's hosted models — see
  [orchestration_architecture.md](orchestration_architecture.md).

---

## Naming convention

| Thing | Pattern | Example |
|---|---|---|
| Compose project name | `bunzli-<pod>` | `bunzli-app` |
| Container | `bunzli-<pod>-<service>` | `bunzli-app-api` |
| Network | `bunzli-<pod>-net` | `bunzli-app-net` |
| Named volume | `bunzli-<pod>-<purpose>` | `bunzli-gpu-qdrant-data` |
| Domain (where applicable) | `<pod>.buenzli.space` | `gpu.buenzli.space` |

The `bunzli-app-iam` pod intentionally uses upstream Zitadel's network
name (`zitadel`) to keep the upstream compose snapshot diff-clean. All
container names are still prefixed `bunzli-app-iam-*` via the project
name.

---

## How pods communicate

- **Browser → `bunzli-app`:** HTTPS to `buenzli.space`, terminated at
  Caddy in `bunzli-app-edge`.
- **`bunzli-app-api` → `bunzli-gpu`:** HTTPS to `gpu.buenzli.space`,
  basic auth on the internal endpoints (`/embed`, `/rerank`,
  `/qdrant`). Configured via `EMBED_SERVICE_URL`,
  `RERANK_SERVICE_URL`, `QDRANT_URL` in the app pod's `.env`.
- **`bunzli-app-api` → Infomaniak hosted LLMs (Apertus, Mistral):**
  HTTPS to Infomaniak's API endpoint with `INFOMANIAK_API_KEY`.
- **Staging orchestrator → `bunzli-gpu-llm`:** HTTPS to
  `gpu.buenzli.space/llm`, OpenAI-compatible API. Same code path as
  production, only `base_url` differs.

---

## What's deliberately NOT a pod

- **CI / GitHub Actions.** Lives in `.github/workflows/`, runs on
  GitHub-hosted runners.
- **Local dev.** The Astro dev server and uvicorn run directly on the
  laptop — no Compose. Faster iteration, no rebuild cycle.
- **One-shot scripts** (`scripts/embed.py`, ingesters). Run from the
  laptop or the GPU box on demand, not as long-lived services.
