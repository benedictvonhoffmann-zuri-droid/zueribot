# `bunzli-gpu` pod

Retrieval stack (embed + reranker + Qdrant) plus a **staging-only** LLM.
Runs on a dedicated Infomaniak Public Cloud GPU instance at
`gpu.buenzli.space`.

> **Status:** scaffold only as of 2026-04-26. The compose stack and
> Dockerfiles are drafted in [Stage B of the orchestration buildout](../../../docs/orchestration_architecture.md#staging-environment-v1-budget-tier).
> Bringing this pod up is the next operational step.

## Services (target state)

| Service | Container | Role | Used by |
|---|---|---|---|
| `embed` | `bunzli-gpu-embed` | EmbeddingGemma 300M behind FastAPI. Applies the doc-side and query-side prompt formats server-side so callers can't forget. | prod + staging |
| `rerank` | `bunzli-gpu-rerank` | BGE-reranker-v2-m3 behind FastAPI. | prod + staging |
| `qdrant` | `bunzli-gpu-qdrant` | Vector database. Two collections: `zurich_kb`, `zurich_law`. | prod + staging |
| `llm` | `bunzli-gpu-llm` | llama.cpp serving Qwen2.5-7B-Instruct Q4_K_M, OpenAI-compatible API. | **staging only** |
| `edge` | `bunzli-gpu-edge` | nginx in front of all the above, TLS via ACME, basic auth on internal endpoints. | prod + staging |

## Hardware

NVIDIA A2 (16 GB VRAM) / 4 vCPU / 8 GB RAM / 50 GB disk on Infomaniak
Public Cloud. See
[orchestration_architecture.md §Staging environment](../../../docs/orchestration_architecture.md#staging-environment-v1-budget-tier)
for the rationale and budget math.

## Discipline

- The `llm` service is **never** called from a user-facing path. Its
  only consumer is the orchestrator running in staging mode.
- `embed`, `rerank`, and `qdrant` are shared by both production and
  staging. Production calls them from the `bunzli-app-api` pod over
  HTTPS with basic auth.
- This pod is **not** a production fallback if Infomaniak's hosted
  models go down. Failures fail closed.
