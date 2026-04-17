# Bünzli Self-Play Evals

Local, offline eval harness. No Claude in the loop — everything runs on Ollama.

## Models

- **Simulator** (`qwen2.5:7b`) — roleplays a Zürcher persona, drives a
  multi-turn conversation.
- **Subject** — live Bünzli at `http://localhost/zuribot/v1/chat/completions`.
- **Judge** (`qwen2.5:14b`) — rates each conversation on 6 axes and labels
  connector / KB gaps.

Override with `--sim-model`, `--subject-model`, `--judge-model`.

## One-shot

```bash
source venv/bin/activate
python -m evals.run --personas all --turns 4 --seeds-per-persona 2
# → evals/reports/YYYY-MM-DD_HHMM.md  +  evals/transcripts/*.jsonl

python -m evals.propose_improvements \
    --report evals/reports/YYYY-MM-DD_HHMM.md \
    --transcripts evals/transcripts/YYYY-MM-DD_HHMM.jsonl
# → evals/proposals/YYYY-MM-DD_HHMM.md
```

## Smoke test (fast, ~2 min once models are warm)

```bash
python -m evals.run --personas ana_kreis4 --turns 2 --seeds-per-persona 1
```

## Files

- `personas.yaml` — 12 personas spanning dialect/German/English/tourist with
  seed questions across all 21 connectors + KB topics.
- `simulator.py` — builds the persona system prompt, emits next user turn.
- `subject_client.py` — HTTP client to Bünzli.
- `judge.py` — grades full conversations (factual / grounding / register /
  helpfulness / refusal safety / tone) and labels patterns.
- `run.py` — orchestrator; writes report + jsonl transcripts.
- `propose_improvements.py` — reads report + transcripts, asks judge model
  to emit system-prompt diffs, KB-seed stubs, connector changes, new personas.

Nothing auto-applies — proposals are Markdown only. Review, then paste diffs.

## Non-goals

- No Claude-API calls.
- No auto-editing of live prompt / KB.
- No UI.
