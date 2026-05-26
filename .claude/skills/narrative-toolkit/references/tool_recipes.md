# Toolkit recipes

Command recipes for each moment in the writing loop, plus the JSON shapes the tools emit.
Assume `<n>` is the novel project directory and the scripts are on PATH (or invoked with
their full skill path).

## Recipe: initialize a new novel project

```bash
python init_kb.py <n> --title "My Novel" --author "Me" --unit chapter   # narrative-ontology
python view_kb.py <n>                                                    # confirm empty overview
# → then run narrative-genesis to populate world/ and characters/
```

## Recipe: before drafting chapter N (assemble memory)

```bash
python build_profile.py <n> --chapter ch_050           # → chapters/profiles/ch_050.json
python view_kb.py <n> --snapshot 50                     # sanity-check the world state
```
Feed `chapters/profiles/ch_050.json` to narrative-execution's writer as the context. It
is masked to the POV and capped at chapter 50, so no future spoilers and no god-view.

## Recipe: answer a reader/author question

```bash
python search_novel.py <n> "how did Ye Fan and Lin Rou's relationship change?"
# Stage 1 gives the relations + events; Stage 2 gives the prose passages to cite.
# Then narrative-memory MEM-03 synthesises a cited answer from these fragments.
```

## Recipe: "did I drop a plot thread?"

```bash
python view_kb.py <n>                  # the overview lists open / at-risk plot threads
python search_novel.py <n> "the black ring mystery"   # find every occurrence in prose
# → feed to narrative-memory MEM-04 to set the hook's status and suggest a payoff
```

## Recipe: audit continuity before finalizing a chapter

```bash
python validate_narrative.py <n>                 # structure + cross-refs (narrative-ontology)
python check_consistency.py <n> --as-of 50       # paradox/possession/knowledge/ripple (narrative-consistency)
```

## Recipe: onboard a co-author to the world

```bash
python view_kb.py <n>                       # overview
python view_kb.py <n> --timeline            # the multi-thread structure
python view_kb.py <n> --character char_ye_fan
```

## JSON shapes (with --json)

### `build_profile.py` → chapter-masked profile
```json
{
  "chapter_id": "ch_050", "story_time": 50, "pov_character": "char_ye_fan",
  "summary_context": { "novel": "...", "volume": "...", "recent_chapters": [ {"chapter_id","logline","story_time"} ] },
  "active_entities": [ { "id","name","type","subtype","description", "state": { "location","inventory","status","psychology","knowledge" } } ],
  "relations_in_effect": [ { "subject","subject_name","predicate","object","object_name","properties","since_chapter" } ],
  "events_so_far": [ { "id","name","story_time","thread_id","participants" } ],
  "pov_knowledge_mask": { "facts_known","facts_unknown","beliefs_held","perception" },
  "visible_facts": [ "fact_..." ],
  "open_plot_threads": [ { "concept","status","last_mention","risk" } ],
  "world_rules": [ ... ],
  "token_estimate": 879
}
```

### `search_novel.py --json` → two-stage result
```json
{
  "query": "...", "as_of": 50,
  "kb": {
    "entities":  [ {"id","name","type","subtype","score"} ],
    "events":    [ {"id","name","story_time","score"} ],
    "relations": [ {"subject","predicate","object","since","properties","score"} ],
    "world_rules":[ {"triple","note","score"} ]
  },
  "passages": [ { "chapter_id","story_time","score","source":"prose|summary","snippet" } ]
}
```

### `view_kb.py --json`
Shape depends on the view: `--timeline` → `{swimlanes:{thread_id:{name,pov,events[]}}}`;
`--snapshot N` → `{as_of_story_time, characters[], relations_in_effect[], events_so_far[]}`;
`--character ID` → `{id,name,subtype,base_profile,initial_state,state_timeline[],relations[]}`.

## Notes

- All tools degrade gracefully on a partial KB: no prose yet → search falls back to
  chapter summaries; no states yet → snapshot shows T=0; no outline yet → `--chapter`
  can't resolve (use `--story-time`).
- `reference/` materials are not auto-ingested into search. Register them in
  `reference/index.json`; pull them in deliberately when researching, so invented lore
  stays separable from source research.
