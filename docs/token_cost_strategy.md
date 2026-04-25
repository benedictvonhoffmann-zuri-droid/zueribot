# Token cost strategy

**Status:** Proposed — drafted 2026-04-25, pending Benedict's sign-off.
**Companion to:** [orchestration_architecture.md](orchestration_architecture.md).
**Scope:** How we keep Bünzli's per-conversation cost predictable at any scale we realistically reach.

---

## TL;DR

A typical Bünzli knowledge turn costs roughly **CHF 0.003–0.004**, dominated by Apertus 70B (8× more expensive than Mistral). At 1,000 daily active conversations that's ≈CHF 30/day or **CHF ~900/month**. The cost shape is sensitive to history length and RAG context size — both controllable. Prompt caching is **not currently documented as supported by Infomaniak**, so we plan as if it isn't available and revisit if it becomes one.

---

## Pricing baseline (Infomaniak, 2026-04)

| Model | Input (CHF / 1M tokens) | Output (CHF / 1M tokens) | Role |
|---|---|---|---|
| Mistral Small 3.2 24B | 0.10 | 0.30 | Tool caller / reasoner |
| Apertus 70B Instruct | 0.70 | 2.50 | Voice / final output |

**Apertus is ~7× more expensive on input and ~8× on output than Mistral.** Because Apertus is the polish step on every visible reply, it dominates the bill. This is a deliberate trade-off (voice quality > cost), but it means cost optimization energy should focus on **what reaches Apertus**.

Source: Infomaniak AI Services pricing page, April 2026.

---

## Per-turn cost estimates

These are honest order-of-magnitude figures, not commitments. Real numbers come from telemetry once we ship.

### Knowledge turn (RAG path)

| Stage | Tokens | Cost (CHF) |
|---|---|---|
| Mistral input (history + glossary + RAG + user) | ~5,000 | 0.00050 |
| Mistral output (intermediate draft) | ~500 | 0.00015 |
| Apertus input (system + glossary + draft + user) | ~3,000 | 0.00210 |
| Apertus output (streamed reply) | ~300 | 0.00075 |
| **Total** | | **~0.00350** |

### Chitchat turn (skip Mistral)

| Stage | Tokens | Cost (CHF) |
|---|---|---|
| Apertus input | ~2,500 | 0.00175 |
| Apertus output | ~200 | 0.00050 |
| **Total** | | **~0.00225** |

### Action turn (tool call, v1.1+)

Comparable to knowledge turn, possibly higher — tool-call loops can run Mistral multiple times before producing the draft. Budget ~CHF 0.005–0.008 per turn.

### Per-conversation rough math

Assume 10 turns, mix of chitchat and knowledge: **~CHF 0.03 per conversation**.

| Daily active conversations | Daily | Monthly |
|---|---|---|
| 100 | CHF 3 | ~CHF 90 |
| 1,000 | CHF 30 | ~CHF 900 |
| 10,000 | CHF 300 | ~CHF 9,000 |

The 10K/day case is a "different conversation" — at that scale, prompt caching, model tiering, or a different deployment model become real questions.

---

## Levers we'll use in v1

### 1. History truncation in the orchestrator
The browser sends the full conversation; the orchestrator truncates before any model call.
- **Strategy:** token-budgeted history, target ~2K tokens, oldest turns dropped first.
- **Pinned regardless:** system prompt, Swiss German glossary, current user message.
- **Why this lever first:** linear-with-session-length cost is the biggest runaway risk. A 50-turn conversation without truncation could cost 5–10× a freshly capped one.

### 2. RAG context budget
- **Cap top-K** to 5–8 chunks after reranking.
- **Sentence-level truncation** for long chunks before injection.
- **Why:** the reranker exists precisely so we can be aggressive on K.

### 3. Skip Mistral on chitchat
Already in the architecture. Saves ~CHF 0.001 per chitchat turn (significant if chitchat is the majority of traffic, which it likely is for a tourism bot).

### 4. Cancel-on-disconnect
If the user closes the tab or navigates away mid-stream, cancel the upstream Apertus call. Abandoned conversations are real and waste real money — Apertus output is the most expensive line item.

### 5. Conversation-level token cap
Hard cap (suggest 50K total tokens per conversation across all model calls). At the cap, prompt the user to start a fresh chat. Protects against:
- Runaway sessions accumulating cost
- Adversarial users trying to drain credit
- Single conversations costing >CHF 0.10 invisibly
- Show visible how much memory they have left in the chat

### 6. Telemetry from day one
Per-turn log:
- conversation_id (anonymized)
- intent path taken
- input/output tokens per model
- estimated CHF cost
- end-to-end latency
- This would potentially also be something to show to the user. Think about it

This is the only way to validate the assumptions in this doc. Without it, every cost decision is a guess.

---

## Levers we'll *not* pull (and why)

| Lever | Why not |
|---|---|
| Use Mistral as voice for chitchat instead of Apertus | The voice *is* the product. Swiss German fluency from Apertus is the differentiator. Cost-saving here would erode the core value. |
| Skip Apertus polish for "factual" replies | Same reason. Inconsistent voice is worse than slightly higher cost. |
| Server-side conversation summarization with a small model | Re-introduces the local SLM we deferred. Becomes a v3 trigger, not a v1 fix. |
| Prompt caching design now | Not documented as supported by Infomaniak. Designing around an unconfirmed feature is premature. Revisit if support confirms or docs update. |

---

## Open items to confirm before launch

1. **Prompt caching support.** Open question with Infomaniak. If supported, the system prompt + glossary become near-free after the first call — meaningful savings on the Apertus input side. Action: ask Infomaniak support directly.
2. **Free tier.** Infomaniak gives 1M credits to test for one month. Useful for dev and load-testing without burning budget.
3. **Budget alarms.** Need a daily-spend Slack/email alert before we have real users. Even one runaway conversation in dev could cost meaningfully.
4. **Streaming cost accounting.** Confirm whether canceled streams on Infomaniak's side bill for delivered tokens only or for the full intended output. Affects the value of cancel-on-disconnect.

---

## What we'd revisit at scale (post-launch)

| Trigger | Action to consider |
|---|---|
| Average conversation length grows past 15+ turns | Switch from windowed truncation to summarization (likely SLM-based — see v3 in the orchestration doc) |
| Sustained >5K daily active conversations | Negotiate volume pricing with Infomaniak |
| Apertus costs dominate >80% of monthly bill | Re-examine voice strategy: Apertus only on first/important turns, Mistral with glossary on follow-ups (A/B carefully) |
| Prompt caching becomes available | Pin glossary aggressively, redesign prompt structure to maximize cache hits |
| Daily spend exceeds CHF 100 | Trigger a cost review before the next deploy |

---

## Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-04-25 | Plan v1 without prompt caching | Not documented as supported by Infomaniak; designing around unconfirmed features is premature |
| 2026-04-25 | Token-budget history truncation at ~2K tokens, oldest first | Single biggest cost lever for long sessions |
| 2026-04-25 | RAG top-K cap at 5–8 after rerank | Reranker exists to enable this |
| 2026-04-25 | Conversation-level hard cap at 50K total tokens | Protects against runaway and adversarial sessions |
| 2026-04-25 | Per-turn token telemetry from day one | Cost decisions need real data, not guesses |
| 2026-04-25 | Will not use Mistral as chitchat voice | Voice quality is the product differentiator |
