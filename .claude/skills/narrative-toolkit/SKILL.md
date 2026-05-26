---
name: narrative-toolkit
description: The runnable command-line tools for a NovelForge novel project — inspect the knowledge base, build chapter-masked memory profiles, and search inside the novel. Use this skill whenever you need to actually run (not just describe) novel KB operations. It views the KB by timeline / character / event graph / chapter snapshot; it materializes a chapter-masked KB profile (the compact as-of-chapter, POV-masked memory snapshot that lets a million-word novel fit an LLM context window); and it runs two-stage semantic search (knowledge-base first, then KAG retrieval over the sub-chapter prose scoped by the chapter-masked profile). Ships view_kb.py, build_profile.py, search_novel.py and the shared narrative_kb.py engine. Operates over the project layout defined by narrative-ontology — read that skill first.
---

# Narrative Toolkit

The operational tools for a novel project. The phase skills (genesis / architect /
execution / memory) describe the *workflow and prompts*; this skill ships the
*runnable scripts* that read and derive the knowledge base. **Read
`narrative-ontology/SKILL.md` first** — every tool assumes that project layout.

All tools are pure standard library (no pip installs) and share one engine,
`scripts/narrative_kb.py`, which loads the KB and answers "as of story-time N" queries.

## The tools

| Tool | Purpose |
|---|---|
| `scripts/view_kb.py` | inspect the KB by timeline / character / events / snapshot |
| `scripts/build_profile.py` | materialize a chapter-masked KB profile (the memory primitive) |
| `scripts/search_novel.py` | two-stage search: knowledge base first, then KAG over prose |
| `scripts/narrative_kb.py` | shared loader + as-of folding engine (imported by the above) |

(Lifecycle tools live with their owning skills: `init_kb.py` + `validate_narrative.py`
in **narrative-ontology**; `check_consistency.py` in **narrative-consistency**.)

### view_kb.py — inspect the KB

```bash
python view_kb.py <novel>/                      # overview: counts, threads, volumes, open loops
python view_kb.py <novel>/ --timeline           # events as thread swimlanes (multi-POV)
python view_kb.py <novel>/ --character char_x    # one character: profile + state timeline + relations over time
python view_kb.py <novel>/ --events              # the causal event graph with dependencies
python view_kb.py <novel>/ --snapshot 45         # full world state AS OF story-time 45
python view_kb.py <novel>/ --chapter ch_045      # snapshot resolved from a chapter's story-time
python view_kb.py <novel>/ --timeline --json     # machine-readable
```

The snapshot/character views fold the temporal graph correctly: relations only appear
while valid (`valid_from_chapter <= N < valid_to_chapter`), inventory reflects deltas up
to N, and the knowledge mask shows what the character knew at that point.

### build_profile.py — chapter-masked KB profile (THE memory primitive)

This is how the novel exceeds an LLM's context window. Instead of feeding the whole
manuscript, you feed a compact (few-KB) snapshot of exactly the world state as of the
chapter, masked to the POV character's knowledge (fog of war):

```bash
python build_profile.py <novel>/ --chapter ch_045          # writes chapters/profiles/ch_045.json
python build_profile.py <novel>/ --story-time 45 --pov char_ye_fan --stdout
python build_profile.py <novel>/ --chapter ch_045 --recent 3   # fewer recent loglines
```

A profile contains: hierarchical summary context (novel + volume + recent chapter
loglines), active entities with their state as of N, the relations in effect, events so
far, the POV's knowledge mask + the `visible_facts` they may write from, open plot
threads to keep live, the world rules, and a `token_estimate`. Feed this to the writer
(narrative-execution) instead of the raw novel.

### search_novel.py — KB-first, then KAG

Two stages, mirroring the NovelForge memory design:

```bash
python search_novel.py <novel>/ "why does the villain attack the city?"
python search_novel.py <novel>/ "Ye Fan and the broken sword" --as-of 45 --topk 5
python search_novel.py <novel>/ "betrayal" --kb-only      # structured KB only
python search_novel.py <novel>/ "betrayal" --json
```

- **Stage 1 (KB-first):** match the query against entities, events, relations, and
  world-rules. Precise and cheap; identifies *which* entities/threads the question is
  about.
- **Stage 2 (KAG):** graph-expand from the Stage-1 entity hits (related entities +
  co-event participants), scope the prose to a chapter-masked view (`--as-of N`, and/or
  only chapters where the matched entities are active), then rank passages by TF-IDF
  cosine. The KB hits are the "knowledge" that augments and focuses text retrieval, so
  you never blindly scan a 2M-word manuscript and answers stay grounded.

`--as-of N` makes search respect the fog of war over time: querying as of chapter 45
will not surface a betrayal that happens in chapter 50.

## How the tools enable million-token novels

```
                    full novel (2M+ words, won't fit context)
                                    │
        ┌───────────────────────────┴───────────────────────────┐
        ▼                                                         ▼
  build_profile.py  ──>  chapter-masked profile (~1K tokens)   search_novel.py
  "the memory you carry into the prompt"                       "retrieve only the
   = summaries + as-of state + POV mask + open loops            relevant passages on demand
                                                                 (KB-first, then KAG)"
```

You write each chapter with its **profile** in context (cheap, always fits). When you
need a specific past detail, **search** pulls just that passage. The manuscript is never
required in context all at once — that is the whole point of decoupling text from state.

## Upgrading the search backend

`search_novel.py` uses pure-stdlib TF-IDF cosine — a solid offline default that needs no
dependencies. To use dense embeddings instead, replace `tfidf_vec` / `cosine` in
`narrative_kb.py` with an embedding backend (e.g. sentence-transformers, or an API). The
two-stage KB-first → KAG structure is unchanged; only the scoring function swaps. Cache
vectors under the project's `.index/` (already gitignored by `init_kb.py`).

## When to use this skill vs. the phase skills

- Use **narrative-toolkit** when you need to *run* something: look at the KB, build a
  profile before drafting, or search for a fact.
- Use **narrative-memory** for the *reasoning* layer: how to route a question, how to
  synthesise a cited answer, how to maintain the plot-thread tracker. narrative-memory's
  retrieval steps are *implemented* by `search_novel.py` + `build_profile.py` here.
- Use **narrative-ontology** for the schema, `init_kb.py`, and `validate_narrative.py`.

## Reference files

- `references/tool_recipes.md` — common command recipes for each phase of writing
  (drafting a chapter, auditing continuity, answering a reader question, onboarding a
  co-author), and the JSON shapes the tools emit.
