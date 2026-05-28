# 星尘：诸族之战

A NovelForge novel project — the manuscript is decoupled from the *world state*. Prose
lives in `chapters/`; the truth (who knows/holds what, who feels what about whom, when,
and why) lives in a temporal knowledge base. This is what keeps a million-word novel
consistent and lets it exceed an LLM's context window.

Story-time unit: **chapter** · prose language: **zh-Hans** · genre: **科幻战争**.

> Prose (and `canonical_name` / `aliases`) are written in the project language. Graph
> **IDs** (`char_ye_fan`) and **relation predicates** (`hates`, `member_of`) stay ASCII
> snake_case regardless, so tooling and merges work across languages. For non-English
> projects, consult the **narrative-locale** skill for naming, genre, and structure
> conventions, and run **cognitive-alignment** to lock invented terms with the author.

## Layout

| Path | What |
|---|---|
| `ontology.json` | canonical temporal graph: entities, time-variant relations, events, threads, world rules |
| `world/` | worldview / World Bible (power system, geography, factions, logic rules) |
| `characters/` | character profiles + T=0 states; `states/` = per-chapter state timelines |
| `timeline/` | narrative threads (swimlanes), event graph, world calendar |
| `outline/` | Novel→Volume→Chapter write-ahead tree; `beats/` = per-chapter beat sheets |
| `masks/` | per-character knowledge masks (fog of war) |
| `chapters/` | prose drafts; `profiles/` = chapter-masked KB profiles (the memory primitive) |
| `memory/` | hierarchical summaries (L1–L4) + plot-thread / open-loop tracker |
| `reference/` | reference docs & resources + `index.json` manifest |

## Tools (from the narrative-toolkit skill)

```bash
# Inspect the KB
python view_kb.py .                       # overview
python view_kb.py . --timeline            # events as thread swimlanes
python view_kb.py . --character char_x    # one character across time
python view_kb.py . --snapshot 45         # world state as of chapter 45

# Build the chapter-masked memory profile (feed THIS to the writer, not the whole novel)
python build_profile.py . --chapter ch_045

# Search: knowledge base first, then KAG over the prose
python search_novel.py . "why does the villain attack?" --as-of 50

# Validate structure + continuity
python validate_narrative.py .
python check_consistency.py .
```

## How memory beats the token limit

For any chapter you write, `build_profile.py` materializes a few-KB snapshot of exactly
the world state as of that chapter, masked to the POV character's knowledge. You feed
that compact profile to the model instead of the manuscript. When you need actual prose,
`search_novel.py` does KB-first retrieval then pulls only the relevant passages (KAG).
The full text is never required in context at once.
