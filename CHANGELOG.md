# Changelog

User-facing and operational changes to Bünzli, newest first.

The README's **Status** table is the snapshot. This file is the running log.

Format: each entry is dated (`YYYY-MM-DD`), one short heading, two or three bullets of *what shipped* and *why it mattered*. Internal-only refactors don't belong here — they belong in `git log`.

---

## 2026-04-26 — Pod-based deployment + ops cleanup

- Restructured Docker layout into `deploy/pods/<pod>/` with a clear naming convention (`bunzli-app`, `bunzli-app-iam`, `bunzli-gpu`).
- Cleaned ~33 GB of stale build cache and abandoned containers across prod VPS and laptop.
- Codified "test pod compose locally before deploying" — caught after a 5-minute prod outage from an untested Caddyfile change.
- New: [docs/infrastructure.md](docs/infrastructure.md), per-pod READMEs, Docker contexts for remote ops without SSH-quoting.

## 2026-04-25 — Knowledge base Phase 1 sealed

- 41,714 chunks ingested across 10 categories (federal/cantonal law, city services, transport, civic life, history, culture, …).
- Acceptance audit passed; corpus frozen pending Phase 2 embedding on the GPU pod.
- Quality-over-volume curation: history sources kept for *voice*, not as a Q&A reference.

## 2026-04-24 — Staging environment spec

- Decided on Infomaniak A2 GPU instance + Qwen 2.5 7B Q4_K_M via llama.cpp for free local iteration.
- Production traffic continues to Apertus 70B (voice) + Mistral 7B (tool calls) via Infomaniak AI Tools.

## 2026-04-23 — Orchestration v1 design

- Architecture decision: code-orchestrated, **no LangChain**, no local SLM in v1.
- Routing split: Apertus for voice, Mistral for tool calls, browser-local state.
- Token cost strategy documented in [docs/token_cost_strategy.md](docs/token_cost_strategy.md).

## 2026-04 — Knowledge base rebuild kicked off

- From-scratch rebuild: 2 collections, 10-category taxonomy, news + directories explicitly out of scope.
- Phase 1 ingesters built incrementally: ch.ch → stadt-zuerich.ch → zh.ch → Wikipedia + federal law PDFs → ZVV + easyvote → cantonal law → zuerich.com → Quartiervereine + MV-ZH.

## 2026-03 — Landing site live

- Public landing at [buenzli.space](https://buenzli.space) with two locales (DE / CH-DE).
- Closed-beta sign-up via email gate, ~50 seats.
- Caddy + Astro + FastAPI on a single Infomaniak Zürich VPS.

---

## Conventions

- One entry per shipped change set (PR or session). Squash multiple commits, don't log each one.
- Phrase from the *user's* perspective where possible. "Faster page load" beats "switched to Astro view transitions."
- Internal cleanups, refactors, and one-off scripts: skip. Use `git log` for those.
- Convert relative dates to absolute when writing.
- Keep entries short — three bullets max. Detail belongs in linked docs or PRs.
