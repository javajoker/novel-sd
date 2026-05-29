---
name: narrative-execution
description: Phase III (Execution) of the NovelForge novel-writing workflow — the core write-and-update loop that treats writing as a database transaction. Split into two sequential sub-phases with a hard gate between them. Phase B (WRITE) drafts prose from the chapter beat sheet (synthesized from event beat designs) under knowledge masking (fog of war); it stops and returns to narrative-architect if the beat cannot be followed exactly. Phase C (KB UPDATE) reverse-extracts state changes from the finalised prose into the knowledge base — character states, masks, ontology/timeline events and threads, world lore, outline status, and memory indexes. One chapter may cover multiple events; one event may span multiple chapters. Run after narrative-architect; read narrative-ontology first.
---

# Narrative Execution (Phase III)

> *Two sub-phases, one gate between them.*
> **Phase B — WRITE:** draft prose. Do not update KB.
> **Phase C — KB UPDATE:** update KB from prose. Do not write new prose.

This phase runs once per chapter. A chapter may cover multiple events (from the timeline);
one event may also span multiple chapters (via foreshadowing or multi_pov technique).
**Read `narrative-ontology/SKILL.md` first.**
Run after narrative-architect has synthesized and validated the chapter beat sheet.

**Language:** for non-English novels, draft prose in the project language; the state
extractor (DB-01) still emits ASCII predicates but reads in-language prose. For Chinese,
apply the locale's extraction traps — 成语/比喻 (心如刀绞 = psychology, not injury),
看/望 vs. 拿/夺 (observe vs. acquire), 突破 vs. 重伤 (breakthrough vs. injury). See
**narrative-locale** and `zh_prompts.md`.

---

## Phase B — WRITE (prose only)

**Gate prerequisite:** the narrative-architect output checklist for this chapter must be
complete. If `outline/beats/<ch>.json` is missing, incomplete (missing `events_covered`
list), or stale, stop — return to narrative-architect to re-synthesize. Do not draft
without a valid beat sheet. If the chapter covers multiple events, all their beat designs
must be complete before writing any of them.

**Phase B produces exactly one file:** `chapters/<chapter_id>.md`.
**Phase B must not write any other KB file.** KB updates are Phase C's job.

### B-0 — Context-window discipline (CTX-01) — read this BEFORE assembling context

> **Write each chapter from a small, chapter-scoped working set — never the whole
> manuscript or the whole KB.** Loading "everything" to be safe is the anti-pattern that
> wrecks both quality and cost: the model drifts, latency explodes, and the context limit
> is hit early on long novels. The KB exists precisely so you *don't* have to.

**The default working set (load only these):**

1. `outline/beats/<ch>.json` — this chapter's beat sheet (the agenda).
2. The **POV's materialized profile** at this `story_time` — the folded state snapshot +
   active mask. Build it with `narrative-toolkit/scripts/build_profile.py` rather than
   reading the full `characters/states/<id>.json` history by hand. This one object carries
   the POV's current inventory, status, psychology, abilities, and `facts_known`.
3. Materialized profiles for **other on-scene characters only** — not the whole cast.
4. `memory/summaries.json` — **only the last 1–3 chapter synopses** (continuity tail), not
   the full summary history.
5. `memory/plot_threads.json` — **only the open hooks the beat sheet targets**, not every
   thread.
6. The specific `ontology.json` slices the beats touch: the `events[events_covered]`
   beat designs, the **as-of-chapter** relation edges for on-scene characters, and any
   `world_rules` a beat could violate.
7. **The calendar window** — `timeline/calendar.json`: `current_story_time` /
   `current_chapter` / the `chapter_to_story_time` entry for this chapter (so the prose
   knows "what time is it now" without scanning the event graph), plus the `travel_rules`
   and `movement_speeds` that apply **only if** this chapter changes location.
8. **The POV's event-thread shard, time-scoped** — read `timeline/events/index.json` (tiny)
   to resolve which event IDs sit in this chapter / story-time window / the POV's thread,
   then load **only** the POV thread shard `timeline/events/<thr>.json` for that window.
   Other threads' shards are loaded only when a beat explicitly references a cross-thread
   event (e.g. a convergence). **Never load the full event graph** (`ontology.json.events`
   or every shard) to write one chapter.

**Expand outward only on demand.** If a beat references a fact, item, place, prior scene,
character, or **another thread's event** not in the working set, *then* pull that one
record — a single prior chapter's prose via `search_novel.py`, one more character's profile,
one lore entry, one other thread shard. Pull the specific record, not the whole file; close
it mentally once used. Never preload the full manuscript "just in case."

**Do not read full prose of earlier chapters to maintain continuity** — that is what
`memory/summaries.json` + the materialized profile are for. Reach for raw prose only when
a beat needs an exact callback (a line of dialogue, a precise description) that the summary
doesn't preserve, and then fetch just that passage.

This keeps every chapter self-contained: it is written from the timeline context, the
character's current state, the recent-memory tail, and its own beats — which is also what
keeps voice/style consistent and lets foreshadowing, reverse-order, and contradiction
handling work inside a bounded window.

### B-1 — Context assembly + knowledge masking (WRITE-01a, Fog of War)

Assemble the chapter-scoped working set from B-0. The table below is the **menu** of KB
files — load the rows you need for *this* chapter's beats, not all of them every time:

| KB file | What to read | Purpose |
|---|---|---|
| `outline/beats/<ch>.json` | This chapter's beat sheet + `events_covered` list | Scene agenda; emotional arc; POV; which events to narrate |
| `ontology.json` → `events[events_covered]` | Each event's `beat_design` sub-object | Technique, scene arc, key moment, POV constraint per event |
| `outline/structure.json` | Volume arc + chapter position | Pacing, cliffhangers, vol-level goals |
| `characters/states/<pov>.json` | Latest snapshot ≤ this story_time | POV's inventory, psychology, abilities |
| `characters/states/<other>.json` | Other scene participants | Their abilities and limits |
| `masks/<pov>.json` | Entry at this story_time | **Fog of War**: what the POV knows |
| `ontology.json` → `entities` + `relations` | As-of-chapter Graph-RAG | Current relationship edges, trust levels |
| `ontology.json` → `world_rules` | All rules | Pre-check: would a beat violate a rule? |
| `world/world_bible.json` | Setting, power system, factions | Lore accuracy in descriptions |
| `memory/summaries.json` | Last 1–3 chapter synopses | Continuity: tone, open threads, callbacks |
| `memory/plot_threads.json` | Open hooks relevant to this chapter | Must not silently drop an active thread |
| `timeline/calendar.json` | `current_*` + `chapter_to_story_time` (always); `travel_rules`/`movement_speeds` only if location changes | Current time-of-story; paradox prevention |
| `timeline/events/index.json` + `events/<pov_thr>.json` | Index (always) → POV thread shard for this story-time window | Time-scoped event context; avoids loading the full event graph |

Then apply three filters in order:

1. **Graph-RAG (precise facts):** reconstruct each character's state by folding
   `characters/states/<id>.json` deltas with `story_time ≤ N` over their `initial_state`.
   Pull current relation edges from `ontology.json.relations` (those with
   `valid_from_chapter ≤ N` and `valid_to_chapter = null` or `≥ N`).
2. **Ontology pre-check (REL-01):** if a beat's action violates a `world_rule`, inject a
   warning so the prose respects the rule or explicitly motivates the exception.
3. **Mask (Fog of War):** load `masks/<pov_id>.json` at this `story_time`. Use only
   `facts_known`; strip `facts_unknown` from context; refer to unknown-name items by
   appearance only ("a rusty sword", not "the Dragon Soul Sword").

The output is a **filtered scene context** — the only world-state the writer may use.

### B-2 — Beat-exact drafting (WRITE-01b)

Draft the scene from the beat sheet + filtered context. Mandatory constraints:

- Use the character's current **inventory** items explicitly where relevant.
- Reflect their current **psychology** in tone — no blank-slate resets between chapters.
- Use no ability the POV does not currently possess.
- Pay off any open `plot_threads` hook that the beat sheet targets.
- Follow the beat sheet's `scene_arc` (e.g. "Confidence → Panic → Desperate Triumph").
- Write in the project language per **narrative-locale** conventions.

**If you cannot follow a beat without contradicting world rules, character state, or
established facts:** stop, surface the conflict to the author, and return to
narrative-architect for a plan revision. Do not improvise around a gate violation
silently — that is how continuity drift starts.

### B-2a — Prose-density floor (LEN-01) — a chapter must FULLY REALIZE its beats

A beat sheet is a director's note, not a synopsis to be transcribed. A drafted chapter that
merely *lists* what happens in a few terse lines is **not done** — it must dramatize each
beat with scene texture. Over-compression is as much a defect as a continuity error.

**Hard minimum (non-negotiable):** a single drafted unit must reach the language floor:

| Language | Per-chapter floor | Standard target | Major-event target |
|---|---|---|---|
| Chinese (字) | **≥ 1,500 字** | 2,000–3,000 字 | 3,000–5,000+ 字 |
| English (words) | **≥ 1,000 words** | 1,500–2,500 words | 2,500–4,000+ words |

A draft below the floor is rejected at the WRITE GATE — expand it before it can pass.
(For Chinese 网文 sizing conventions see **narrative-locale**; the floor never drops below
the table above regardless of genre.)

**Length comes from realization, not padding.** To reach the floor, develop — do not repeat
or inflate:

- **Scene grounding** — where, when, the sensory field (light, sound, temperature, smell);
  open every scene in a concrete place at a concrete time.
- **Full dialogue exchanges** — let conversations breathe across multiple turns with beats,
  pauses, and subtext; never collapse an exchange to a single reported line.
- **Interiority** — extended POV observation, reasoning, memory, and emotional movement,
  filtered through the mask (only what the POV knows). One sentence of inner life is not
  enough for a beat that turns on it.
- **Physical action and blocking** — show characters moving through space and handling
  objects, not just speaking in a void.
- **Rhythm** — vary sentence length; let a key moment land with its own paragraph.

**Length serves the event, not a quota.** A chapter may run long to finish its event(s) —
length is *unlimited* on the high side, and one continuous draft may cover several beats or
events that the author later splits into multiple chapters. But it may never fall below the
floor. If a beat sheet's `prose_notes` carry an `avoid` list or a "短/简" tone cue, that
guides **register and restraint of plot, not word count** — terse *tone* is fine; a terse
*chapter* that skips scene realization is not. When in doubt, dramatize the beat in full.

After drafting, do a quick length check (`wc -m` for 字, `wc -w` for words). If under floor,
return to the beats and realize the under-developed ones before saving as final.

Save draft to `chapters/<chapter_id>.md`. The author reviews and edits.
**The final edited text is the input to Phase C.** Phase C must not begin until prose is
accepted as final.

---

## Phase C — KB UPDATE (extract and store)

**Gate prerequisite:** `chapters/<chapter_id>.md` is accepted as final prose.
Do not begin Phase C until the prose is done. Do not write new prose in Phase C.

Phase C updates all KB files in the canonical sequence below — this order prevents
dependency conflicts (states before masks, masks before ontology relations, ontology
before timeline mirrors, etc.).

### C-0 — Automation + the sync gate (run this; do not hand-skip the mirrors)

Several Phase-C steps are **deterministic mirrors** of canon (the prose + beat sheets)
and carry no authorial judgement: the chapter cursor, `timeline/calendar.json`, outline
chapter status, and the *existence* of a per-chapter summary entry. These are exactly the
steps that get silently dropped under batch pressure — leaving the calendar and memory
frozen dozens of chapters behind the prose. **Do not regenerate them by hand.** Run:

```
python .claude/skills/narrative-execution/scripts/sync_kb.py --write <novel-slug>/
```

It propagates only facts already in canon (it parses each chapter's `siege_day N` as the
authoritative world clock), normalizes off-vocabulary statuses (`written` → `drafted`),
advances `current_chapter`, rebuilds `chapter_to_story_time` / `chapter_to_world_day`, and
appends **skeleton** summary entries (marked `"_autogen": true`) for any missing chapter.
It deliberately does **not** fabricate authorial content: relation edges, plot-thread
occurrences, convergences, and the *prose* of summaries still need the manual passes below
(C-1, C-2, C-3 relations, C-7 plot_threads, enriching the `_autogen` summaries).

**The gate (non-skippable):** a chapter/batch is not "done" until the freshness gate is
green:

```
python .claude/skills/narrative-ontology/scripts/validate_narrative.py <novel-slug>/
```

This now **errors** (exit 1) if the cursor/calendar/summaries/status lag the written
chapters — so a truncated Phase C can no longer hide behind a green "✓ valid". Do not
commit a batch while this gate is red. (`--no-freshness` runs structural checks only.)

**Event-graph consistency (second automation + gate).** `ontology.json#events` is the
single source of truth for the event graph; three classes of file reference or mirror it
and drift apart. The orphan trap: an event ID written into a chapter's `events_covered`
(beats), `planned_events` (structure), or `events_covered` (summaries) that was *never
declared* in `ontology.json#events` — the old structural validator skipped this (check #9
ignores `planned_events` so early outlining isn't blocked), so a written chapter could
reference a ghost event forever. Repair + regenerate the timeline mirrors with:

```
python .claude/skills/narrative-execution/scripts/sync_events.py --write <novel-slug>/
```

It (a) creates an ontology event **stub** (`"_stub": true`) for every orphan ref, deriving
`story_time` / `thread_id` / `chapter_ids` / `status` / `name` from the referencing
structure chapter + prose-on-disk; (b) adds each event to exactly one thread's `event_ids`
(in story_time order); and (c) regenerates `timeline/events.json`, the `timeline/events/`
shards + `index.json`, and `timeline/threads.json` wholesale as faithful projections of
ontology. Like `_autogen` summaries, a stub is a placeholder — its `name`,
`projected_outcome`, participants, and dependencies need a human pass. It will **not**
auto-assign a thread when structure gives no `thread_id` (reported, never faked).
`validate_narrative.py` **errors** (exit 1) on any orphan ref, any event not in exactly one
thread, or any timeline-mirror coverage gap. (`--no-events` runs without this gate.)

### C-1 — Character state snapshots

For every character whose inventory, status, psychology, or knowledge changed in the
prose: write a new time-stamped snapshot to `characters/states/<id>.json`. Rules:

- Snapshots are **append-only deltas** — do not edit existing snapshots.
- Set `story_time` to this chapter's story_time.
- Emit only the fields that changed (inventory_delta, status, psychology, knowledge_gained).

### C-2 — Knowledge masks

For each POV character (and any non-POV who explicitly learned something in the scene):
update `masks/<id>.json`. For each fact the prose shows the character learning:

- Move the fact from `facts_unknown` to `facts_known` (timestamp: this chapter).
- If the architect placed a `projected_facts_to_learn` entry at this story_time, confirm
  or correct it: promote confirmed facts to `facts_known`, mark unlearned projections as
  `projected` still.
- **Never promote a fact to `facts_known` based on planning alone** — only prose-confirmed
  events count.

### C-3 — Ontology: relations, events, threads, world_rules, current_chapter

Update `ontology.json` in four passes:

**Relations:**
- When a relationship flips: terminate the old edge (`valid_to_chapter = N`) and create a
  NEW edge (`valid_from_chapter = N`). Never mutate the old edge's predicate — history
  must stay queryable.
- Trust/hate/romance shifts → emit new relation edges.

**Events:**
- For each event ID in the chapter's `events_covered` list: advance
  `status: planned → drafted`. (An event that spans multiple chapters advances to
  `drafted` only when its final chapter is complete; mark it `partially_drafted`
  in intermediate chapters.)
- Correct `projected_outcome` where the actual prose diverged from the architect's
  projection.
- Add any event improvised in prose (full fields: story_time, participants, thread_id,
  dependencies, projected_outcome, status: drafted).
- **Invariant — declare before you reference.** Any event ID that appears in a chapter's
  `events_covered` (beats), `planned_events` (structure), or `events_covered` (summaries)
  **must** exist here in `ontology.json#events`. Referencing an undeclared event is the
  orphan bug; `sync_events.py` will create a `_stub` for it and the event gate will error
  until it exists. Declare the event here first; fill the stub's semantics by hand.

**Threads:**
- Append new event IDs to the relevant thread's `event_ids` (each event belongs to
  **exactly one** thread).
- Record any new convergence (where threads met in this chapter) with story_time,
  location, and knowledge exchanged.

**World rules + current_chapter:**
- Add any new lore-rules discovered in prose (LORE-01, step C-4).
- Advance `ontology.json.source.current_chapter` to this chapter number.

### C-4 — Dynamic lore writeback (LORE-01)

The writer often improvises new proper nouns ("the Star-Fire Grass"). Detect concepts not
yet in the KB and create entries in `world/world_bible.json` + `ontology.json` entities
so they become canonical. Do not let improvised lore stay un-tracked.

### C-5 — Timeline mirrors + calendar (regenerate from canon)

After `ontology.json` is updated, regenerate the cheap, query-scoped mirrors from it. The
three event-mirror files below are **deterministic projections of ontology** — do not
hand-append them; run `sync_events.py --write` (C-0) and it regenerates all three
wholesale, faithfully and idempotently. The bullets describe what it produces:

- `timeline/events.json` (flat) — `{id, story_time, thread_id, chapter_ids, status}` per
  event; and `timeline/events/<thread_id>.json` — per-thread shard, sorted by story_time.
  Mirrors reference `ontology.json#events`; do not author event truth here.
- `timeline/events/index.json` — chapter event IDs under `by_chapter[ch]` (keyed on the
  event's primary/first chapter), `by_story_time[t]`, and `by_thread[thr]`; `last_story_time`
  + `last_chapter` track the cursor (`source.current_chapter`).
- `timeline/threads.json` — thread stubs with updated `event_ids`, `convergences_with`, and
  `current_time`.
- **`timeline/calendar.json` (state-bearing — update every chapter, do NOT leave frozen;
  this one is `sync_kb.py`'s job, not `sync_events.py`'s):**
  - advance `current_story_time` and `current_chapter`;
  - append `chapter_to_story_time[<ch>] = <story_time>`;
  - **if** the prose advances an in-world date or moves a character between locations:
    append `chapter_to_world_day[<ch>]` and refresh `world_calendar.current`; add any new
    `travel_rules` / `movement_speeds` the prose established (LORE-01-style).

> Legacy KBs may still carry a flat `timeline/events.json`; new writes go to
> `timeline/events/`. If a flat file is present, you may migrate it once (split by thread)
> or leave it as a read-only fallback — but keep `timeline/events/` authoritative going
> forward.

### C-6 — Outline status

In `outline/structure.json`, advance this chapter's `status: beats_ready → drafted`.

### C-7 — Memory indexing

- **`memory/summaries.json`** — add a new `chapter_summaries` entry (logline + synopsis +
  active_entities + tags). Update `volume_summaries` if the volume arc shifted.
- **`memory/plot_threads.json`** — for each open hook that appeared in this chapter, add a
  new occurrence entry. Update any hook that was resolved or newly introduced.

### C-8 — Ripple check (RIPPLE-02)

Compare the chapter's actual outcome against the future outline. If the hero lost his
left arm but Ch.55 plans a "two-handed sword technique", or an item was destroyed but
Ch.50 needs it to open a gate — flag the conflict with a severity and a suggested fix
(rewrite earlier chapter, or change the later plan). Delegate the deterministic scan to
**narrative-consistency** (`scripts/check_consistency.py`); use RIPPLE-02 for narrative
judgement on how to resolve each flag.

---

## Canonical KB write-order (Phase C)

The sequence below resolves all inter-file dependencies:

```
1.  characters/states/<id>.json       — state snapshots per affected character
2.  masks/<id>.json                   — knowledge updates per affected POV
3.  ontology.json                     — relations, events, threads, world_rules, current_chapter
4.  timeline/events.json + events/<thr>.json + events/index.json + threads.json
                                      — event-graph mirrors; regenerate via sync_events.py --write (projects ontology)
5.  timeline/calendar.json            — current_story_time/current_chapter + chapter_to_story_time (+ world_day/travel if changed); via sync_kb.py --write
6.  world/world_bible.json            — improvised lore writeback
7.  outline/structure.json            — chapter status advance
8.  memory/summaries.json             — chapter + volume summaries
9.  memory/plot_threads.json          — hook occurrences + status updates
10. [ripple check]                    — narrative-consistency scan
```

---

## The execution loop (full pipeline)

```
outline/beats/<ch>.json (architect output)
      │
      │  ── DESIGN GATE: checklist complete? if not → return to architect
      ▼
PHASE B — WRITE
      │
      ▼  ── B-1: assemble context (Graph-RAG + REL-01 pre-check)
      ▼  ── B-2: apply Fog of War mask (WRITE-01a)
      ▼  ── B-3: draft prose beat-by-beat (WRITE-01b)
      │         if beat deviation required → stop → return to architect
      ▼
chapters/<ch>.md  →  author reviews / edits
      │
      │  ── WRITE GATE: prose accepted as final? if not → revise prose
      ▼
PHASE C — KB UPDATE
      │
      ▼  ── C-1: character states
      ▼  ── C-2: knowledge masks
      ▼  ── C-3: ontology (relations, events, threads, world_rules, current_chapter)
      ▼  ── C-4: dynamic lore writeback (LORE-01)
      ▼  ── C-5: timeline mirrors
      ▼  ── C-6: outline status
      ▼  ── C-7: memory indexing
      ▼  ── C-8: ripple check (RIPPLE-02)
      │
      ▼
KB UPDATE GATE: all checklist items complete?
      │  if conflicts → flag → return to architect for plan adjustment (Phase D)
      ▼
hand to narrative-memory (Phase IV summary + index)
```

---

## State extractor rules (DB-01) — the core of Phase C

Read the finalised prose and emit JSON deltas. This is the most error-prone operation;
follow these rules precisely and anchor on the test suite.

**Extract four kinds of change:**

1. **Inventory** — gained/lost/modified items → `inventory_delta` in the state snapshot.
2. **Status** — injury / buff / debuff / rank_up / recovery / cleansing / psychology →
   `status` array in the snapshot.
3. **Knowledge** — facts the character learned → `knowledge_gained` in snapshot +
   `masks/<id>.json` update.
4. **Relations** — trust/hate/romance shifts → relation edges in `ontology.json`.

**Critical extraction traps** (full cases in `references/extraction_tests.md`):

- **Metaphor vs. literal.** "a knife pierced his heart" = psychology change, NOT injury.
  Ignore physical words used figuratively.
- **Observation vs. acquisition.** "saw the sword" = no inventory change; "grabbed the
  sword" = add. Window-shopping does not change inventory.
- **Relationship flips.** Friend → enemy: terminate old edge (`valid_to_chapter = N`),
  create NEW edge (`valid_from_chapter = N`). Never mutate old edge predicate.
- **Compound changes.** A breakthrough (rank_up) often also clears injuries (recovery) —
  emit both.

Before emitting, think step by step: did the character actually touch and keep the item,
or just see it?

---

## Writing-as-transaction data flow

| Data | Lives in | Phase B reads | Phase C writes |
|---|---|:---:|:---:|
| World rules / lore | `world/` + `ontology.json.world_rules` | ✓ (pre-check) | ✓ (LORE-01) |
| Entity nodes + state | `ontology.json.entities` + `characters/states/` | ✓ (Graph-RAG) | ✓ (DB-01) |
| Relationship edges | `ontology.json.relations` | ✓ (Graph-RAG) | ✓ (DB-01) |
| Event graph | `ontology.json.events[]` + `timeline/events/<thr>.json` + `index.json` | ✓ (scoped: POV shard + index) | ✓ planned→drafted; shard+index sync |
| Narrative threads | `ontology.json.threads[]` + `timeline/threads.json` | ✓ (convergence) | ✓ append event_ids + current_time |
| Calendar / story-clock | `timeline/calendar.json` | ✓ (current time + travel) | ✓ current_*/chapter_to_story_time every chapter |
| Chapter cursor | `ontology.json.source.current_chapter` | — | ✓ advance |
| Knowledge masks | `masks/` | ✓ (Fog of War) | ✓ fact revealed |
| Prose | `chapters/` | — | ✓ (Phase B only) |

---

## Phase B output checklist

- [ ] Context-window discipline (CTX-01): drafted from the chapter-scoped working set
      (beats + POV/on-scene profiles + recent-summary tail + targeted threads), expanding
      to other KB only on demand. Full manuscript NOT loaded.
- [ ] Prose-density floor (LEN-01): draft meets the language floor (≥ 1,500 字 / ≥ 1,000
      words) and fully realizes every beat with scene grounding, full dialogue, and
      interiority — not a synopsis. Verified with `wc -m` / `wc -w`.
- [ ] `chapters/<chapter_id>.md` — the finalised, author-approved prose.
  *(This is the only file Phase B writes.)*

## Phase C output checklist (per chapter)

- [ ] `characters/states/<id>.json` — new snapshot per affected character.
- [ ] `masks/<id>.json` — updated for each fact revealed this chapter; projected entries
      confirmed or corrected.
- [ ] `ontology.json.relations[]` — old edges terminated, new edges created.
- [ ] `ontology.json.events[]` — status advanced `planned→drafted`; projected_outcome
      corrected; improvised events added.
- [ ] `timeline/events/<thr>.json` + `timeline/events/index.json` — touched thread shard(s)
      appended; index updated (by_chapter / by_story_time / by_thread + last_*).
- [ ] `ontology.json.threads[]` + `timeline/threads.json` — event IDs appended; new
      convergences recorded; `current_time` advanced; mirror synced.
- [ ] `timeline/calendar.json` — `current_story_time` + `current_chapter` advanced;
      `chapter_to_story_time` entry added; `world_day`/`travel_rules` updated if the prose
      moved the date or a character's location. (NOT left frozen.)
- [ ] `ontology.json.world_rules[]` — new lore-rules added (LORE-01).
- [ ] `ontology.json.source.current_chapter` — advanced to this chapter number.
- [ ] `world/world_bible.json` — improvised new lore entered.
- [ ] `outline/structure.json` — chapter status advanced to `drafted`.
- [ ] `memory/summaries.json` — new chapter entry; volume entry updated if arc shifted.
- [ ] `memory/plot_threads.json` — occurrences updated; resolved/new hooks filed.
- [ ] Ripple check (RIPPLE-02) run; conflicts flagged (or confirmed none).
- [ ] `sync_kb.py --write` run so the deterministic mirrors (cursor, calendar,
      outline status, summary skeletons) match the prose.
- [ ] `sync_events.py --write` run so the event graph is consistent (every referenced
      event declared in ontology, one-thread membership, timeline mirrors regenerated).
- [ ] **Both gates green:** `validate_narrative.py` passes with NO `[freshness]` errors
      (calendar/cursor/summaries/status keep pace) and NO `[events]` errors (no orphan
      refs, one-thread membership, mirror coverage). Do not commit a batch while red.

---

## Anti-patterns

- **Loading the whole manuscript/KB to write one chapter (CTX-01 violation).** Draft from
  the chapter-scoped working set; pull other records only on demand. Preloading "everything
  to be safe" causes drift, latency, and context exhaustion — the KB exists to prevent it.
- **Transcribing the beat sheet instead of dramatizing it (LEN-01 violation).** A few terse
  lines that merely state what happens is not a chapter. Under-floor drafts (< 1,500 字 /
  < 1,000 words) are rejected at the WRITE GATE. Realize every beat with scene texture,
  full dialogue, and interiority.
- **Starting Phase C before prose is final.** KB updates mid-edit cause state snapshots
  that reference deleted or rewritten beats. Wait for author sign-off.
- **Writing KB files in Phase B.** The write gate exists for a reason — if prose-in-
  progress updates the mask, a mid-draft edit can create a mask that never matches the
  final prose.
- **God-view leaks in Phase B.** Never write from the global truth — always pass through
  the POV character's knowledge mask. The most common consistency failure.
- **Mutating temporal edges in place.** Always terminate + create; never edit predicates.
- **Rewriting state history.** Snapshots are append-only. Add a new snapshot; don't edit
  the old one.
- **Skipping the ripple check.** Run `check_consistency.py` before declaring a chapter
  final. Cheap, deterministic, catches errors that compound expensively.
- **Un-tracked improvised lore.** Harvest new proper nouns into the KB (LORE-01)
  immediately, or continuity drifts.
- **Leaving the calendar frozen (C-5 violation).** `timeline/calendar.json` is
  state-bearing, not static — advance `current_story_time`/`current_chapter` and append the
  `chapter_to_story_time` entry every chapter. A calendar stuck at ch_001 silently breaks
  the time-of-story context the next chapter loads under CTX-01. **This is now enforced:**
  `sync_kb.py` regenerates it from canon and `validate_narrative.py` errors if it lags.
- **Truncating Phase C to "the files I remember" (the drift trap).** Updating only
  states/masks/ontology and skipping the calendar + memory mirrors is how a KB silently
  rots — it passes the *old* structural validator while the timeline and summaries freeze
  chapters behind. Always finish with `sync_kb.py --write` + a green freshness gate.
- **Referencing an event that was never declared (the orphan trap).** Putting an event ID
  in a chapter's `events_covered` / `planned_events` without first creating it in
  `ontology.json#events` leaves a ghost: the beat/summary/structure points at nothing, no
  thread owns it, no timeline mirror lists it. **This is now enforced:** `sync_events.py`
  stubs the orphan and `validate_narrative.py` errors (`[events]`) until it is a real,
  single-thread, fully-mirrored ontology event. Declare events before you reference them.
- **Hand-editing the timeline event mirrors.** `timeline/events.json`, the
  `timeline/events/*.json` shards, and `index.json` are deterministic projections of
  `ontology.json#events` — edit the ontology, then run `sync_events.py --write`. Hand-edits
  drift from canon and get overwritten on the next sync anyway.
- **Inventing a status word.** Chapter status vocabulary is fixed: `planned → beats_ready →
  drafted → final` (`partially_drafted` for in-progress multi-chapter events). Do not coin
  synonyms like `written`; they pass nothing and the validator rejects them.
- **Loading the full event graph to write one chapter (CTX-01 violation).** Use the
  `timeline/events/index.json` + the POV thread shard; pull other shards only when a beat
  names a cross-thread event. Never read `ontology.json.events` in full just to draft.

---

## Reference files

- `references/execution_prompts.md` — WRITE-01a (Fog of War filter), WRITE-01b
  (state-driven writer), DB-01 (state/relationship extractor), LORE-01 (lore
  harvester), RIPPLE-02 (broken-link detector), with system roles + JSON contracts.
- `references/extraction_tests.md` — the five DB-01 unit tests (happy path, metaphor
  trap, window-shopping, transaction, level-up) with expected JSON. Use as few-shot
  examples and as a self-check.
