"""Per-source KB ingesters — Phase 1.

Each module is a small, focused ingester that knows one source. Runs
produce validated .jsonl under data/chunks/{category}/{source}/.

Build order per spec §15. Start with ch.ch (first JS-rendered source),
then federal law PDFs, then Quartierspiegel, then everything else.
"""
