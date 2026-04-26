# README & CHANGELOG maintenance guide

The `README.md` at the repo root is **the** front door for visitors who don't know Bünzli — recruiters, collaborators, security reviewers, anyone landing here from a LinkedIn post. It has to read like a serious project on day one and stay accurate as the system evolves.

This document explains the structure, who it's for, and how to keep it from drifting.

---

## Audiences (in priority order)

1. **Recruiters / hiring managers.** Skim the top third in 90 seconds. Need to come away with: *what is this, what does it run on, what decisions were made, is this person serious.*
2. **Technical collaborators.** Read the architecture and stack tables. Need: *can I run it locally, where do I open a PR, what's the deploy story.*
3. **Security / privacy reviewers.** Jump straight to **Privacy** and **Security posture**. Need: *concrete claims they can verify, not marketing.*
4. **Future-Benedict and future-Claude.** Need: *current truth, not aspirational copy.*

If a section doesn't serve at least one of these audiences, cut it.

---

## Structure (what each section is for)

| Section | Purpose | Update trigger |
|---|---|---|
| Lede + tagline | One-sentence pitch + verifiable privacy claim | Only on real positioning shifts |
| **Status table** | At-a-glance current state, recruiter-friendly | Every shipped change that moves a row |
| **Why** | Four constraints that drive decisions | Rarely — only if a constraint actually changes |
| **Architecture** + diagram | What runs where; pods table; stack table | Any pod or stack change |
| **Privacy, concretely** | Specific claims, not slogans | When a claim's mechanism changes |
| **Security posture** | What's in place vs. planned | When something moves from "planned" to "live" |
| **Connectors** | Live data sources by domain | When a connector lands or is removed |
| **Knowledge base** | RAG corpus state in plain language | At each phase boundary |
| **Roadmap** | Near / medium / longer term | After each shipping cycle |
| **Repository layout** | Tree of where things live | When directory structure shifts |
| **Running locally** | Reproducible getting-started | When dev setup changes |
| **Deployment** | Single pod-deploy command + smoke test | When the deploy command changes |
| **Cost model** | Honest serving-cost framing | Rarely |
| **On using AI to build it** | Disclosure | Don't touch |
| **Contributing / Contact / License** | Boilerplate | Don't touch |

---

## The Status table is load-bearing

It's the recruiter-facing dashboard. Every row is one of: **Live**, **Staged**, **In progress**, **Designed**, **Sealed**, or a date target.

Rules:
- A row goes to **Live** *only after* the thing is deployed and reachable.
- Move rows promptly — a stale "In progress" that's actually live makes the project look dead.
- Don't add aspirational rows. If it's not started, it belongs in **Roadmap**, not **Status**.

---

## CHANGELOG.md

The README is a snapshot; the CHANGELOG is the running log. They share work:

- **Status table** answers *where are we now.*
- **CHANGELOG** answers *what changed recently and why it mattered.*
- **Roadmap** answers *where are we going.*

When you ship something user-visible, write the CHANGELOG entry **and** update the Status row in the same PR.

CHANGELOG conventions are at the bottom of [`CHANGELOG.md`](../CHANGELOG.md). Short version: one entry per shipped change set, three bullets max, user-perspective phrasing, drop pure refactors.

---

## Update workflow

After each shipped change, before merging the PR:

1. **Status table** — does any row need to move?
2. **Architecture / Stack table** — did the actual stack change? Update the row, not just the prose.
3. **Roadmap** — promote near-term items that landed; demote / delete cancelled ones.
4. **CHANGELOG** — new dated entry at the top.
5. **Re-read the lede.** It tends to drift quietly. The privacy claim must still be defensible.

If a session changed the deploy story, also update the per-pod READMEs under `deploy/pods/` and `docs/infrastructure.md`. Those are the operational sources of truth — the README's Deploy section is the *summary*, not the manual.

---

## Anti-patterns

- **Aspirational copy.** "Bünzli will use X" instead of the truth, "Bünzli is designed to use X, build pending GPU pod." Recruiters can smell this.
- **Stack name-dropping without rationale.** Every row in the Stack table has a *why* column. Keep it that way.
- **Marketing language for privacy.** Replace with concrete, verifiable mechanisms.
- **Letting the diagram drift.** If a pod's added or moved, the ASCII diagram is wrong within a week. Fix it in the same PR.
- **Bundling README updates into unrelated PRs.** Either ship the doc with the change that motivates it, or as its own dedicated docs PR — never as a stale afterthought.
- **Two sources of truth.** If it's in [`docs/infrastructure.md`](infrastructure.md), don't duplicate it in the README — *link* to it.

---

## When in doubt

Read the README cold. If the Status table doesn't match what's actually live, fix that first. Everything else can wait.
