# Novel project structure

What `scripts/init_kb.py` creates, and what each path is for. This is the structure a
novel is *initialized* into — a self-contained, version-controllable project where the
prose and the world-state knowledge base live side by side.

```
<novel-slug>/
├── README.md                     # project guide + tool cheat-sheet (generated)
├── .gitignore                    # ignores .index/ search cache (the KB itself IS tracked)
├── ontology.json                 # CANONICAL temporal graph (entities, relations, events, threads, world_rules)
│
├── world/
│   └── world_bible.json          # worldview: power system, geography, factions, ontology_triples (logic rules)
│
├── characters/
│   ├── <char_id>.json            # base profile + initial_state (T=0 baseline)
│   └── states/
│       └── <char_id>.json        # append-only per-chapter state deltas (inventory/status/knowledge/psychology)
│
├── timeline/
│   ├── threads.json              # narrative threads (multi-POV swimlanes)
│   ├── events.json               # event graph mirror
│   └── calendar.json             # world calendar, travel_rules, movement_speeds
│
├── outline/
│   ├── structure.json            # Novel → Volume → Chapter write-ahead tree
│   └── beats/
│       └── <chapter_id>.json      # per-chapter beat sheet (beats + emotional arc)
│
├── masks/
│   └── <char_id>.json            # knowledge mask: facts_known / facts_unknown per story-time (fog of war)
│
├── chapters/
│   ├── <chapter_id>.md           # the prose draft
│   └── profiles/
│       └── <chapter_id>.json      # CHAPTER-MASKED KB PROFILE (built by build_profile.py) — the memory primitive
│
├── memory/
│   ├── summaries.json            # hierarchical summaries L1 novel / L2 volume / L3 chapter / L4 scene
│   └── plot_threads.json         # open-loop / foreshadow tracker
│
└── reference/
    ├── index.json                # manifest of reference materials (see below)
    └── <dropped files>           # research, source texts, style samples, maps, art, notes
```

## The four things this structure gives you (mapped to the requirements)

1. **Chapter masked / indexing ontology + chapters.** `ontology.json` is the index;
   `world/`, `outline/`, `characters/`, `timeline/` are the worldview/outline/character/
   event data; `chapters/` holds the prose. `chapters/profiles/<id>.json` is the
   *chapter-masked* view — the KB folded to that chapter and masked to the POV.

2. **Tools to view the KB.** `view_kb.py` (narrative-toolkit) renders the KB by
   timeline, character, event graph, or chapter snapshot — each respecting the temporal
   graph (relations only show while valid; inventory/knowledge reflect the as-of state).

3. **Tools for semantic search.** `search_novel.py` (narrative-toolkit) searches the
   ontology/KB first, then does KAG retrieval over the sub-chapter prose, scoped by the
   chapter-masked profile (graph-expanded entities, `--as-of N`).

4. **A place for reference docs/resources.** `reference/` holds external materials, with
   `reference/index.json` as the manifest. Kept separate from invented lore so research
   never leaks into the canon by accident.

## `reference/index.json` manifest shape

```json
{
  "description": "Manifest of external reference docs/resources for this novel.",
  "resources": [
    { "id": "ref_0001", "title": "Tang dynasty court structure",
      "path": "reference/tang_court.md", "kind": "research",
      "note": "Source for the Imperial Sect hierarchy." },
    { "id": "ref_0002", "title": "Author voice sample",
      "path": "reference/voice_sample.md", "kind": "style",
      "note": "Match this prose rhythm." }
  ]
}
```

`kind` ∈ `research | style | map | art | notes | source_text`. Register every file you
drop into `reference/` so the agent knows it exists and what it is for. Reference
material is **not** auto-ingested into the novel's ontology or search corpus — pull it in
deliberately when researching, so the line between *your world* and *your sources* stays
clear.

## Why the split (canonical graph vs. auxiliary files)

`ontology.json` stays small and queryable — it is loaded in full by every tool. The
bulky, fast-changing, or per-entity data lives in sibling files referenced from the
graph (`profile_ref` / `state_ref` / `mask_ref` on entities):

- character **state timelines** grow every chapter → their own files.
- **knowledge masks** are per-character and per-time → their own files.
- **beat sheets** and **chapter profiles** are per-chapter → their own files.
- **prose** is the largest data → plain `.md`, never inlined into JSON.

This keeps the canonical graph cheap to load while the heavy data scales out.

## Version control

The whole project is meant to be a git repository: the prose AND the knowledge base are
the product, so track them. Only `.index/` (the optional embedding/search cache) is
gitignored — it is derived and rebuildable.
