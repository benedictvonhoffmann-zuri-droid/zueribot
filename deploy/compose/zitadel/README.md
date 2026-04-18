# Zitadel — self-hosted auth

Minimal Zitadel stack for Bünzli. Runs independently of the main
`deploy/docker-compose.yml` stack so it can be started, stopped, and
redeployed on its own.

## What's in the box

Upstream files, verbatim, pinned to `ZITADEL_VERSION=v4.13.0` in
`.env.example`. Snapshot taken from
<https://github.com/zitadel/zitadel/tree/main/deploy/compose>.

- `docker-compose.yml` — Traefik + Zitadel API + Zitadel Login UI + Postgres.
  Redis and OTEL collector are opt-in profiles we don't enable.
- `.env.example` — pinned image tags and insecure-for-local defaults.
- `.env` — your local copy. Git-ignored.

## Run locally

```sh
cd deploy/compose/zitadel
cp .env.example .env
docker compose --env-file .env up -d --wait
```

Then open <http://localhost:8080> and log in with the default admin:

- User: `zitadel-admin@zitadel.localhost`
- Pass: `Password1!`

First thing to do: change that password, then create the Bünzli project
+ apps (see "Configure apps" below).

## Stop / reset

```sh
# Stop (keeps data)
docker compose --env-file .env down

# Nuke everything including Postgres volume
docker compose --env-file .env down -v
```

## Configure apps (one-time, in the admin console)

1. **Project**: create project "Bünzli".
2. **Web app (User Agent / SPA, PKCE)** for the frontend:
   - Redirect URIs:
     - `http://localhost:4321/chat/auth/callback` (dev)
     - `https://buenzli.space/chat/auth/callback` (prod, later)
   - Post-logout URIs: `http://localhost:4321/chat/`, `https://buenzli.space/chat/`
   - Auth method: **PKCE**
   - Grant types: Authorization Code, Refresh Token
3. **API app** for the backend:
   - Auth method: **JWT** (download the signing key if needed; for JWT
     validation the backend just needs the issuer/JWKS URL).

Copy the client IDs into the app (frontend `.env`, backend config).

## Production on Infomaniak

Same compose, different env:
- `ZITADEL_DOMAIN=auth.buenzli.space`
- `ZITADEL_EXTERNALPORT=443`
- `ZITADEL_EXTERNALSECURE=true`
- `ZITADEL_PUBLIC_SCHEME=https`
- Bump `POSTGRES_ADMIN_PASSWORD` and `ZITADEL_MASTERKEY` to real secrets.
- Use an Infomaniak-issued TLS cert or Traefik's Let's Encrypt overlay
  (download separately from upstream — not included here yet).

## Upgrades

Bump `ZITADEL_VERSION` in `.env`, then:

```sh
docker compose --env-file .env -f docker-compose.yml pull
docker compose --env-file .env -f docker-compose.yml up -d --wait
```
