# Bünzli Knowledge Base — Rebuild Spec

**Status:** Phase 1 ingesters complete — 22 of the planned ~25 target sources landed; remainder explicitly deferred (HLS, Stadt Zürich AS, a few dead-end directories). Ready for the §14 acceptance pass.
**Last updated:** 2026-04-25.
**Supersedes:** the current Chroma-based KB at `data/knowledge_base/` and `data/law_knowledge_base/`, which will be discarded once Phase 2 (Qdrant + embeddings) is live.

This document is the single source of truth for how Bünzli's knowledge base is structured, chunked, and annotated. Every ingest script must conform to this spec.

---

## 0. Progress tracker

Updated as ingesters land. `scripts/ingest/*.py` is the authoritative list of what exists today.

### Done (Phase 1 ingesters shipped)

| Source | Script | Categories | Authority |
|---|---|---|---|
| ch.ch — Bundesportal | `ch_ch.py` | admin, civic, housing, mobility, health | federal |
| stadt-zuerich.ch | `stadt_zuerich.py` | admin, housing, mobility, emergency, education, leisure, health | city |
| zh.ch (canton portal) | `zh_ch_canton.py` | admin, mobility, housing, health, emergency, education, civic, leisure | cantonal |
| Wikipedia (curated DE+EN) | `wikipedia.py` | leisure, neighborhoods, civic | wikipedia |
| Federal law PDFs (8 codes) | `law_pdfs.py` | law (statute) | federal |
| ZVV | `zvv.py` | mobility | cantonal |
| easyvote | `easyvote.py` | civic | community |
| Zürich cantonal law (LS) | `zh_cantonal_law.py` | law (statute) | cantonal |
| zuerich.com (Tourism) | `zuerich_com.py` | food_drink, leisure | private |
| bag.admin.ch | `bag_admin_ch.py` | health | federal |
| estv / sem / bsv | `admin_federal.py` | admin | federal |
| swissvotes.ch | `swissvotes.py` | civic | federal |
| parlament.ch | `parlament.py` | civic | federal |
| Tox Info Suisse | `emergency_refs.py` | emergency | federal |
| Museums + Badis | `leisure_refs.py` | leisure | community/city |
| Gault Millau + Harrys Ding | `food_drink_refs.py` | food_drink | community |
| Quartierspiegel (per-Kreis PDFs) ⭐ | `quartierspiegel.py` | neighborhoods | city |
| Stadtarchiv / Zürichs Geschichte ⭐ | `stadtarchiv.py` | leisure (history) | city |
| Mieterverband (CH + ZH) + HEV Schweiz | `housing_assoc.py` | housing | community |
| UZH / ETH / ZHAW / PHZH | `unis.py` | education | community |
| Quartiervereine (24 sites) | `quartiervereine.py` | neighborhoods | community |

Chunks go to `data/chunks/{category}/{source}/*.jsonl` (gitignored). Full crawls are deferred to the AI pod; what's in the repo are smoke-test runs.

### Deferred / dropped

Sources in §11 that we explicitly chose not to ingest, with the reason. Re-evaluate before Phase 2 acceptance.

- **HLS (Historisches Lexikon der Schweiz)** — Cloudflare blocks non-browser UAs and robots declares `ai-train=no` (attempted 2026-04-24). Re-attempt later via Playwright with respectful rate limiting, or skip permanently.
- **Stadt Zürich AS (Amtliche Sammlung)** — attempted 2026-04-25 via Playwright. Leaf pages (e.g. `/amtliche-sammlung/1/101.html` for the Gemeindeordnung) load only navigation chrome — the actual statute body is not in the rendered DOM. The AS is a pointer index, not the canonical text store. Deferred until we find the canonical municipal-law source.
- **Quartierverein Kreis 5 (Industriequartier)** — its domains (qv5.ch, chreis5.ch) now redirect to casino-spam at chreis5.info. Verein appears defunct; re-add if a clean domain reappears.
- **Quartierverein rqv.ch (Riesbach)** — server 500-erroring on 2026-04-25. Riesbach is already covered via `8008.ch`. Re-add if it returns.
- **apotheken-notfall.ch** — domain dead (NXDOMAIN). Pharmacy emergency lookups will become a live tool, not a KB lookup.
- **Stadt Zürich Wochenmärkte** — no clean canonical page; market info comes via `zuerich_com.py`.
- **Reddit / community forums, news feeds, business directories, classifieds, live schedules** — out of scope per §1 (handled later as live tools or dropped).

### Already covered by existing portals (do not re-ingest)

- SRZ / Stadtpolizei → `stadt_zuerich.py` (service pages) and `zh_ch_canton.py` (`sicherheit-justiz`).
- Kapo Zürich / gd.zh.ch → `zh_ch_canton.py`.
- Stadt Zürich Velo / Parken / Schulen → `stadt_zuerich.py`.

---

## 1. Goals

- Give Bünzli grounded, citable answers about Zürich (admin, housing, mobility, health, emergency, education, civic, leisure, food & drink, neighbourhoods) and Swiss law (federal, cantonal, municipal).
- Serve both DE-speaking residents and EN-speaking newcomers.
- Historical / archival content is a **character layer** — it shapes Bünzli's voice, not just Q&A.
- Keep ingestion reproducible, incremental, and decoupled from the embedding model.

Out of scope for the KB (handled elsewhere as live tools or dropped):
- News feeds (SRF Zürich, tsri.ch, Züritipp) → live news tool later.
- Business directories (local.ch) → live lookup tool.
- Classifieds / events (Ronorp) → out of scope.
- Reddit / community forums → out of scope.
- Live schedules (FCZ, GC, ZSC matches, concerts) → live tool; KB carries club/venue background only.

---

## 2. Architecture — two-phase pipeline

```
Phase 1 (runs today, app pod)            Phase 2 (runs later, AI pod)
──────────────────────────────           ───────────────────────────────
crawl → extract → clean → chunk          read .jsonl
     → write .jsonl                           → wrap in EmbeddingGemma prompt
                                              → embed (EmbeddingGemma-300M)
                                              → upsert into Qdrant
```

**Why two phases:**
- The AI pod does not exist yet. Splitting lets us build, inspect, and iterate on chunk quality now without the embedding model.
- Chunks as `.jsonl` files are grep-able, diff-able, replayable. A chunker bug does not require re-crawling.
- If we later change embedding model or vector DB, Phase 1 output is reusable.

**Phase 1 dependencies:** Python + HTTP client + BeautifulSoup/Playwright + the EmbeddingGemma tokenizer file (~2 MB, no model weights, CPU only, used solely to count tokens).

**Phase 2 dependencies:** Full EmbeddingGemma-300M model, BGE-reranker-v2-m3 at query time, Qdrant as a service in `deploy/docker-compose.yml`.

---

## 3. Collections

Two Qdrant collections:

| Collection | Contents | Chunking pattern |
|---|---|---|
| `zurich_kb` | All general semantic content — prose, procedures, references, historical | structural, 400–600 tokens |
| `zurich_law` | Statutes only — federal + cantonal + municipal | 1 article = 1 chunk |

News, classifieds, directories, and event listings are **not** in either collection.

---

## 4. Taxonomy (metadata `category`)

Ten top-level buckets for `zurich_kb`, plus `law` for the law collection.

| Category | Covers |
|---|---|
| `admin` | Anmeldung, Steuern, AHV, permits, Abfall/ERZ procedures, Strom/Wasser, Umzug |
| `housing` | Rent law explained, Mieterverband/HEV, Nebenkosten, Kündigung, Genossenschafts-Kultur |
| `mobility` | ZVV tariffs/zones, Velo-Regeln, Parkkarten, e-Scooter, car-sharing concepts |
| `health` | Krankenkasse basics, Hausarzt, hospitals, Spitex |
| `emergency` | 112/117/118/144, Notdienste, Giftnotruf, after-hours pharmacies |
| `education` | Volksschule, Kreisschulpflege, Kitas, Berufsschule, Unis |
| `civic` | Gemeinde/Kanton/Bund, Abstimmungen erklärt, initiatives, political system |
| `leisure` | Badis, hiking, museums, landmarks, festivals, Sihlwald, winter, history |
| `food_drink` | Beizen-Kultur, Märkte, Zürich food scene |
| `neighborhoods` | Kreis 1–12 characterisations, Quartier pages |

`subcategory` is optional, shallow, lowercased with a slash — e.g. `admin/steuern`, `housing/rent_law`, `leisure/history`.

`language` is a separate metadata field, **not** a taxonomy bucket. English content lives in the same buckets as German.

---

## 5. Chunking strategy

### 5.1 Splitting hierarchy (best → worst)

1. **Structural** — split on the document's own hierarchy: H1 → H2 → H3 → paragraph. Always preferred.
2. **Recursive character fallback** — try big separators (`\n\n`), fall back to smaller (`\n`, `.`, ` `). Used when structure is weak.
3. **Fixed token windows** — last resort. Avoid when possible.

### 5.2 Size targets

- **Target:** 400–600 tokens per chunk.
- **Hard max:** 1000 tokens. Embeddings degrade sharply past this.
- **Hard min:** 100 tokens. Merge upward rather than emit micro-chunks.
- **Overlap:** 10–15% (50–80 tokens).

Never split mid-sentence. Never split a list item, a table, or a code block.

### 5.3 Chunking by `doc_type`

| doc_type | Strategy | Rationale |
|---|---|---|
| `article` | Structural (5.1) + 400–600 tokens | Wikipedia, guides, gov explainers, HLS entries |
| `procedure` | Keep whole if ≤ 800 tokens; else split on step boundaries | Admin/Behördenkram — steps must stay intact |
| `reference` | One entity = one chunk, no splitting | Restaurants, hospitals, Badis, Notfallnummern |
| `statute` | One article = one chunk; split on Absatz boundaries if > 2000 tokens | Preserves legal citation granularity |
| `historical` | Structural + 300–400 tokens (smaller target) | Pulled often for character flavour; smaller blends better |

### 5.4 Special content handling

- **Tables:** never split mid-table. If a table exceeds 1000 tokens, serialise each row as `Column: value` prose.
- **Lists:** keep items together when short. Long lists may split on logical sub-groupings.
- **Code blocks / technical fragments:** keep intact, include surrounding prose as context.
- **Very long pages:** use the parent-child pattern (§ 6) — embed precise small chunks, retrieve the larger section when needed.

### 5.5 Heading-path prefix (mandatory)

Every chunk's `embed_text` is prefixed with the heading path as plain text:

```
ch.ch > Wohnen > Umzug > Anmeldung > Schritt 3

Bringen Sie zu Ihrem Termin folgende Unterlagen mit: ...
```

This is the single highest-leverage retrieval lift we get for free. It is **not** added to `display_text` (which stays clean).

---

## 6. Parent-child pattern

For long structured documents — especially long articles and multi-Absatz statutes — we store both:

- **Child chunk** — 400–600 tokens, precise, carries a `parent_chunk_id` pointing to its parent.
- **Parent chunk** — the larger enclosing section (~1500–2000 tokens), stored as a normal chunk with `doc_type` unchanged and a special `chunk_index` like `P01`, `P02`.

At retrieval time we embed and search over the children (precision), then — when the answer warrants — return the parent to the LLM for context. Implementation is deferred to Phase 2; Phase 1's job is to emit both.

A document triggers parent-child when any natural section would exceed ~1200 tokens after structural splitting.

---

## 7. Metadata schema (`schema_version: 1`)

Every chunk carries a single flat JSON object. Qdrant payload fields.

### 7.1 Required fields (every chunk)

| Field | Type | Example | Purpose |
|---|---|---|---|
| `chunk_id` | string | `d9f4ab0_0003` | Unique per chunk |
| `doc_id` | string | `d9f4ab0` | Parent document ID; stable hash |
| `chunk_index` | int or string | `3` or `P01` | Position in doc; `P` prefix = parent chunk |
| `parent_chunk_id` | string or null | `d9f4ab0_P01` | Parent-child pattern |
| `source_url` | string | `https://www.ch.ch/de/umzug/` | Citation |
| `source_name` | string | `ch.ch — Bundesportal` | Display |
| `title` | string | `Anmeldung bei Zuzug` | Parent doc title |
| `heading_path` | string | `ch.ch > Wohnen > Umzug > Anmeldung > Schritt 3` | Breadcrumb, prepended to `embed_text` |
| `language` | string | `de` / `en` / `fr` | Filter + reranker |
| `category` | string | `admin` | One of 10 (or `law`) |
| `subcategory` | string or null | `admin/umzug` | Shallow |
| `authority` | string | `federal` / `cantonal` / `city` / `wikipedia` / `community` / `private` | Trust-weighting in reranker |
| `doc_type` | string | `article` / `procedure` / `reference` / `statute` / `historical` | Drives chunking + filter |
| `chunk_shape` | string | `prose` / `table` / `list` / `code` | Shape of chunk content; optional debug |
| `token_count` | int | `487` | Sized with EmbeddingGemma tokenizer |
| `tags` | array of strings | `["umzug", "newcomer"]` | Free-form, filterable |
| `created_at` | ISO date | `2024-09-12` | When source was first seen |
| `updated_at` | ISO date | `2025-11-14` | When source last changed; drives incremental re-ingest |
| `ttl_days` | int or null | `180` | Re-crawl cadence; null = stable (historical) |
| `schema_version` | int | `1` | Bumpable when schema evolves |
| `display_text` | string | `"Bringen Sie ..."` | Clean text for user display + citations |
| `embed_text` | string | `"ch.ch > ... \n\nBringen Sie ..."` | What Phase 2 embeds (wrapped in prompt format) |

### 7.2 Optional fields, per `doc_type`

| doc_type | Extra fields |
|---|---|
| `procedure` | `step_index` (int, if step-split) |
| `reference` | `entity_name` (str), `entity_type` (str), `address` (str) |
| `statute` | `law_name` (str), `abbrev` (str), `sr_number` (str, federal) or `ls_number` (str, cantonal), `article_number` (str), `paragraph` (str, if Absatz-split) |
| `historical` | `period` (str, nullable, e.g. `19. Jahrhundert`) |

### 7.3 Cross-cutting optional fields

| Field | Type | Example |
|---|---|---|
| `district` | string or null | `Kreis 6` / `Wipkingen` |
| `license` | string | `CC0` / `CC-BY-SA` / `proprietary-cited` / `fair-use-summary` |

### 7.4 Qdrant payload indexes

Create at collection-init time for filter performance:

- `category`, `subcategory`, `doc_type`, `language`, `authority`, `district`
- `tags` (array)
- `doc_id`, `updated_at`

---

## 8. EmbeddingGemma prompt format (Phase 2)

EmbeddingGemma requires task-specific prompts. Applied **at Phase 2 only**; Phase 1 jsonl stores unwrapped `embed_text`.

- **Document side (ingestion):** `title: none | text: <embed_text>`
- **Query side (retrieval):** `task: search result | query: <user_question>`

Skipping these silently degrades retrieval quality. Both the ingest worker and the orchestrator must apply them.

---

## 9. Identifiers and hashing

- `doc_id = sha1(source_url + "|" + language + "|" + schema_version)[:12]`
- `chunk_id = doc_id + "_" + zero_padded(chunk_index, 4)` (e.g. `d9f4ab0_0003`)
- Parent chunk: `chunk_index = "P01"`, `chunk_id = doc_id + "_P01"`

Stable IDs enable `upsert` — re-crawling a page updates chunks in place, no duplicates.

---

## 10. Incremental updates

1. Crawler fetches source, computes `updated_at` from `<meta>` / `Last-Modified` / visible date / crawl-time fallback.
2. If `updated_at` matches the stored value for that `doc_id`, skip.
3. If changed (or doc is new): re-chunk, **delete all chunks in Qdrant with `doc_id = X`**, then upsert the new chunks.
4. Document deleted at source: delete all chunks with its `doc_id`.

Simpler than diffing individual chunks; fast enough at our scale.

---

## 11. Source catalogue (target state)

**Legend:** `ttl` in days; `null` = stable, no re-crawl scheduled.

### 11.1 `admin`
| Source | URL | Lang | doc_type | ttl |
|---|---|---|---|---|
| ch.ch — Bundesportal | `ch.ch` | de/en/fr | procedure | 180 |
| zh.ch service pages | `zh.ch/de/steuern-finanzen`, `/wirtschaft-arbeit`, `/migration` | de | procedure | 180 |
| stadt-zuerich.ch services | Bevölkerungsamt, Steuern | de | procedure | 180 |
| estv.admin.ch | `estv.admin.ch` | de/en | procedure | 365 |
| sem.admin.ch | `sem.admin.ch` | de/en | procedure | 365 |
| bsv.admin.ch | `bsv.admin.ch` | de/en | article | 365 |

### 11.2 `housing`
| Source | URL | Lang | doc_type | ttl |
|---|---|---|---|---|
| HEV Schweiz | `hev-schweiz.ch` | de | article | 365 |
| Mieterverband | `mieterverband.ch` | de | article | 365 |
| stadt-zuerich.ch Stadtentwicklung | `/stadtentwicklung` | de | article | 365 |
| WBG Zürich | `wbg-zh.ch` | de | article | 365 |

Cap Mieterverband crawl depth — must not exceed ~15% of total `housing` chunks.

### 11.3 `mobility`
| Source | URL | Lang | doc_type | ttl |
|---|---|---|---|---|
| ZVV tariffs & rules | `zvv.ch` | de/en | reference + article | 180 |
| SBB general info | `sbb.ch/de/abos-billette` | de/en | article | 365 |
| Stadt Zürich Velo | `stadt-zuerich.ch/velo` | de | article | 365 |
| Tiefbauamt Parken | `stadt-zuerich.ch/parkieren` | de | article | 365 |
| bfu.ch | `bfu.ch` | de/en | article | 365 |
| Publibike / Mobility | `publibike.ch`, `mobility.ch` | de/en | article | 365 |

### 11.4 `health`
| Source | URL | Lang | doc_type | ttl |
|---|---|---|---|---|
| bag.admin.ch | `bag.admin.ch` | de/en | article | 365 |
| gesundheit.zh.ch | `gd.zh.ch` | de | article | 365 |
| USZ, Stadtspitäler | `usz.ch`, `stadtspital.ch` | de/en | reference | 365 |
| priminfo.admin.ch | `priminfo.admin.ch` | de/en/fr | article | 365 |
| Spitex Zürich | `spitex-zuerich.ch` | de | reference | 365 |

### 11.5 `emergency`
| Source | URL | Lang | doc_type | ttl |
|---|---|---|---|---|
| Schutz & Rettung Zürich | `schutz-rettung-zuerich.ch` | de | reference | 365 |
| Stadtpolizei Zürich | `stadt-zuerich.ch/stadtpolizei` | de | reference | 365 |
| Kapo Zürich | `kapo.zh.ch` | de | reference | 365 |
| Tox Info Suisse | `toxinfo.ch` | multi | reference | null |
| Apotheken-Notfalldienst | `apotheken-notfall.ch` / `pharmasuisse.org` | de | reference | 90 |

### 11.6 `education`
| Source | URL | Lang | doc_type | ttl |
|---|---|---|---|---|
| VSA Kanton ZH | `vsa.zh.ch` | de | article | 365 |
| MBA Kanton ZH | `mba.zh.ch` | de | article | 365 |
| Stadt Zürich Schulen | `stadt-zuerich.ch/schulen` | de | article | 365 |
| UZH/ETH/ZHAW/PHZH | `uzh.ch`, `ethz.ch`, `zhaw.ch`, `phzh.ch` | multi | article | 365 |
| Kitaplätze Stadt Zürich | `stadt-zuerich.ch/kinderbetreuung` | de | procedure | 365 |

### 11.7 `civic`
| Source | URL | Lang | doc_type | ttl |
|---|---|---|---|---|
| ch.ch politisches System | `ch.ch/de/politisches-system` | multi | article | 365 |
| easyvote | `easyvote.ch` | de/fr/it | article | 180 |
| swissvotes.ch | `swissvotes.ch` | de/fr/en | reference | 180 |
| parlament.ch | `parlament.ch` | multi | article | 365 |
| stat.zh.ch | `stat.zh.ch` | de | article | 365 |
| Stadt Zürich Statistik | `stadt-zuerich.ch/statistik` | de | article | 365 |
| admin.ch | `admin.ch/de` | de | article | 365 |

### 11.8 `leisure` (incl. history — character layer)
| Source | URL | Lang | doc_type | ttl |
|---|---|---|---|---|
| In Your Pocket Zürich | `inyourpocket.com/zurich` | en | article | 365 |
| FCZ / GC / ZSC Lions | `fcz.ch`, `gc-zuerich.ch`, `zsclions.ch` | de | article | 365 |
| zuerich.com (subset) | `/de/besuchen/*` | de/en | article | 365 |
| Wikipedia DE+EN | curated list | de/en | article | 365 |
| Historisches Lexikon der Schweiz ⭐ | `hls-dhs-dss.ch` | multi | historical | null |
| Stadtarchiv Zürich | `stadt-zuerich.ch/stadtarchiv` | de | historical | null |
| ZB e-rara / e-manuscripta | `e-rara.ch`, `e-manuscripta.ch` | de | historical | null |
| EHRI Project | `ehri-project.eu` | en | historical | null |
| Landesmuseum / Kunsthaus / Rietberg | `landesmuseum.ch`, `kunsthaus.ch`, `rietberg.ch` | de/en | reference | 365 |
| Badi-Info | `badi-info.ch` | de | reference | 365 |

ZB e-rara / e-manuscripta: curate ~20–30 specific historical texts, not bulk ingest.

### 11.9 `food_drink`
| Source | URL | Lang | doc_type | ttl |
|---|---|---|---|---|
| Gault Millau Zürich | `gaultmillau.ch/zueri-isst` | de | reference | 365 |
| Harry's Ding | `harrysding.ch` | de | article | 365 |
| zuerich.com Essen & Trinken | `/de/besuchen/essen-trinken` | de/en | article | 365 |
| Stadt Zürich Märkte | `stadt-zuerich.ch/maerkte` | de | reference | 365 |

Harry's Ding scrape requires discussion before execution (JS-heavy; failed previously).

### 11.10 `neighborhoods`
| Source | URL | Lang | doc_type | ttl |
|---|---|---|---|---|
| Quartierspiegel Stadt Zürich ⭐ | `stadt-zuerich.ch/quartierspiegel` | de | article | 365 |
| Wikipedia Kreis/Quartier | DE + EN | multi | article | 365 |
| Gemeinschaftszentren Zürich | `gz-zh.ch` | de | article | 365 |
| Quartiervereine (all 34, quality-checked) | per-Quartier | de | article | 365 |

Quartiervereine: ingest all 34, but relevance-check per site — skip dormant/dead ones.

### 11.11 `law` (separate collection)
| Source | URL | Lang | doc_type | ttl |
|---|---|---|---|---|
| Federal codes (8 PDFs) | Fedlex | de | statute | null |
| ZH-Lex (cantonal) ⭐ | `zhlex.zh.ch` | de | statute | 365 |
| Stadt Zürich AS | `stadt-zuerich.ch/AS` | de | statute | 365 |

---

## 12. Stadt-zuerich.ch JS-hydration caveat

Several high-value sources live on `stadt-zuerich.ch`, which uses `stzh-*` Web Components with `visibility: hidden` until JS hydrates. Plain HTTP yields < 20 characters per page. Affected in this spec:

- Quartierspiegel (`neighborhoods`, critical)
- Stadt Zürich Stadtentwicklung (`housing`)
- Selected Bevölkerungsamt / Steuern pages (`admin`)
- Stadtpolizei (`emergency`)
- stadt-zuerich.ch/schulen (`education`)
- Stadtarchiv (`leisure/history`)
- Stadt Zürich Statistik (`civic`)
- Stadt Zürich AS (`law`)

**Approach:** use Playwright (headless Chromium) for these domains in the ingest. Fallback: manual paste into `data/manual_content/` if Playwright fails. To validate in the first ingester that hits a `stadt-zuerich.ch` page.

---

## 13. Repository layout

```
backend/kb/                           # new module
├── __init__.py
├── chunker.py                        # structural splitter; size/overlap enforcement
├── metadata.py                       # schema dataclass, validation, doc_id/chunk_id helpers
├── tokenizer.py                      # EmbeddingGemma tokenizer loader (counting only)
├── writers.py                        # .jsonl writer
└── fetchers.py                       # HTTP + Playwright fetchers, shared rate limiting

scripts/ingest/                       # one file per source
├── __init__.py
├── _base.py                          # shared crawl / extract utilities
├── ch_ch.py
├── zhlex.py
├── hls.py
├── wikipedia.py
├── quartierspiegel.py
├── law_pdfs.py
├── fcz.py
└── …

scripts/embed.py                      # Phase 2 — runs on AI pod

data/chunks/{category}/{source}/*.jsonl   # Phase 1 output
data/law_pdfs/*.pdf                       # source PDFs (already present)
```

Old `scripts/ingest.py`, `scripts/ingest_wikipedia.py`, `scripts/ingest_opendata.py`, `scripts/ingest_law_pdfs.py` have been retired (removed 2026-04-24) — their logic is redistributed into `scripts/ingest/*.py`. `scripts/cleanup_kb.py` stays until Phase 2 retires the old Chroma stores.

---

## 14. Quality checklist (acceptance before Phase 2)

Before any collection goes into production, sample 20 random chunks per source and verify:

- [ ] Each chunk reads as self-contained
- [ ] Tables and lists are intact where they should be
- [ ] `heading_path` is accurate and non-empty on every chunk
- [ ] Every chunk traces back to a valid `source_url`
- [ ] `updated_at` actually updates when the source changes and we re-ingest
- [ ] `token_count` agrees with an independent Gemma-tokenizer pass (sanity check)
- [ ] Sample 10 questions per category — do the top-30 retrieved chunks look plausible?
- [ ] No mid-sentence splits
- [ ] `display_text` has no heading-path pollution (clean for display)
- [ ] `embed_text` includes the heading path

---

## 15. Build order

1. Scaffold `backend/kb/` (chunker, metadata, tokenizer, writers, fetchers).
2. First ingester: **ch.ch** — cleanest HTML, multilingual, fills `admin` + EN coverage simultaneously. Acts as a reference implementation.
3. Second: **federal law PDFs** — exercises the `statute` path.
4. Third: **Quartierspiegel** — exercises the Playwright path.
5. Everything else in parallel, grouped by category.
6. Acceptance (§ 14) per source.
7. When all sources pass: build `scripts/embed.py`, spin up Qdrant in Compose, run Phase 2.
8. Wire retrieval + BGE reranker into the agent.
9. Decommission the old Chroma stores and their handler code.

---

## 16. Things explicitly deferred

- **Contextual retrieval** (1-sentence LLM summary prepended per chunk) — revisit after Phase 2 baseline eval.
- **Automatic re-crawl scheduling** — manual for now; cron later.
- **Embedding-time quality filters** (near-duplicate detection across sources) — after first end-to-end run.
- **Multilingual cross-language retrieval tuning** — EmbeddingGemma is multilingual out of the box; re-eval after baseline.
- **The old knowledge connector handlers** — stay as-is serving the old Chroma stores until Phase 2 replaces them.
