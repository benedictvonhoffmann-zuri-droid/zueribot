# Orchestration architecture

**Status:** Proposed — drafted 2026-04-25, pending Benedict's sign-off.
**Scope:** How user messages flow through models and tools in Bünzli's runtime.
**Supersedes:** Nothing yet. This is the first written architecture decision for the runtime layer.
**Companion docs:** [token_cost_strategy.md](token_cost_strategy.md) — per-turn cost math and levers.

---

## TL;DR

Two cloud models (Apertus for voice, Mistral for tool-calling) coordinated by **plain Python code** running inside the existing FastAPI backend. The local GPU runs only retrieval components (embedding model, reranker, Qdrant) — no LLM. We deliberately defer adding a local small language model (SLM) as orchestrator until we hit a concrete problem that code cannot solve.

This is **v1**. A local SLM orchestrator (Qwen3 family) is **v3** in the roadmap, not v1.

---

## What we're choosing between

Two architectures were on the table:

| | Option A: SLM orchestrator (original) | **Option B: Code orchestrator (this doc)** |
|---|---|---|
| Components | Local SLM + Apertus + Mistral + embed + rerank + Qdrant | Apertus + Mistral + embed + rerank + Qdrant |
| Latency hops | 3 model calls (SLM → Mistral → Apertus) | 2 model calls (Mistral → Apertus polish) |
| VRAM pressure | Tight if SLM upgrades to 4B | Plenty of headroom |
| Failure if GPU dies | Bot down (or complex fallback) | RAG degrades; bot still talks |
| Eval surface | 3 prompts × N model versions | 2 prompts |
| Debuggability | SLM decisions opaque, prompt-tuned | Switch-statement, fully traceable |

We are picking Option B for v1. Option A's strengths (PII scrubbing on-prem, prompt compression, smart routing) solve problems Bünzli does not yet have at user volumes we do not yet have. Building it now is a debugging tax with no measurable user benefit.

---

## Architecture (v1)

```
User
  │
  ▼
FastAPI request handler
  │
  ▼
Orchestrator (Python function, deterministic)
  │
  ├── load conversation state
  ├── load Swiss German glossary
  ├── (optional) PII scrub via regex / Presidio
  │
  ├── classify intent ──► switch statement
  │     │
  │     ├── [knowledge]  embed → Qdrant search → rerank
  │     │                          │
  │     │                          ▼
  │     │                  Mistral(prompt + top-k context, with tool schemas)
  │     │                          │
  │     │                          ├── if tool_call → exec tool → loop back to Mistral
  │     │                          ▼
  │     │                  intermediate answer (English or mixed)
  │     │
  │     ├── [action]      Mistral(tool schemas only) → tool exec → narration draft
  │     │
  │     └── [chitchat]    skip Mistral; build prompt directly
  │
  ▼
Apertus("polish into natural Swiss German", + intermediate answer + glossary)
  │
  ▼
stream tokens to user
```

The orchestrator is a single Python module. Its job is pre-LLM preparation, post-LLM stitching, and the switch statement that decides which path a turn takes.

---

## Components

### Cloud models (Infomaniak AI API)

- **Apertus 70B Instruct** — voice. Receives a prepared draft answer + glossary and rewrites in natural Swiss German. Streams to the user. Never sees raw user input or tool schemas.
- **Mistral Small 3.2 24B** — tool-caller and reasoner. Sees user query, retrieved context, and tool schemas. Does the actual thinking. Never speaks to the user.

### Local (single GPU on VPS)

- **EmbeddingGemma 300M** — text → vector for similarity search.
- **BGE-reranker-v2-m3** — reorders top-K Qdrant hits by relevance.
- **Qdrant** — vector store for the Zürich knowledge base (Phase 1 sealed at 41,714 chunks, 2 collections).

No LLM runs locally **in production** in v1. The staging environment hosts a small LLM for testing — see "Staging environment" below.

### Orchestrator (Python, in FastAPI process)

- Stateful per-conversation (memory in Postgres or Redis — TBD, see open questions).
- Owns the Swiss German glossary injection.
- Owns intent classification (initially: keyword + regex, upgradeable to a small classifier).
- Owns the tool-execution loop.
- Emits trace IDs across all downstream calls.

---

## Tech stack

### Recommended (v1)

| Concern | Choice | Why |
|---|---|---|
| LLM API client | `openai` Python SDK pointed at Infomaniak's OpenAI-compatible endpoint | Direct, debuggable, no abstraction layer to leak |
| Tool calling | Native Mistral function calling via the OpenAI SDK schema | Already supported by the SDK, no framework needed |
| Vector search | `qdrant-client` | Direct |
| Embeddings + reranker | Run as small FastAPI services on the GPU host, called over HTTP | Decouples model serving from app process |
| Conversation state | Postgres (already in stack) | One less moving piece than Redis for v1 volumes |
| HTTP client | `httpx` | Already in FastAPI ecosystem |
| Observability | OpenTelemetry traces with one trace ID per user turn | Required for debugging multi-hop turns |

### Considered and rejected

- **LangChain / LangGraph.** Heavy dependency, opinionated abstractions, frequent breaking changes. Earns its weight when composing many chains, agents, or memory backends — we have one orchestrator function and two model calls. Adds debugging cost without solving a problem we have. Reconsider only if v3's agent loop genuinely needs graph-based control flow we cannot express in code.
- **LlamaIndex.** RAG-focused. We are already building our own RAG pipeline (Phase 1 ingesters shipped) — adopting LlamaIndex would mean re-doing it.
- **Pydantic AI.** Newer, cleaner, type-safe. Plausible alternative if we want stronger typing on tool I/O. Worth revisiting at v2.
- **LiteLLM.** Thin model-gateway layer. Useful only if we want to swap providers without code changes. Defer until we have a reason to swap.

---

## What we lose vs. the SLM-orchestrator plan

Honest accounting of what Option B does not give us:

1. **On-prem PII scrubbing before API calls.** Mitigation: a regex / Presidio pass in Python is ~80% of the value and fully deterministic. Genuine on-prem semantic scrubbing waits for v3.
2. **Aggressive prompt compression by SLM.** Mitigation: Bünzli's user turns are short tourist questions. There is little to compress. Reassess if average input length grows.
3. **"Smart" intent routing.** Mitigation: a switch statement on intent covers the realistic traffic mix for v1. Add an SLM the day this assumption breaks (see "When we'd add the SLM" below).

---

## When we'd add the local SLM (v3 trigger criteria)

We commit now to **not adding** a local SLM orchestrator until at least one of these is observed in production:

- Conversation memory regularly exceeds what naive windowed truncation handles well, and we see quality degradation on long sessions.
- Intent routing logic in the switch statement passes ~10 branches and keeps growing.
- A compliance or contractual requirement forces semantic PII scrubbing on-prem (regex is not enough).
- Cost telemetry shows that prompt-prep token savings would clearly outweigh GPU + ops cost at current traffic.

If/when triggered, the SLM slots into the existing orchestrator as a **prompt-prep step**, not a replacement. The switch statement stays.

---

## Resolved decisions (2026-04-25)

1. **Streaming.** Apertus tokens stream directly to the user. No buffering. Apertus is polishing a complete draft, so mid-stream surprises are rare.
2. **Time-to-first-token target: ~3 seconds.** Constrains retrieval depth and rerank-K. Sub-2s is unrealistic with two API hops; over-5s feels broken.
3. **Conversation state lives in the browser (localStorage), not on the server.** The backend is stateless across turns. The frontend sends the conversation history with each request; the orchestrator builds a fresh prompt every turn.
   - **Implication — token cost.** History grows with the conversation. We need a truncation strategy: keep last N turns, or token-budget the history (e.g. last ~3K tokens), with the system prompt + glossary always pinned.
   - **Implication — no multi-device continuity.** Deliberate. Different browsers = different histories. Treated as a privacy feature, not a bug.
   - **Implication — clearing browser clears history.** Deliberate. Same framing.
   - **Implication — no server-side chat logs by default.** Strong privacy story we should communicate. Logging for analytics/debugging needs explicit opt-in or anonymized telemetry only.
   - **Open sub-question:** truncation strategy specifics (turn-count vs. token-budget vs. summarization). Decide at implementation time.
4. **Failure mode: fail closed.** If Mistral is slow or unavailable, return a "try again" message. No silent fallback to Apertus-direct, which would produce wrong-but-confident answers without RAG or tools.
5. **Glossary injection: Apertus only.** Mistral reasons better in English; injecting Swiss German terms is likely net-negative. Revisit with an A/B once running.
6. **v1 scope: chitchat + RAG only.** Tool calling lands as v1.1 once the orchestrator skeleton is proven.

## Open questions (still unresolved)

- **Connectors as tools vs. live widgets.** Some integrations (e.g. transit, ERZ schedules, Quandoo) may belong as live UI widgets rendered alongside the chat rather than as tool calls invoked by Mistral. To be decided per-connector during v1.1 planning. Likely split: information-display connectors → widgets; action-taking connectors (booking, reporting) → tool calls.
- **History truncation strategy** (see decision 3).

---

## Staging environment (v1 budget tier)

Bünzli will run a single Infomaniak Public Cloud GPU instance that hosts the retrieval stack (embeddings, reranker, Qdrant) **and**, in staging, a small LLM. Staging is a real, independent environment that mirrors the prod orchestrator but uses a self-hosted LLM in place of Infomaniak's hosted Mistral, so we can iterate on prompts, run evals, and load-test without burning Infomaniak credits.

### Hardware

| Spec | Value |
|---|---|
| GPU | NVIDIA A2 (16GB VRAM) |
| vCPU | 4 |
| System RAM | 8GB |
| Disk | 50GB |
| Provider | Infomaniak Public Cloud (`a2-` prefixed flavor) |

This is the cheapest tier that fits the workload. **System RAM is the binding constraint**, not VRAM.

### What runs on this box

| Component | VRAM | RAM |
|---|---|---|
| EmbeddingGemma 300M | ~0.6 GB | ~0.5 GB |
| BGE-reranker-v2-m3 | ~2.3 GB | ~0.5 GB |
| Qdrant (knowledge base) | 0 | ~1–2 GB |
| Linux + service overhead | 0 | ~1 GB |
| Staging LLM (Qwen2.5-7B-Instruct, Q4_K_M) | ~5 GB | ~0.5 GB (mmap) |
| **Total** | **~8 GB** | **~3.5–4.5 GB** |

VRAM has comfortable headroom. Host RAM is tight — we'll need to monitor pressure in practice.

### Staging LLM choice

- **Model:** [Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) in **GGUF Q4_K_M** quantization (~4.5 GB on disk).
- **Why this model:** strongest 7B-class general-purpose model in 2026 for our workload — solid OpenAI-compatible function calling, multilingual (incl. German), good structured output.
- **Why this quantization:** Q4_K_M is the size/quality sweet spot. ~4× smaller than FP16 with negligible quality drop for inference.
- **Why a 7B and not Mistral 24B:** Mistral 24B Q4 (~14 GB on disk) doesn't load reliably on 8 GB host RAM under our serving stack. We accept the parity gap and cover it with periodic Infomaniak free-credit runs (see "Bridging the parity gap").

### Serving stack

| Concern | Choice | Why |
|---|---|---|
| LLM inference | **llama.cpp** in `server` mode | Memory-mapped weight loading; low host-RAM footprint. Fits 8 GB system RAM where vLLM would not. Exposes an OpenAI-compatible HTTP endpoint. |
| Embeddings + reranker | Small FastAPI processes | Same as production. |
| Qdrant | Containerized | Tune mmap settings to keep payload off RAM. |
| All services | Run as systemd units with memory limits | Defensive — prevents one runaway service from OOM-killing another. |

The orchestrator points its `base_url` at the staging GPU box for staging runs, and at Infomaniak for production. **No code changes between environments** — the OpenAI-compatible API surface is identical.

### What staging can and cannot test

| Can test end-to-end | Cannot test (still needs prod / Infomaniak) |
|---|---|
| Orchestrator logic + intent routing | Apertus voice quality |
| RAG pipeline (embed → Qdrant → rerank) | Swiss German fluency end-result |
| Tool-call loop and function-calling shape | Mistral-24B-specific reasoning quirks |
| Prompt regression tests | Infomaniak rate limits and any prompt-caching behavior |
| History truncation behavior | Real-network latency budget |
| Token-counting and telemetry instrumentation | |
| Load shape / orchestrator stability | |

This covers most of the bug surface. The voice and reasoning-fidelity gaps are real but bounded.

### Bridging the parity gap

Infomaniak's free 1M-credit/month tier covers periodic prod-parity runs. The plan:
- Day-to-day prompt iteration and eval loops → staging box (unlimited volume, no cost).
- Weekly or pre-deploy regression sweep → run the full orchestrator against Infomaniak's hosted Mistral 24B + Apertus 70B to catch model-fidelity regressions.
- 1M credits comfortably covers a full regression sweep plus headroom.

### Risks and escape hatches

- **Memory pressure.** 8 GB RAM with four services is tight. Mitigations: swap, Qdrant mmap tuning, llama.cpp thread/ngl tuning. **Escape hatch:** if it's painful in practice, drop the local LLM and use Infomaniak free credits for everything. Embed + reranker + Qdrant alone are comfortable on this box.
- **7B ≠ 24B for tool-calling reliability.** Some bugs only surface at 24B. **Escape hatch:** the parity-bridging weekly Infomaniak run catches those. If the gap becomes too noisy, upgrade the staging box to NVIDIA L4 + 16 GB RAM (one flavor change, no architectural rework).
- **Operational surface grows.** Four services on one box vs. zero. **Mitigation:** containerize everything; automate provisioning so staging can be torn down and recreated cheaply.

### Discipline

This is a **dev/eval/staging tool**, not the local orchestrator we deferred to v3. Specifically:
- The staging LLM is **never** called from a user-facing path.
- It is **not** a production fallback if Infomaniak goes down.
- It does **not** drift into v3 territory by stealth. If we ever want it user-facing, that's a separate architecture decision.

---

## Implications for the rest of the stack

- **One new GPU box for v1: the staging environment** (NVIDIA A2 / 4 vCPU / 8 GB RAM / 50 GB disk on Infomaniak Public Cloud). Hosts embed + reranker + Qdrant for both staging *and* production retrieval, plus a self-hosted LLM in staging only. Production LLM calls go to Infomaniak's hosted models. Detail in the "Staging environment" section above.
- **The Qwen3 family stays in the roadmap, not the build plan.** Document them as "v3 candidates" but do not provision for them.
- **`.env` additions:** `INFOMANIAK_API_KEY`, `INFOMANIAK_BASE_URL`, `APERTUS_MODEL_ID`, `MISTRAL_MODEL_ID`, `QDRANT_URL`, `EMBED_SERVICE_URL`, `RERANK_SERVICE_URL`. All to be added to `.env.example` when implementation begins.
- **Knowledge base.** Phase 1 is sealed (41,714 chunks). Phase 2 (embed + Qdrant ingest) is the prerequisite for the [knowledge] path of this orchestrator.

---

## Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-04-25 | Use code, not an SLM, as v1 orchestrator | Lower complexity, fewer failure modes, problems an SLM solves are not yet real for Bünzli |
| 2026-04-25 | Use plain Python + OpenAI SDK; reject LangChain | Framework cost not justified for two model calls and a switch statement |
| 2026-04-25 | Local GPU runs retrieval only in v1 | Keeps VRAM headroom; LLM hosting deferred |
| 2026-04-25 | Stream Apertus tokens directly | Better perceived latency; mid-stream surprises rare |
| 2026-04-25 | TTFT target ~3s | Honest budget given two API hops |
| 2026-04-25 | Conversation state in browser localStorage, server stateless | Privacy feature; no server-side chat logs by default |
| 2026-04-25 | Fail closed on Mistral failure, no Apertus fallback | Wrong-but-confident answers worse than a retry message |
| 2026-04-25 | Glossary injected into Apertus only | Mistral reasons better in English |
| 2026-04-25 | v1 = chitchat + RAG; tools deferred to v1.1 | Smallest provable orchestrator skeleton first |
| 2026-04-26 | Staging on Infomaniak A2 / 4vCPU / 8GB RAM / 50GB disk | Cheapest tier that fits embed + reranker + Qdrant + a 7B-class staging LLM |
| 2026-04-26 | Staging LLM = Qwen2.5-7B-Instruct, Q4_K_M GGUF, served by llama.cpp | Best 7B for tool calling; llama.cpp fits 8GB host RAM where vLLM would not |
| 2026-04-26 | Accept staging-prod parity gap; bridge via weekly Infomaniak free-credit runs | 7B ≠ 24B; periodic full-stack runs against hosted Mistral catch fidelity regressions |
| 2026-04-26 | Staging LLM is never user-facing | Discipline; prevents drift into the v3 local-orchestrator we deferred |
