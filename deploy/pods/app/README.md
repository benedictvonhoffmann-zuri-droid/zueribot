# `bunzli-app` pod

Public-facing application stack. Runs on the Infomaniak VPS at
`83.228.227.247`. Serves [buenzli.space](https://buenzli.space).

## Services

| Service | Container | Image | Role |
|---|---|---|---|
| `edge` | `bunzli-app-edge` | `caddy:2` | TLS termination, reverse proxy, ACME |
| `api` | `bunzli-app-api` | Built from repo root `Dockerfile` | FastAPI backend (`api_server.py`) — handles `/zuribot/*` |
| `landing` | `bunzli-app-landing` | Built from `Dockerfile.landing` | nginx serving the Astro static site at the root |

Edge proxy routing:

```
buenzli.space/             → landing:80
buenzli.space/zuribot/*    → api:8000 (prefix stripped by Caddy)
www.buenzli.space          → 301 → buenzli.space
```

Network: `bunzli-app-net` (bridge, internal-only).

## Env

All env vars live in **one place**: the repo-root `.env`. Both the
`edge` and `api` services read it via `env_file: ../../../.env`.
There is **no per-pod `.env`** for `bunzli-app` — keep it that way.

Required keys (see top-level `.env.example` for the full list):

- `ACME_EMAIL` — Let's Encrypt registration, used by Caddy.
- `ANTHROPIC_API_KEY`, `LLM_*`, `SMTP_*`, `EVENTFROG_KEY` — consumed by the API.

## Deploy

From your laptop:

```bash
# 1. If .env changed, ship it first:
scp /Users/benedictvonhoffmann/zuribot/.env bunzli@83.228.227.247:/home/bunzli/zueribot/.env

# 2. Pull and rebuild on the VPS:
ssh bunzli@83.228.227.247 'cd ~/zueribot && git pull && cd deploy/pods/app && docker compose up -d --build'

# 3. Smoke-test:
curl -sS -o /dev/null -w "site: %{http_code}\n" https://buenzli.space/
curl -sS -o /dev/null -w "api:  %{http_code}\n" https://buenzli.space/zuribot/health
```

## Local dev

For UI work, run Astro and FastAPI directly on your laptop (faster than
rebuilding the container). To exercise the full stack with TLS, run the
pod locally:

```bash
docker compose -f deploy/pods/app/docker-compose.yml up -d --build
```

Caddy will fail to issue real certs for `buenzli.space` from your
laptop — that's expected. For local TLS, override the Caddyfile or
hit `http://localhost:80` directly.

## Troubleshooting

- `docker compose -p bunzli-app logs -f edge` — Caddy logs (TLS issues, routing).
- `docker compose -p bunzli-app logs -f api` — FastAPI logs.
- `docker compose -p bunzli-app ps` — current state.
- Build cache eating disk: `docker builder prune -af` on the host.
