---
name: narrative-memory
description: Phase IV (Memory) of the NovelForge novel-writing workflow — the global long-text memory and query system that solves the "forgetting" problem in million-word serials. Use this skill to build the hierarchical summary index (novel→volume→chapter→scene loglines), route a reader/author question to the right retrieval strategy (graph query for exact facts, vector/semantic for vibes, summary scan for plot outlines), synthesise an evidence-cited answer across chapters, and track plot threads / unresolved foreshadowing (open-loop detection). Reads the whole narrative-ontology KB and writes memory/. Bridges to the ontology-qa skill for retrieval. Run after chapters are drafted by narrative-execution; read narrative-ontology first.
---

# Narrative Memory (Phase IV)

> *Goal: solve the "forgetting" of million-word serials. Once a novel passes a million
> words the context window alone is hopeless — combine vector search, graph query, and
> hierarchical summaries into one hybrid RAG system.*

This phase keeps the novel queryable and catches dropped threads. It reads the whole KB
and maintains `memory/summaries.json` + `memory/plot_threads.json`. **Read
`narrative-ontology/SKILL.md` first.** Run after narrative-execution finalises a
chapter (to index it) and on demand (to answer questions / audit threads).

The reasoning in this skill (route → retrieve → synthesise → track) is *implemented* by
the runnable tools in **narrative-toolkit**: `build_profile.py` materializes the
chapter-masked memory snapshot, and `search_novel.py` runs the KB-first → KAG retrieval.
This skill says *how to think*; the toolkit *does it*.

## The memory primitive that beats the token limit

The single most important artifact for exceeding a model's context window is the
**chapter-masked KB profile** (`chapters/profiles/<id>.json`, built by
`narrative-toolkit/scripts/build_profile.py`). It is a few-KB snapshot of exactly the
world state as of a chapter, masked to the POV's knowledge: hierarchical summaries up to
N, active entities with their as-of-N state, the relations in effect, the POV's
knowledge mask, open plot threads, and the world rules. You carry *this* into the
writing prompt instead of the manuscript. A 2M-word novel never needs to fit context at
once — you hold the compact profile, and pull specific prose on demand via search.

**Language:** write summaries/loglines in the project language. Search is CJK-aware (the
tokenizer splits space-less Chinese into unigrams+bigrams), and "million words" means
**百万字** (characters ≈ 1 token each) — which is precisely the scale where the
chapter-masked profile + search are mandatory. See **narrative-locale**.

## What this phase maintains

```
              ┌──────────── memory/summaries.json (the index) ────────────┐
   L1 novel summary  →  L2 volume summaries  →  L3 chapter loglines+synopsis  →  L4 scene chunks
              └───────────────────────────────────────────────────────────┘
                                       │
   question ──> QueryRouter (MEM-02) ──┼──> graph_query (exact facts, inventory, timeline)
                                       ├──> vector_search (vibes, similar scenes, emotional arcs)
                                       └──> summary_scan (high-level plot)
                                       │
                              Synthesizer (MEM-03) → evidence-cited answer
                                       │
                         plot_threads.json ← Open-Loop Detector (MEM-04)
```

Prompts: `references/memory_prompts.md` (MEM-01 indexer, MEM-02 router, MEM-03
synthesizer, MEM-04 open-loop detector).

## Step 1 — Index a finalised chapter (MEM-01)

When narrative-execution finishes a chapter, compress it into a structured summary
record and append to `memory/summaries.json.chapter_summaries` (schema §6.1):

- **Logline** — < 30 words, for quick scanning.
- **Synopsis** — ~200 words, retaining **causality** (why things happened) and **state
  changes** (who got what).
- **Active entities** — every character/item active in the chapter (entity IDs).
- **Tags** — themes (combat, betrayal, level_up, romance, discovery).

Then roll up: regenerate the affected volume summary (L2) when a volume's chapters
change, and the novel summary (L1) at major milestones. This is the hierarchical
summary tree the writer's context composer pulls from for global awareness.

## Step 2 — Route a question (MEM-02)

Reader/author questions vary. Classify each to the right tool(s):

- **`graph_query`** — exact facts, inventory checks, relationships, timeline order.
  ("Who holds the Heaven Sword now?" → traverse `ontology.json` edges as-of the
  current chapter.)
- **`vector_search`** — vague concepts, emotional arcs, "find a similar scene".
  ("When did the hero feel despair?" → semantic search over chapter synopses / scene
  chunks.)
- **`summary_scan`** — high-level plot outline. ("What happens in Volume 2?")
- **`hybrid`** — many questions need both. ("Did I establish the villain fears fire?"
  → graph_query for `weaknesses` AND vector_search for fear-of-fire scenes.)

Output the chosen tool(s) + the concrete query. Execute the retrieval with
**`narrative-toolkit/scripts/search_novel.py`** — it runs Stage 1 (KB-first over
entities/events/relations/world-rules) then Stage 2 (KAG over the prose, graph-scoped by
the chapter-masked profile, with `--as-of N` for temporal masking). For generic ontology
grounding beyond the novel-specific layer, the `ontology-qa` skill also applies.

## Step 3 — Synthesise with citations (MEM-03)

Given the retrieved fragments (graph data + summaries + prose snippets), compose a
human answer. **Rules:** cite the source of every claim (`[Ref: Ch.10]`,
`[Graph: rel_0042]`); flag contradictions in the retrieved material (Ch.10 says he
loves blue, Ch.50 says he hates it); say "No record found" rather than hallucinate.

Example — "How did the hero and heroine's relationship develop?" → trace the arc from
the graph edges (trust 0 → 80) cross-referenced with chapter summaries: meet ([Ch.05])
→ misunderstanding ([Ch.20]) → reconciliation ([Ch.50]).

## Step 4 — Track plot threads / open loops (MEM-04)

The feature authors want most: "did I plant something and never pay it off?" Maintain
`memory/plot_threads.json` (schema §6.2). For each hook, track `status`:

`open` (just planted) → `dormant` (unmentioned a while) → `at_risk` (gone so long
readers may forget) → `resolved` (paid off).

When a hook crosses the at-risk threshold (e.g. 50+ chapters since last mention),
surface it with a suggestion ("trigger a ring-related event soon, or readers forget").
Feed at-risk hooks to **narrative-architect** so payoffs get scheduled into the outline.

## Relationship to ontology-qa and book-to-knowledge-graph

- **ontology-qa** is the generic retrieval+grounding skill over an ontology.
  narrative-memory is the novel-specific layer on top: it adds the summary hierarchy,
  the temporal as-of-chapter graph queries, and the plot-thread tracker, and delegates
  raw retrieval to ontology-qa.
- For a *finished* novel a user wants to analyse from scratch (not write), the
  **book-to-knowledge-graph** pipeline (chunk → extract → merge → store → qa) is the
  right tool — it builds a static ontology. narrative-memory instead maintains the
  *living* index of a novel being written, where the graph already exists and grows
  chapter by chapter.

## Output checklist

- [ ] `memory/summaries.json` updated: L3 record for the new chapter; L2/L1 rolled up
      when needed.
- [ ] Questions answered with citations and contradiction flags.
- [ ] `memory/plot_threads.json` updated; at-risk hooks surfaced to the user / architect.
- [ ] `validate_narrative.py` passes.

## Reference files

- `references/memory_prompts.md` — MEM-01 (hierarchical summarizer), MEM-02 (hybrid
  search router), MEM-03 (evidence-based synthesizer), MEM-04 (open-loop detector),
  with system roles + JSON/output contracts.

Runnable implementations of the retrieval steps live in **narrative-toolkit**:
`build_profile.py` (the memory snapshot) and `search_novel.py` (KB-first → KAG).
