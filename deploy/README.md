# `deploy/` — pod-based deployment layout

Bünzli's runtime is split into **pods**. Each pod is an independent
Docker Compose stack that runs on its own host (or, in development, on
your laptop). Pods are versioned together with the rest of the repo so
you can deploy a pod without touching the others.

See [docs/infrastructure.md](../docs/infrastructure.md) for the full
architecture overview (which pod runs where, why, and how they connect).

## Pods today

| Pod | Path | Hosts | Purpose |
|---|---|---|---|
| `bunzli-app` | [`pods/app/`](pods/app/) | Existing Infomaniak VPS (`83.228.227.247`) | Caddy edge + FastAPI API + Astro landing |
| `bunzli-app-iam` | [`pods/app-iam/`](pods/app-iam/) | Same VPS as `bunzli-app` (separate stack, separate domain `auth.buenzli.space`) | Self-hosted Zitadel for auth |
| `bunzli-gpu` | [`pods/gpu/`](pods/gpu/) | New Infomaniak Public Cloud GPU instance (`gpu.buenzli.space`) | Embeddings, reranker, Qdrant — and a staging-only LLM |

Each pod has its own README with the env vars, deploy command, and
verification steps.

## Naming convention

Every container, network, and volume should be discoverable from its
name alone. The shape:

```
bunzli-<pod>-<service>
```

- `bunzli-app-edge` — Caddy on the app pod
- `bunzli-app-api` — FastAPI on the app pod
- `bunzli-gpu-embed` — embedding service on the GPU pod
- `bunzli-gpu-llm` — staging LLM on the GPU pod

This is enforced by setting `name: bunzli-<pod>` at the top of each
pod's `docker-compose.yml` and `container_name: bunzli-<pod>-<service>`
on each service.

## What does NOT live here

- **Application code.** Lives at the repo root (`api_server.py`,
  `backend/`, `frontend/`, `scripts/`). Pods consume it via build
  contexts and bind mounts.
- **Secrets.** `.env` files are gitignored. Each pod has an
  `.env.example` documenting the required variables.
- **One-off scripts.** Live in `scripts/` at the repo root.
