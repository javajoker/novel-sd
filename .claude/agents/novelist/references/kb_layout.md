# Novel KB layout cheat-sheet

The single working directory `<novel-slug>/` that all six narrative skills share. Full
field-level schema: `narrative-ontology/references/narrative_schema.md`.

```
<novel-slug>/
├── ontology.json              ← CANONICAL graph: entities, temporal relations, events, threads, world_rules
├── world/
│   ├── world_bible.json       ← power system, geography, factions, ontology_triples
│   └── elements/<id>.json      (optional) one file per world element
├── characters/
│   ├── <char_id>.json         ← base profile + initial_state (T=0)
│   └── states/<char_id>.json  ← append-only CharacterState deltas over story-time
├── timeline/
│   ├── threads.json           ← NarrativeThread[] (multi-POV swimlanes), small registry
│   ├── events/                ← event graph mirror, sharded for scoped reads
│   │   ├── index.json         ← by_chapter / by_story_time / by_thread → event IDs (+ last_*)
│   │   └── <thread_id>.json    ← one shard per thread: its event stubs, by story_time
│   └── calendar.json          ← world calendar + current_*/chapter_to_story_time + travel_rules
├── outline/
│   ├── structure.json         ← Novel→Volume→Chapter write-ahead tree
│   └── beats/<chapter_id>.json← BeatSheet: ordered beats + emotional arc
├── masks/
│   └── <char_id>.json         ← KnowledgeMask: facts_known/unknown per story-time
├── chapters/
│   ├── <chapter_id>.md        ← prose
│   └── profiles/<chapter_id>.json ← chapter-masked KB profile (the memory primitive)
├── memory/
│   ├── summaries.json         ← L1 novel / L2 volume / L3 chapter / L4 scene
│   └── plot_threads.json      ← open-loop / foreshadow tracker
└── reference/
    ├── index.json             ← manifest of reference docs/resources
    └── <dropped files>        ← research, source texts, style samples, maps, art
```

## Who reads / writes what

| Path | Written by | Read by |
|---|---|---|
| `ontology.json` (entities, world_rules) | genesis, execution (lore) | all |
| `ontology.json` (relations, temporal) | genesis (T=0), execution (extract) | architect, execution, memory, consistency |
| `ontology.json` (events, threads) | architect | execution, memory, consistency |
| `world/` | genesis, execution (LORE-01) | all (pre-checks) |
| `characters/<id>.json` | genesis | all |
| `characters/states/<id>.json` | execution (DB-01) | execution (mask context), consistency |
| `timeline/events/<thr>.json` + `index.json` | execution (C-5, regenerated from canon) | execution (CTX-01 scoped read: POV shard + index) |
| `timeline/calendar.json` | genesis/architect (setup); **execution every chapter** (current_*/chapter_to_story_time) | execution (CTX-01 time window), architect (travel-time), consistency (paradox) |
| `outline/structure.json` + `beats/` | architect | execution, memory |
| `masks/<id>.json` | genesis (T=0), execution (reveal) | execution (fog of war), consistency |
| `chapters/<id>.md` | execution | memory (indexing) |
| `memory/summaries.json` | memory | execution (context), memory (QA) |
| `memory/plot_threads.json` | memory | architect (schedule payoffs) |

## ID prefixes (from narrative-ontology)

`char_` character · `elem_` world element · `evt_` event · `thr_` thread ·
`rel_` relation edge · `ch_` chapter (zero-padded) · `vol_` volume · `thm_` theme ·
`fact_` knowledge fact · `rule_` world-rule triple.

## Story-time

One integer clock (`story_time`) for the whole KB — chapter number by default, or
absolute world-day for fine control. Recorded in `ontology.json.source.story_time_unit`
and `timeline/calendar.json`. All temporal comparisons (`valid_from_chapter`,
state `story_time`, mask `story_time`, event `story_time`) use it.

## The scripts

```bash
# lifecycle (narrative-ontology)
python narrative-ontology/scripts/init_kb.py <novel-slug> --title "..." --author "..."
python narrative-ontology/scripts/validate_narrative.py <novel-slug>/   # structure + cross-refs

# continuity (narrative-consistency); --as-of N, --class X, --json
python narrative-consistency/scripts/check_consistency.py <novel-slug>/

# operate (narrative-toolkit)
python narrative-toolkit/scripts/view_kb.py <novel-slug>/ --timeline      # inspect
python narrative-toolkit/scripts/build_profile.py <novel-slug>/ --chapter ch_045  # memory snapshot
python narrative-toolkit/scripts/search_novel.py <novel-slug>/ "query" --as-of 45  # KB-first + KAG
```

Tools that read the KB share `narrative-toolkit/scripts/narrative_kb.py` (the as-of
folding engine). To plug in dense embeddings for search, swap the scoring functions
there; the two-stage structure is unchanged.

> **Context-window discipline (CTX-01).** `build_profile.py` is the working-set primitive
> for Phase III-B: it materializes the chapter-masked profile (folded state + active mask)
> that — together with the beat sheet, the last 1–3 summaries, the targeted plot hooks, the
> **calendar window** (`timeline/calendar.json` current_*/chapter_to_story_time), and the
> **POV's event-thread shard** (`timeline/events/index.json` → `events/<thr>.json`) — is the
> *only* context a chapter is drafted from. The event mirror is sharded by thread so a
> chapter never loads the whole event history. Pull other shards / KB records (or prior
> prose via `search_novel.py`) on demand; never load the full manuscript. See
> `narrative-execution/SKILL.md` §B-0.
