---
name: narrative-genesis
description: Phase I (Genesis) of the NovelForge novel-writing workflow — establish the static world and the initial entity states before any prose is written. Use this skill when starting a new novel or adding foundational world-building. It converts a vague idea into a structured World Bible with ontology-triple logic rules, generates deep character profiles (the Ghost and the Lie), and freezes each character's T=0 state (inventory, knowledge, psychology, abilities) plus the initial social graph. Also handles Socratic brainstorming for users who only have a fuzzy idea, and a lore-conflict guard before anything is saved. Writes world/ and characters/ in a narrative-ontology knowledge base. Read narrative-ontology first for the schema.
---

# Narrative Genesis (Phase I)

> *Goal: build the database's bedrock — the "physical laws" of the world and every
> character's starting state — so the rest of the engine has a consistent foundation.*

This is the first of the four NovelForge phases. It produces **structured data**
(World Bible + character cards + T=0 states), not prose. Everything writes into a
narrative-ontology KB (`world/`, `characters/`, and entity/world_rule entries in
`ontology.json`). **Read `narrative-ontology/SKILL.md` and its `narrative_schema.md`
first** — this skill assumes that layout.

## When to run

- A brand-new novel: scaffold the KB (`narrative-ontology/scripts/init_kb.py`), then
  run genesis.
- Adding a major new region / faction / power tier mid-novel.
- A character who needs a proper T=0 baseline (so continuity tracking works).

If the user only has a fuzzy idea ("a cyberpunk cultivation novel"), start with the
**Socratic Muse** flow (below) before generating anything.

**Language:** if `source.language` is not `en`, write the World Bible, character
profiles, and all content in that language, and consult **narrative-locale** for genre,
naming, and power-system conventions (for Chinese: 境界 realms, 灵根, sect/technique
naming; in-language prompt variants in `narrative-locale/references/zh_prompts.md`). IDs
and relation predicates stay ASCII. Run cognitive-alignment to lock invented terms first.

## The three genesis steps

```
fuzzy idea ──(Socratic Muse, optional)──> clear concept
                                              │
                  ┌───────────────────────────┼───────────────────────────┐
                  ▼                            ▼                            ▼
        1. World Bible              2. Character Profiles          3. T=0 State Init
        (GEN-02 World Structurer)   (CHAR-01 Profiler)             (CHAR-01 State Engine)
        world/world_bible.json      characters/<id>.json           characters/<id>.json
        + world_rules[] triples     + entities[] in graph          .initial_state + social graph edges
```

Run the corresponding prompt from `references/genesis_prompts.md` for each step. They
are the exact wordings (GEN-01/02, CHAR-01) that yield consistent structured output.

### Step 0 — Socratic Muse (only if the idea is vague)

Don't generate the world immediately. Interview the user: **one probing question at a
time**, focused on *second-order effects* (if magic is free, why hasn't the economy
collapsed?). After ~5 rounds, propose generating the World Bible. See prompt GEN-01.

### Step 1 — World Bible

Convert the concept into `world/world_bible.json`: power system (levels, costs,
constraints), geography, factions, and — critically — **ontology triples** that encode
the world's logic as `(source) -[RELATION]-> (target)`. Write those triples into
`ontology.json`'s `world_rules[]` (they are what narrative-consistency enforces). Major
factions / locations / magic systems also become **entities** with `subtype` set
(`faction`, `location`, `magic_system`, `concept`).

Examples of rules to extract as triples:

- Elemental: `(Fire) -[WEAK_AGAINST]-> (Water)`
- Hierarchy: `(Core Disciple) -[RANKS_HIGHER_THAN]-> (Inner Disciple)`
- Geography: `(Black Forest) -[LOCATED_IN]-> (Northern Continent)`
- Taboo: `(Sword Sect) -[FORBIDS]-> (Blood Magic)`

### Step 2 — Character profiles

For each named character generate `characters/<char_id>.json` with `base_profile`. Go
beyond appearance: capture **the Ghost** (a past event that haunts them) and **the
Lie** (a misconception they hold about the world) — these drive the emotional arc that
narrative-architect plans against. Add the character as an `entity` (type `Person`,
`subtype` protagonist/antagonist/supporting) in `ontology.json` with `profile_ref`,
`state_ref`, `mask_ref` pointing at the files.

### Step 3 — T=0 state instantiation (the critical technical point)

This is what separates NovelForge from a notes app. Freeze time at story start and
record exactly what each character **possesses, knows, and feels** — the `initial_state`
block in `characters/<char_id>.json` (see schema §2). Then lay down the **initial
social graph** as relations in `ontology.json` with `valid_from_chapter: 0`:

```json
{ "id": "rel_0001", "subject": "char_ye_fan", "predicate": "childhood_friend_of",
  "object": "char_lin_rou", "valid_from_chapter": 0, "valid_to_chapter": null,
  "properties": { "trust": 80, "reason": "Grew up in the same village" } }
```

Knowledge at T=0 is also the first **knowledge mask** entry (`masks/<id>.json`,
story_time 0): list what they know and — just as important — what they *don't*
(`facts_unknown` usually includes the villain's identity). Create the matching `fact_`
entities they reference so the mask validates.

## Lore-conflict guard (before saving)

Before committing new world settings, check them against existing `world_rules[]` and
prior lore. Use prompt GEN-03 (Logic Police): does the proposed setting contradict an
existing rule, or is it a valid exception? E.g. "Day-Walker vampires use mana to shield
from the sun" vs. the rule "vampires burn in sunlight" — flag as conflict *or* explain
the sanctioned exception, don't silently allow both.

## Output checklist

After genesis, the KB should have:

- [ ] `ontology.json.source.tier` set to one of `short_story` / `novella` / `novel` /
      `long_novel` — drives the minimum chapters-per-volume floor that
      narrative-architect enforces (short_story: none; novella: 10; novel: 30;
      long_novel: **80**).
- [ ] `world/world_bible.json` populated (power system, geography, factions).
- [ ] `ontology.json.world_rules[]` with the logic-lock triples.
- [ ] `ontology.json.entities[]` for every named character + major world element.
- [ ] `characters/<id>.json` with `base_profile` + `initial_state` per character.
- [ ] `ontology.json.relations[]` for the initial social graph (all `valid_from_chapter: 0`).
- [ ] `masks/<id>.json` story_time-0 entry per POV character.
- [ ] `python narrative-ontology/scripts/validate_narrative.py <novel-slug>/` passes.

Then hand off to **narrative-architect** (Phase II) to plan the timeline and outline.

## Reference files

- `references/genesis_prompts.md` — GEN-01 (Socratic Muse), GEN-02 (World Structurer),
  GEN-03 (Lore Conflict Guard), CHAR-01 (Profiler + T=0 State Engine), with the exact
  system roles and the JSON output contracts.
