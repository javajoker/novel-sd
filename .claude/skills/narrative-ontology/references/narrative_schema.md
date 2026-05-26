# Narrative ontology schema (v1.0-narrative)

Strict superset of the base ontology schema v1.0 (`Person|Place|Organization|Object|
Concept|Work|Other` entities, `relations`, `events`, `themes`). Everything here adds
the *temporal*, *stateful*, *masked*, and *multi-threaded* layers a novel needs.
Validator: `scripts/validate_narrative.py`.

`story_time` is the universal clock. It is an integer (use chapter number as the
coarse default, or absolute world-calendar day for fine control — pick one per novel
and record the choice in `timeline/calendar.json`). All temporal fields compare on
this integer.

## Language conventions (the bilingual rule)

A novel can be written in any language (`source.language`), but the graph's *structural*
fields stay ASCII so tooling, validation, and merging are language-independent. This
separation is mandatory:

| Field | Language | Example (Chinese novel) |
|---|---|---|
| entity `id`, event `id`, `thread_id`, `rel_*`, `fact_*` | **ASCII** slug (pinyin/romanized) | `char_ye_fan`, `evt_wolf_fight`, `fact_villain_identity` |
| relation `predicate`, dependency `relation`, world-rule `relation` | **ASCII** snake_case / UPPER_SNAKE (schema vocabulary) | `hates`, `member_of`, `PRECEDES`, `FORBIDS` |
| `canonical_name`, `aliases`, `description`, `name`, `note`, `reason`, beat text, summaries, prose | **project language** | `canonical_name: "叶凡"`, `description: "孤儿剑客……"` |

So a Chinese entity looks like:
```json
{ "id": "char_ye_fan", "canonical_name": "叶凡", "type": "Person", "subtype": "protagonist",
  "aliases": ["叶天帝", "小凡"], "attributes": { "pinyin": "Yè Fán", "element": "水" },
  "description": "为父报仇的孤儿剑客。" }
```
`attributes.pinyin` (optional) keeps a romanization next to the display name. The ASCII
`id` is derived once from the pinyin and never changes even if the display name does.
The validator allows any non-newline characters in `canonical_name`/`description`, so
Chinese passes; it still requires predicates to be ASCII snake_case. See the
**narrative-locale** skill for genre/naming/structure conventions per language.

---

## 1. Canonical graph — `ontology.json`

```json
{
  "ontology_version": "1.0-narrative",
  "source": {
    "novel_title": "...",
    "novel_author": "...",
    "story_time_unit": "chapter",      // "chapter" | "world_day"
    "current_chapter": 50,
    "language": "en",                  // BCP-47 PROSE language: en | zh-Hans | zh-Hant | ja | ...
    "genre": ""                        // optional: 玄幻 | 仙侠 | xianxia | epic_fantasy | ...
  },
  "entities":    [ /* Entity */ ],
  "relations":   [ /* Relation */ ],
  "events":      [ /* Event */ ],
  "themes":      [ /* Theme — identical to base v1.0 */ ],
  "threads":     [ /* NarrativeThread */ ],
  "world_rules": [ /* OntologyTriple */ ]
}
```

### 1.1 Entity (base + narrative fields)

```json
{
  "id": "char_ye_fan",                 // required, prefix-typed (see ID conventions)
  "canonical_name": "Ye Fan",          // required
  "type": "Person",                    // required, base controlled vocab
  "subtype": "protagonist",            // optional novel role: protagonist|antagonist|
                                       //   supporting|faction|location|item|magic_system|concept
  "aliases": ["Fan", "the Stone Emperor"],
  "description": "...",                // ≤ 280 chars
  "attributes": { "age": "19", "element": "Water" },
  "salience": 0.98,                    // importance in the novel, 0..1
  "profile_ref": "characters/char_ye_fan.json",  // optional, for Person: deep profile file
  "state_ref":   "characters/states/char_ye_fan.json", // optional: state timeline file
  "mask_ref":    "masks/char_ye_fan.json"        // optional: knowledge mask file
}
```

`type` stays in the base controlled vocab so merging/export keep working. `subtype`
is the novel-specific role used for dashboards and prompts.

### 1.2 Relation — TIME-VARIANT edge (the soul of the system)

```json
{
  "id": "rel_0042",
  "subject": "char_ye_fan",            // required, entity ID in same file
  "predicate": "hates",                // required, snake_case verb (base rule)
  "object": "char_lin_rou",            // required, entity ID in same file
  "valid_from_chapter": 50,            // required, story_time the edge becomes true
  "valid_to_chapter": null,            // null = still valid; else story_time it ended
  "properties": {                      // quantified, novel-specific
    "trust": -20, "romance": 0, "hate": 90,
    "reason": "Stole the Spirit Orb"
  },
  "context": "He no longer considered her a sister.",  // ≤ 280 chars evidence
  "confidence": 0.95
}
```

**Flip rule.** When a relationship changes (sibling → enemy), do NOT edit the old
edge's predicate. Set the old edge's `valid_to_chapter` to the change chapter and add
a NEW edge with `valid_from_chapter` = change chapter. The graph "as of chapter N" =
all edges where `valid_from_chapter <= N AND (valid_to_chapter IS NULL OR
valid_to_chapter > N)`.

Quantified relationship keys (use consistently): `trust` (−100..100), `romance`
(0..100), `hate` (0..100), `intensity` (0..100), plus free-form `reason`.

### 1.3 Event — scheduled + causal node

```json
{
  "id": "evt_wolf_king_fight",
  "name": "Ye Fan fights the Wolf King",   // required
  "description": "...",                     // ≤ 500 chars
  "thread_id": "thr_protagonist",           // which swimlane (must exist in threads[])
  "story_time": 45,                         // when it occurs (start)
  "duration": 1,                            // in story_time units (days/chapters)
  "location": "elem_black_forest",          // entity ID
  "participants": ["char_ye_fan"],          // entity IDs
  "chapter_id": "ch_045",                   // optional: chapter that renders it
  "status": "drafted",                      // planned|drafted|final
  "dependencies": [                         // causal/chronological edges to other events
    { "event": "evt_enter_forest", "relation": "PRECEDES", "time_gap": "2 days" },
    { "event": "evt_enter_forest", "relation": "ENABLES",  "reason": "must be inside to fight" }
  ],
  "prerequisites": [                        // hard gates checked by paradox guard
    { "type": "possession", "entity": "char_ye_fan", "object": "elem_iron_sword" }
  ],
  "projected_outcome": {                    // what narrative-architect PLANS to happen
    "relation_shifts": [
      { "subject": "char_ye_fan", "predicate": "fears", "object": "elem_wolf_king", "delta": "+30" }
    ],
    "state_changes": [
      { "entity": "char_ye_fan", "kind": "injury", "desc": "broken sword, exhausted" }
    ]
  },
  "context": "..."
}
```

`dependencies.relation` ∈ `PRECEDES` (chronology) | `CAUSES` (logical consequence) |
`ENABLES` (precondition) | `RETALIATION` | `HAPPENED_AFTER`. These edges form the
event graph that narrative-memory traces backward ("why is X happening?") and
narrative-architect validates forward (paradox / travel-time).

### 1.4 NarrativeThread — the swimlane

```json
{
  "id": "thr_protagonist",
  "name": "Ye Fan's revenge arc",
  "description": "...",
  "pov_character": "char_ye_fan",       // default POV for events on this thread
  "start_time": 0,
  "end_time": null,
  "event_ids": ["evt_enter_forest", "evt_wolf_king_fight"],
  "convergences": [                     // where threads meet
    { "with_thread": "thr_villain", "story_time": 60, "location": "elem_blood_sect",
      "knowledge_exchanged": ["fact_villain_identity"] }
  ]
}
```

### 1.5 OntologyTriple — world rule / logic lock

```json
{
  "id": "rule_0001",
  "source": "Fire",                     // free string or entity ID
  "relation": "WEAK_AGAINST",           // UPPER_SNAKE: WEAK_AGAINST|STRONG_AGAINST|
                                        //   RANKS_HIGHER_THAN|LOCATED_IN|ALLIED_WITH|
                                        //   HOSTILE_TO|FORBIDS|REQUIRES|CONFLICTS_WITH
  "target": "Water",
  "scope": "elemental",                 // elemental|hierarchy|geography|faction|taboo
  "note": "Fire spells deal half damage in water-aligned zones."
}
```

These are the rules narrative-consistency (REL-01 / Ontology Guardian) enforces: e.g.
`(Sword Sect)-[FORBIDS]->(Blood Magic)` means a Sword-Sect disciple learning Blood
Magic must trigger an expulsion event or be flagged.

### 1.6 Theme

Unchanged from base v1.0 (`id`, `name`, `description`, `related_entities`,
`related_events`). Use for `thm_revenge`, `thm_redemption`, etc.

---

## 2. Character profile — `characters/<char_id>.json`

The deep profile + frozen T=0 state. Written by narrative-genesis.

```json
{
  "id": "char_ye_fan",
  "name": "Ye Fan",
  "role": "protagonist",
  "base_profile": {
    "appearance": { "age": 19, "build": "lean", "eyes": "black", "features": "scar on left brow" },
    "personality": { "mbti": "INTJ", "traits": ["calm", "vengeful"], "speech": "terse" },
    "background": { "origin": "Qing Village", "family": "orphan", "key_events": ["father killed when 7"] },
    "the_ghost": "Watched his father die and could do nothing.",     // haunting past event
    "the_lie": "Believes strength alone keeps people safe."          // misconception about the world
  },
  "initial_state": {                    // === T=0 snapshot, the continuity baseline ===
    "story_time": 0,
    "location": "elem_qing_village",
    "inventory": [
      { "item": "elem_rusty_sword", "status": "equipped", "significance": "father's blade" },
      { "item": "3 spirit stones", "status": "carried" }
    ],
    "knowledge": [
      { "fact": "fact_own_identity", "confidence": "certain" },
      { "fact": "fact_villain_identity", "confidence": "unknown" }   // does NOT know yet
    ],
    "beliefs": [ { "belief": "Lin Rou is loyal", "is_true": true } ],
    "psychology": { "sanity": 100, "core_desire": "avenge father", "core_fear": "powerlessness",
                    "mood": "guarded", "hate": 0 },
    "abilities": [ { "name": "Basic Swordsmanship", "level": 1, "element": "Water" } ]
  }
}
```

`initial_state` IS the first `CharacterState` (story_time 0). The state timeline file
appends snapshots as the story advances.

---

## 3. Character state timeline — `characters/states/<char_id>.json`

Ordered list of snapshots. narrative-execution appends one whenever a chapter changes
the character's state. **Do not** rewrite earlier snapshots — they are the historical
record that makes "state as of chapter N" queryable.

```json
{
  "character_id": "char_ye_fan",
  "states": [
    {
      "story_time": 45,
      "chapter_id": "ch_045",
      "location": "elem_black_forest",
      "inventory_delta": [
        { "item": "elem_iron_sword", "action": "remove", "reason": "broke fighting wolf" },
        { "item": "elem_crossbow", "action": "add", "reason": "picked up off ground" }
      ],
      "status": [ { "type": "injury", "desc": "fractured left ribs", "severity": "medium" } ],
      "knowledge_gained": [ { "fact": "fact_cave_is_ruin", "source": "discovery" } ],
      "psychology": { "sanity": 80, "mood": "desperate" },
      "abilities_delta": [],
      "derived_inventory": ["elem_rusty_sword", "elem_crossbow", "3 spirit stones"]  // optional cache of full inventory after applying delta
    }
  ]
}
```

`*_delta` arrays hold the *change* this chapter made; `derived_inventory` is an
optional materialised snapshot so readers don't have to replay every delta. The
extractor (DB-01) produces the deltas; a state can be reconstructed by folding all
deltas with `story_time <= N` over `initial_state`.

`status.type` ∈ `injury|buff|debuff|rank_up|recovery|cleansing|psychology|death`.
`inventory_delta.action` ∈ `add|remove|modify`.

---

## 4. Knowledge mask — `masks/<char_id>.json`

The fog of war. For any `story_time`, what does this character KNOW (vs. the global
truth in the graph)? narrative-execution reads this to filter context before drafting
a POV scene, and writes to it when a chapter reveals a fact to the character.

```json
{
  "character_id": "char_ye_fan",
  "knowledge_at": [
    {
      "story_time": 45,
      "facts_known": ["fact_own_identity", "fact_cave_is_ruin"],
      "facts_unknown": ["fact_villain_identity", "fact_lin_rou_is_spy"],
      "beliefs_held": [ { "belief": "the innkeeper is friendly", "is_true": false } ],
      "perception": { "level": "low", "notes": "cannot detect hidden enemies" }
    }
  ]
}
```

**Masking rule (fog of war):** when assembling context to write a scene from
`char_ye_fan`'s POV at story_time 45, include only `facts_known`; strip any graph fact
in `facts_unknown` or not listed; describe `facts_unknown` items by appearance only
("a rusty sword", never "the legendary Dragon Soul Sword") unless the character's
`perception` would reveal them.

---

## 5. Outline (write-ahead) — `outline/structure.json` + `outline/beats/<chapter_id>.json`

### 5.1 `outline/structure.json` — Novel → Volume → Chapter tree

```json
{
  "novel_title": "...",
  "logline": "An orphan hunts his father's killer across a cyber-cultivation world.",
  "volumes": [
    {
      "id": "vol_01", "number": 1, "title": "The Awakening",
      "summary": "...",                 // ≤ 300 words synopsis
      "story_focus": "Ye Fan leaves the village and discovers his element",
      "time_span": { "from": 0, "to": 25 },
      "primary_characters": ["char_ye_fan", "char_lin_rou"],
      "cliffhangers": ["thread:villain revealed at edge of frame"],
      "chapters": [
        {
          "id": "ch_045", "number": 45, "title": "The Hidden Cave",
          "thread_id": "thr_protagonist",
          "pov_character": "char_ye_fan",
          "story_time": 45,
          "planned_events": ["evt_enter_forest", "evt_wolf_king_fight"],
          "one_line": "Ye Fan enters the cave and breaks his sword on the Wolf King.",
          "status": "outlined",         // outlined|beats_ready|drafted|final
          "beat_sheet_ref": "outline/beats/ch_045.json"
        }
      ]
    }
  ]
}
```

### 5.2 `outline/beats/<chapter_id>.json` — the beat sheet (with emotional arc)

```json
{
  "chapter_id": "ch_045",
  "pov_character": "char_ye_fan",
  "scene_arc": "Confidence → Panic → Desperate Triumph",
  "beats": [
    {
      "n": 1, "title": "The Ambush",
      "action": "Ye Fan approaches the wolf, confident in his swordsmanship.",
      "psychology": "Arrogance — he underestimates the beast.",
      "internal_monologue": "Just a beast. My steel is faster.",
      "event_id": "evt_wolf_king_fight"
    },
    {
      "n": 2, "title": "The Shattering",
      "action": "The Wolf King bites the sword; the blade snaps.",
      "psychology": "Shock / fear — the Lie (he is invincible) is challenged.",
      "internal_monologue": "Impossible... this is Cold Iron!"
    }
  ]
}
```

The beat sheet is what narrative-execution's writer consumes. Each beat may link to an
`event_id` so extracted state changes can be reconciled against the plan.

---

## 6. Memory index — `memory/summaries.json` + `memory/plot_threads.json`

### 6.1 `memory/summaries.json` — hierarchical summary tree (L1→L4)

```json
{
  "novel_summary": "...",               // L1: ≤ 500 words, the whole book in one
  "volume_summaries": [
    { "volume_id": "vol_01", "summary": "..." }   // L2: ≤ 1000 words each
  ],
  "chapter_summaries": [                 // L3: per chapter, the searchable record
    {
      "chapter_id": "ch_045",
      "logline": "Ye Fan discovers the Ancient Cave and breaks his sword on the Wolf King.",  // < 30 words
      "synopsis": "...",                 // ~200 words, retains causality + state changes
      "active_entities": ["char_ye_fan", "elem_wolf_king", "elem_rusty_sword"],
      "tags": ["combat", "discovery", "item_destruction"],
      "story_time": 45
    }
  ],
  "scene_chunks": [ /* optional L4: scene-level entries, same shape as base SemanticChunk */ ]
}
```

### 6.2 `memory/plot_threads.json` — open-loop / foreshadow tracker

```json
{
  "plot_hooks": [
    {
      "id": "hook_black_ring",
      "concept": "The Mystery of the Black Ring",
      "status": "dormant",              // open|dormant|at_risk|resolved
      "introduced_chapter": "ch_003",
      "last_mention_chapter": "ch_015",
      "occurrences": [
        { "chapter_id": "ch_003", "note": "Picks up a black ring; it whispers 'Find the Key'." },
        { "chapter_id": "ch_015", "note": "Merchant refuses to buy it, looking scared." }
      ],
      "payoff_planned_chapter": null,
      "risk": "85 chapters since last mention — readers may forget."
    }
  ]
}
```

`status` transitions: `open` (just planted) → `dormant` (unmentioned a while) →
`at_risk` (gone too long, may be forgotten) → `resolved` (paid off). narrative-memory
maintains this; narrative-architect consults it so payoffs get scheduled.

---

## 7. Calendar — `timeline/calendar.json`

```json
{
  "story_time_unit": "chapter",
  "world_calendar": { "epoch": "Spirit Era Year 1024", "current": "Year 1024, Month 5, Day 12" },
  "chapter_to_world_day": { "ch_045": 130 },   // map chapter → absolute world day (optional)
  "travel_rules": [
    { "from": "elem_city_a", "to": "elem_city_b", "distance_km": 1000,
      "terrain": "mountain", "base_days": 4, "note": "−50% speed in mountains" }
  ],
  "movement_speeds": { "Foundation Building": "500 km/day flying" }
}
```

Used by narrative-architect's travel-time calculator and narrative-consistency's
paradox guard (a character can't be in two places at once, or arrive faster than
`travel_rules` allow without a sanctioned accelerator).

---

## What MUST NOT appear (inherited from base v1.0)

- Markdown or HTML inside any string field.
- Newlines in `canonical_name`, `predicate`, `name`, or any `id`.
- Pronouns as canonical names.
- A relation whose `subject`/`object` is not a declared entity.
- An event whose `thread_id` is not a declared thread.
- Two character-state snapshots with the same `story_time` for one character.
