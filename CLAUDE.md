# Bünzli — development & deploy process

This file is read automatically by Claude at the start of every session in this repo. Its job: make every session follow the same shape, instead of inventing the workflow each time.

---

## Project shape (one paragraph)

Bünzli is a Zürich-focused AI assistant. The repo holds a FastAPI backend (`api_server.py`, `backend/`), a static landing site (`frontend/landing/`, Astro + Tailwind, two locales), a chat frontend (`frontend/chat/`), and a Docker Compose deployment (`deploy/`) targeting a single Infomaniak VPS in Zürich. Operational details (VPS IP, SSH user, env layout, smoke-test commands) live in `DEPLOY_NOTES.md` at the repo root — gitignored, present on Benedict's machine.

---

## How we work

Benedict is a PM, not an engineer. That shapes everything below.

- **He won't read code or review PRs in detail.** Don't ask "does this look right?" — verify it yourself, then summarize what changed in plain language.
- **Never ask the user to do something verifiable yourself.** If a backend is running, hit its endpoint. If a UI changed, check it in preview. Only ask Benedict to do things only he can do (open Infomaniak panel, check his inbox, paste a password into `.env`).
- **State things in plain language.** Tables, short sentences, concrete file paths. Don't dump unexplained shell output.
- **Long detail-oriented sessions are the norm**, not the exception. Don't try to compress.

---

## Standard task flow

### 1. Plan before touching files

For anything beyond a one-line fix, write a short plan first (Skill: `/plan` or just structured text) covering:
- What the change is and why
- Files affected
- How it splits into commits
- How we'll verify it works

Get a yes from Benedict before implementing.

### 2. Work in a worktree

Sessions launched via the worktree mechanism already do this. If working directly in the main repo, create a worktree:

```bash
git worktree add .claude/worktrees/<name> -b claude/<name>
```

Never edit `main` directly.

### 3. Commit in small, focused chunks

Each commit should do one coherent thing. A typical landing-page polish session produces 3–5 commits, not one mega-commit. Commit message format:

```
Short imperative summary (under 70 chars)

Why this change exists, in plain language. What it changes, what it
doesn't. Any operational follow-up needed.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

### 4. Verify before claiming done

Match verification to what changed:

| Change type | How to verify |
|---|---|
| Landing/chat UI | `preview_start` → `preview_click` / `preview_fill` → `preview_snapshot` or `preview_screenshot`. **Check at mobile width too** (Benedict reviews on his phone). |
| Backend route | Start uvicorn locally, `curl` the route, read the response. |
| SMTP / external service | Run a real call, confirm Benedict received the side-effect (email, etc). |
| Translation/copy | Switch the locale in preview, eyeball the strings on the page. |

If you can't verify (e.g. needs Benedict's mailbox), say so explicitly. Don't claim success.

### 5. Push & merge

```bash
# From the worktree:
git push -u origin claude/<branch-name>

# Open PR:
gh pr create --title "..." --body "..."

# Merge (Benedict doesn't review — squash and delete branch):
gh api -X PUT repos/benedictvonhoffmann-zuri-droid/zueribot/pulls/<N>/merge \
  -f merge_method=squash \
  -f commit_title="<title> (#<N>)"

# Delete the remote branch:
gh api -X DELETE repos/benedictvonhoffmann-zuri-droid/zueribot/git/refs/heads/claude/<branch-name>
```

Note: `gh pr merge` locally fails with "main is already used by worktree" — use the API as above to bypass.

---

## Deploy

Anything user-visible needs a deploy. The standard sequence:

```bash
# 1. If .env changed, scp the new one:
scp /Users/benedictvonhoffmann/zuribot/.env bunzli@83.228.227.247:/home/bunzli/zueribot/.env

# 2. Pull & rebuild:
ssh bunzli@83.228.227.247 'cd ~/zueribot && git pull && cd deploy && docker compose up -d --build'

# 3. Smoke-test from your laptop:
curl -sS -o /dev/null -w "site: %{http_code}\n" https://buenzli.space/
curl -sS -o /dev/null -w "api:  %{http_code}\n" https://buenzli.space/zuribot/health
```

Full operational reference (paths, container names, troubleshooting) is in `DEPLOY_NOTES.md`.

**Confirm with Benedict before any deploy.** Even small ones — "this would touch the live site, OK to push and deploy?" Production isn't reversible without effort.

---

## Secrets & .env

- `.env` is gitignored at repo root. Real secrets only.
- `.env.example` is committed. Placeholders only — every variable the app reads must be listed here, with a comment if it's optional or has a default.
- When adding a new env var: update `.env.example` in the same commit as the code change, and remind Benedict to add the real value to his local `.env` and re-`scp` to the VPS.
- The Zitadel stack at `deploy/compose/zitadel/` has its own `.env` — same rules, different file.

---

## Memory system

Benedict's per-project memory lives at `~/.claude/projects/-Users-benedictvonhoffmann-zuribot/memory/`. The `MEMORY.md` index is loaded into every session automatically. Use it for:

- **User profile** (Benedict's role, preferred working style)
- **Project state** (decisions, deadlines, current initiatives — convert relative dates to absolute)
- **Feedback** (corrections AND validated approaches — explain the *why* so future sessions can apply it to edge cases)
- **References** (where info lives outside the repo — Linear projects, dashboards, the Infomaniak panel)

Don't store: code patterns (read the code), git history (use `git log`), debug fixes (the fix is in the commit).

Update memory when something changes — don't accumulate stale entries.

---

## End of session: refresh this file

Before wrapping a session, re-read this CLAUDE.md and update it if anything during the session changed the workflow, deploy process, tooling, or anti-patterns. The goal is to keep this file as the single source of truth — the next session should not have to rediscover things we already learned together. Small edits are fine; commit them alongside the session's work.

Same applies to `DEPLOY_NOTES.md` (gitignored) when operational details change: new container, new env var, new subdomain.

---

## Anti-patterns to avoid (learned the hard way)

- **Editing files in the main repo when you're supposed to be in a worktree.** Always check `pwd` before the first edit. If you've edited the wrong path, `cp` to the right one and `git checkout --` to revert main.
- **Claiming a feature works without testing it.** "The code looks right" is not verification.
- **Asking Benedict to do verifiable engineering steps.** He'll do it, but it wastes his time and breaks his trust that you're capable.
- **Bundling unrelated changes into one commit.** Each commit should be revertable on its own.
- **Adding 3rd-party services without explicit ask.** Benedict has rejected Formspree, mock backends, and similar shortcuts. Default to "build it on our own VPS" unless he says otherwise.
- **Skipping the plan step on non-trivial work.** A 30-second plan saves a 30-minute rewrite.
