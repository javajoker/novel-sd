---
name: narrative-ontology
description: The data-model foundation for AI-assisted long-form fiction (NovelForge). Defines a temporal, stateful, knowledge-masked knowledge base for a novel — the file layout plus the schema for entities with per-chapter state timelines (inventory/knowledge/psychology), time-variant relationship edges (valid_from_chapter/valid_to_chapter), a multi-thread event graph driven by story-time, narrative threads with POV, per-character knowledge masks (fog of war), the write-ahead outline/beat tree, world-rule ontology triples, and the hierarchical summary index. Use this skill FIRST whenever building or editing a novel knowledge base, or when any narrative-genesis / narrative-architect / narrative-execution / narrative-memory / narrative-consistency skill needs the canonical schema and validator. Extends the ontology-extraction v1.0 schema for the forward (outline→prose) and backward (prose→state) narrative loop.
---

# Narrative Ontology

The shared data model for a stateful novel. Every other `narrative-*` skill reads
and writes this knowledge base; this skill owns the schema, the on-disk layout, and
the validator. Read it before touching a novel KB.

## Why this is not just the book→KG ontology

The `ontology-extraction` / `book-to-knowledge-graph` pipeline turns **existing text
into a static graph** (one direction, no time). A novel-in-progress needs the
opposite and more:

1. **Bidirectional.** Plan forward (outline → prose) *and* extract backward
   (prose → state deltas).
2. **Temporal.** "Friends in Ch.1, enemies in Ch.50." Every edge and every
   character state is stamped with story-time, so you can query the graph *as of*
   any chapter.
3. **Masked.** Each character knows only some facts at any time. The graph stores
   the global truth; **knowledge masks** project the limited view a POV character
   may write from (fog of war).
4. **Multi-threaded.** Parallel storylines (protagonist line, villain line) run on
   their own threads and converge at synchronised events.

This schema is a strict superset of the base v1.0 ontology, so the
`ontology-merging` / `ontology-storage` / `ontology-qa` scripts still operate on the
`entities / relations / events / themes` core.

## Knowledge-base layout (the novel project structure)

`scripts/init_kb.py` initializes a full, self-contained novel **project** — prose and
world-state KB side by side, version-controllable. Every `narrative-*` skill and tool
assumes exactly this layout:

```
<novel-slug>/
├── README.md                     # project guide + tool cheat-sheet (generated)
├── .gitignore                    # ignores the .index/ search cache
├── ontology.json                 # CANONICAL graph — entities, relations, events, themes, threads, world_rules
├── world/
│   ├── world_bible.json          # worldview: power system, geography, factions, ontology_triples (rules)
│   └── elements/<element_id>.json # one file per location / faction / item / concept (optional split)
├── characters/
│   ├── <char_id>.json            # base profile + initial_state (T=0)
│   └── states/<char_id>.json     # ordered CharacterState snapshots over story-time
├── timeline/
│   ├── threads.json              # NarrativeThread[] — the swimlanes (multi-POV)
│   ├── events.json               # event graph: nodes + causal/chronological edges
│   └── calendar.json             # world calendar ↔ story_time mapping, travel-time rules
├── outline/
│   ├── structure.json            # Novel → Volume → Chapter outline tree (write-ahead plan)
│   └── beats/<chapter_id>.json   # BeatSheet: ordered beats + emotional arc for one chapter
├── masks/
│   └── <char_id>.json            # KnowledgeMask: facts this character knows, per story_time
├── chapters/
│   ├── <chapter_id>.md           # the prose draft
│   └── profiles/<chapter_id>.json # CHAPTER-MASKED KB PROFILE — the as-of-chapter, POV-masked memory snapshot
├── memory/
│   ├── summaries.json            # hierarchical summary index (novel/volume/chapter/scene)
│   └── plot_threads.json         # open-loop / foreshadow tracker
└── reference/
    ├── index.json                # manifest of reference docs/resources
    └── <dropped files>           # research, source texts, style samples, maps, art, notes
```

`ontology.json` is the index that ties it together. The auxiliary files
(`characters/states`, `masks`, `outline/beats`, `chapters/profiles`, `memory`) hold the
bulky, fast-changing, or per-entity data that would bloat the canonical graph. The
schema for all of them is in `references/narrative_schema.md`; the full project rationale
(and the `reference/` manifest shape) is in `references/project_structure.md`.

Two paths added beyond the bare graph:

- **`chapters/profiles/<id>.json`** — the *chapter-masked KB profile*: the KB folded to a
  chapter and masked to the POV's knowledge. This compact snapshot is the **memory
  primitive that lets the novel exceed an LLM's context window** — you feed it to the
  writer instead of the whole manuscript. Built by `narrative-toolkit/scripts/build_profile.py`.
- **`reference/`** — external reference docs/resources, with `index.json` as the
  manifest. Kept separate from invented lore so research never leaks into canon.

The runnable tools that operate over this layout (view / profile / search) live in the
**narrative-toolkit** skill.

## The canonical graph — `ontology.json`

Extends base v1.0. Top level:

```json
{
  "ontology_version": "1.0-narrative",
  "source": { "novel_title": "...", "novel_author": "...", "current_chapter": 50 },
  "entities":    [ /* Entity (+ narrative fields) */ ],
  "relations":   [ /* Relation (+ temporal validity + quantified props) */ ],
  "events":      [ /* Event (+ story_time, thread_id, dependencies, projected_outcome) */ ],
  "themes":      [ /* Theme — unchanged from base */ ],
  "threads":     [ /* NarrativeThread */ ],
  "world_rules": [ /* OntologyTriple — (source) -[relation]-> (target) logic locks */ ]
}
```

The four narrative additions versus base v1.0:

- **Relations carry time.** `valid_from_chapter`, `valid_to_chapter` (null = still
  valid), plus quantified `properties` (`trust`, `romance`, `hate`, `intensity`,
  `reason`). When a relationship flips, you **terminate** the old edge
  (`valid_to_chapter = N`) and **create** a new one — never mutate in place. This is
  what makes "as-of chapter N" queries correct.
- **Events are scheduled and causal.** `story_time`, `duration`, `thread_id`,
  `participants` (entity IDs), `location`, `dependencies` (`PRECEDES` / `CAUSES` /
  `ENABLES` edges to other events), and `projected_outcome` (the relationship shift
  this event is *planned* to cause — pre-baked by narrative-architect, confirmed by
  narrative-execution).
- **`threads`** are the multi-POV swimlanes.
- **`world_rules`** are the ontology triples — the logic locks
  (`(Fire)-[WEAK_AGAINST]->(Water)`) that narrative-consistency enforces.

## The five auxiliary structures

Full field lists live in `references/narrative_schema.md`. In brief:

| File | Holds | Written by | Read by |
|---|---|---|---|
| `characters/<id>.json` | base profile + T=0 `initial_state` | narrative-genesis | all |
| `characters/states/<id>.json` | `CharacterState[]` over story-time (inventory, knowledge, psychology, location, status) | narrative-execution (extract) | narrative-execution (mask), narrative-consistency |
| `masks/<id>.json` | `KnowledgeMask` — `facts_known` / `beliefs_held` per `story_time` | narrative-execution | narrative-execution (drafting), narrative-consistency |
| `outline/structure.json` + `beats/<ch>.json` | write-ahead Novel→Volume→Chapter tree + per-chapter beat sheet | narrative-architect | narrative-execution, narrative-memory |
| `memory/summaries.json` + `plot_threads.json` | hierarchical summaries + open-loop tracker | narrative-memory | narrative-memory (QA), narrative-architect |

## ID conventions

Stable, human-readable, prefix-typed IDs (this KB is edited by hand and by the AI
across many sessions, so IDs must not churn):

| Kind | Prefix | Example |
|---|---|---|
| Character / person entity | `char_` | `char_ye_fan` |
| World element (place/faction/item/concept) | `elem_` | `elem_black_forest` |
| Event | `evt_` | `evt_wolf_king_fight` |
| Narrative thread | `thr_` | `thr_protagonist` |
| Relation edge | `rel_` | `rel_0042` |
| Chapter | `ch_` | `ch_045` (zero-padded, sortable) |
| Volume | `vol_` | `vol_01` |
| Theme | `thm_` | `thm_revenge` |
| Fact (knowledge) | `fact_` | `fact_king_poisoned` |

Use a readable slug for entities you name once (`char_ye_fan`); use a zero-padded
counter for high-churn auto-generated edges (`rel_0042`). Chapters are
`ch_NNN` so they sort lexically.

**IDs and predicates are always ASCII**, even for non-English novels — a Chinese novel
has `id: "char_ye_fan"`, `predicate: "hates"`, but `canonical_name: "叶凡"`. The prose
language is recorded in `source.language` (`en` / `zh-Hans` / `zh-Hant` / …). See the
schema's "Language conventions" section and the **narrative-locale** skill for
per-language naming, genre, and serial-structure conventions.

## How to use this skill

- **Initialising a new novel** → `python scripts/init_kb.py <novel-slug> --title "..."
  --author "..."` scaffolds the whole project (graph + auxiliary dirs + `reference/` +
  `chapters/profiles/` + README + .gitignore). Then hand off to narrative-genesis to
  populate `world/` and `characters/`.
- **Editing the graph** → read the relevant file, edit, then run the validator.
- **Validating** → `python scripts/validate_narrative.py <novel-slug>/` checks the
  whole KB (canonical graph + auxiliary files + cross-references). Run it after every
  batch of edits; the other skills assume a valid KB.
- **Viewing / profiling / searching** → use the **narrative-toolkit** skill's scripts
  (`view_kb.py`, `build_profile.py`, `search_novel.py`).

## Quality checks before saving any file

1. Every relation/event `participant`/`location`/`subject`/`object` ID must resolve
   to a declared entity (in `ontology.json` entities).
2. Every `thread_id` on an event must exist in `threads`.
3. `valid_to_chapter`, when set, must be ≥ `valid_from_chapter`.
4. No two character states for the same character share a `story_time`.
5. Knowledge-mask `facts_known` IDs must exist in some character state or world rule.
6. No duplicate IDs within a file; no Markdown/HTML inside string fields.

`scripts/validate_narrative.py` enforces all six.

## Reference files

- `references/narrative_schema.md` — full field-level schema for the canonical graph
  and all auxiliary structures, with worked examples.
- `references/project_structure.md` — the novel project layout, what each path is for,
  the `reference/` manifest shape, and the canonical-vs-auxiliary split rationale.
- `scripts/init_kb.py` — initialize a full novel project (dirs + seed files + README).
- `scripts/validate_narrative.py` — whole-KB validator (extends the base
  `validate_ontology.py` checks with the temporal / state / mask / cross-file rules).

The viewing / profile / search tools live in the **narrative-toolkit** skill.
