---
name: narrative-architect
description: Phase II (Chronicle) of the NovelForge novel-writing workflow — builds the causal event graph (timeline) as the primary artifact, derives a brief per-event beat design, and synthesizes chapter beat sheets just-in-time. Timeline is the planning unit; chapters are output containers. Works one event at a time. Run after narrative-genesis; read narrative-ontology first.
---

# Narrative Architect (Phase II)

> Timeline first. Beat designs follow events. Chapters are output containers.
> Work **ONE EVENT AT A TIME** — define it in the timeline, write a brief beat design,
> assign to chapter(s), project masks, hand off to execution. Repeat.
> *Goal: handle multi-POV and time synchronisation, and resolve "time paradoxes",
> by planning the story as a causal event graph on parallel threads — and laying down
> the outline the writer will follow.*

This is the second NovelForge phase. It plans **forward** from a causal event graph, not
from a chapter list. Chapters are assigned after events are defined — never the other way
around. **Read `narrative-ontology/SKILL.md` first.** Run after narrative-genesis has
populated the world and characters.

**Language:** beat designs, scene arcs, and key-moment notes are written in the project
language. For Chinese: follow 黄金三章 opening, 爽点 cadence, 卷/章 sizing.
IDs/predicates stay ASCII.

**Volume sizing:** before setting any volume to `status: planned` in
`outline/structure.json`, verify its projected chapter count meets the floor for the
novel's length tier (read from `ontology.json.source.tier`):

| Tier | `source.tier` | Min chapters / vol |
|---|---|---|
| Short story | `short_story` | No volume structure needed |
| Novella | `novella` | 10 / vol |
| Novel | `novel` | 30 / vol |
| Long novel / web-serial | `long_novel` | **80 / vol (hard floor)** |

If a planned volume falls short, expand the event graph (add events / branches) or merge
into an adjacent volume. Flag to the author before proceeding.

---

## The two-layer plan

**Layer 1 — TIMELINE (what happens):** a brief causal event graph. Each event has an ID,
story_time, participants, causal dependencies, and a projected_outcome. The overall
timeline stays concise — one or two lines per event. New characters and sub-arcs are
added to the timeline when they emerge naturally from writing, not forced out in a single
up-front planning pass.

**Layer 2 — BEAT DESIGN (how it's narrated):** a brief director's note per event
specifying POV, narrative technique, scene arc, and the load-bearing key moment. Beat
design is **not** a 3–5 sub-beat breakdown — that level of texture belongs to the writer
in Phase B. Beat design is the minimal instruction execution needs to draft correctly.

Both layers live together: the `beat_design` sub-object sits inside the event entry in
`ontology.json.events[]`. Chapter beat sheets are synthesized from event beat designs;
they are a derived artifact, not a primary one.

---

## Event entry structure

```json
{
  "id": "evt_...",
  "story_time": 17,
  "duration": 1,
  "location": "...",
  "participants": ["char_..."],
  "thread_id": "thr_...",
  "dependencies": [
    { "event_id": "evt_...", "type": "PRECEDES|CAUSES|ENABLES" }
  ],
  "prerequisites": [],
  "projected_outcome": "...",
  "status": "planned|drafted|final",
  "chapter_ids": ["ch_N"],
  "beat_design": {
    "pov": "char_...",
    "technique": "direct|foreshadowing|reverse|parallel|ellipsis|multi_pov",
    "scene_arc": "...",
    "key_moment": "...",
    "pov_constraint": "..."
  }
}
```

**`chapter_ids`** — one event may span multiple chapters (e.g. a revelation foreshadowed
in ch_N, resolved in ch_N+3). One chapter may cover multiple events (list them all in
the beat sheet). Both are normal; neither is an exception.

> **A `beat_design` is a brief director's note, not a length budget.** It tells the writer
> *what* happens and *how* to frame it (technique, arc, key moment, POV limit) — the writer
> then fully realizes it as prose under narrative-execution's LEN-01 floor (≥ 1,500 字 /
> ≥ 1,000 words). Any optional tone cue you add (e.g. a `prose_notes`/`avoid` field, or a
> "短/克制" register note) governs **register and plot restraint, not word count** — a terse
> *tone* is a valid instruction; a skeletal *chapter* is not. Never write a beat design that
> can only be satisfied by an under-floor chapter.

**`technique` choices:**

| Technique | When to use |
|---|---|
| `direct` | Scene plays out in chronological order; event is the chapter's weight |
| `foreshadowing` | Plant the seed here; full meaning deferred to a later chapter |
| `reverse` | Outcome lands first (more impact); cause revealed as mystery payoff |
| `parallel` | Two events intercut in the same chapter to make a thematic mirror visible |
| `ellipsis` | Event happens off-page; only consequences are shown — the gap is the point |
| `multi_pov` | Same event needs two POVs in two different chapters; assign both chapter_ids |

---

## Chapter beat sheet synthesis (just-in-time)

`outline/beats/<ch>.json` is synthesized **just-in-time** from all events whose
`chapter_ids` include that chapter. It is a derived artifact — not authored independently.

**Synthesis steps:**
1. Collect all events where `chapter_ids` contains `<ch>`.
2. Order them by `story_time` (or by intended narrative sequence for non-chronological
   techniques).
3. For each event, build a beat entry from its `beat_design` fields; include the event's
   `projected_outcome` as psychology context.
4. Assign a primary `pov_character` for the chapter (may be overridden per beat for
   `multi_pov`).
5. Write `outline/beats/<ch>.json`. Include an `events_covered` array listing all event
   IDs that this chapter carries.

Because the beat sheet is derived, changing an event's `beat_design` propagates cleanly
on re-synthesis — no manual beat-sheet edits needed.

---

## Design gate (minimum viable, per event)

**Writing is unlocked per event — not per chapter batch.** Once the following items are
complete for an event, Phase B may begin for the chapter(s) that carry it:

- [ ] Event defined in `ontology.json.events[]` — full fields including `beat_design`.
- [ ] `chapter_ids` assigned; thread's `event_ids` updated.
- [ ] `outline/beats/<ch>.json` synthesized (or re-synthesized if the chapter already
      exists and is gaining a new event).
- [ ] `masks/<pov_id>.json` projected entry added — `projected_facts_to_learn` at this
      `story_time` for the POV character(s).
- [ ] Light paradox check: character is in the right location, holds required items,
      no timeline contradiction with earlier events.

Full architecture (multi-thread convergence maps, exhaustive travel-time validation,
complete new-lore taxonomy) is done as the timeline grows — it is **not** a prerequisite
before the first event is written.

---

## Per-event design pipeline

```
"what happens next" (rough plot point or author intent)
      │
      ▼  Step 0: read KB current state (always before adding anything)
      │
      ▼  Step 1: define event in timeline
      │    • Write into ontology.json.events[]: story_time, participants,
      │      dependencies (PRECEDES / CAUSES / ENABLES), projected_outcome,
      │      thread_id, status: planned
      │    • Assign chapter_ids. Append to thread.event_ids.
      │
      ▼  Step 2: write beat_design (brief director's note)
      │    • POV (POV-01): whose perspective maximises tension / dramatic irony?
      │    • technique: direct / foreshadowing / reverse / parallel /
      │                 ellipsis / multi_pov
      │    • scene_arc: short phrase (e.g. "silence → fracture → half-truth")
      │    • key_moment: one sentence — the load-bearing instant of the scene
      │    • pov_constraint: one sentence — what the POV does NOT know going in
      │
      ▼  Step 3: synthesize chapter beat sheet
      │    • Collect all events mapped to this chapter_id
      │    • Build outline/beats/<ch>.json with events_covered list
      │
      ▼  Step 4: mask projection
      │    • Add projected_facts_to_learn to masks/<pov_id>.json at this story_time
      │    • Mark as projected (execution confirms after prose is final)
      │
      ▼  Step 5: light paradox spot-check
      │    • Travel time feasible? Character state permits participation?
      │    • If paradox → surface to author, fix event, re-synthesize beat sheet
      │
      ▼
DESIGN GATE: all items above complete for this event's chapter(s)?
      │  YES → hand to Phase B (WRITE) for those chapters
      │  NO  → complete the checklist first; do not write
```

For a multi-event arc, run steps 1–5 per event sequentially. Do not batch-plan a whole
arc and then write — the workflow unit is the event.

---

## Step 0 — Read the KB before adding any event

| KB file | What to check | Why |
|---|---|---|
| `ontology.json` | events[], threads[], world_rules, current_chapter | Avoid contradictions; find dependency targets |
| `characters/states/<id>.json` | Latest snapshot ≤ story_time | Plan from their actual current state |
| `masks/<id>.json` | Current knowledge mask (all entries) | Plan reveals the POV can plausibly discover |
| `outline/structure.json` | Chapter status, volume arc | Which chapters are drafted vs. available to assign |
| `outline/beats/<ch>.json` | Events already mapped to target chapter | Don't duplicate or conflict with existing beat designs |
| `memory/plot_threads.json` | Open hooks | New events should service or plant open loops |
| `memory/summaries.json` | Last 1–3 chapter synopses | Continuity and tonal consistency |
| `world/world_bible.json` | Power system, geography, travel rules | Ability and location constraints |

Only after loading this context should any new event or beat design be written.

---

## New characters and sub-arcs

**Do not plan every character and sub-arc up front.** Add them to the KB when a chapter
needs them:

- **New character:** add to `ontology.json.entities[]`, create `characters/<id>.json`
  and `characters/states/<id>.json` at T=0, write their initial mask entry.
- **New sub-arc:** add a `sub_arc` tag to the relevant chapters in
  `outline/structure.json`. Add a new thread to `ontology.json.threads[]` if needed.
- **New lore:** add to `world/world_bible.json` when the plot event requires it.

The timeline stays brief. Sub-arc structure emerges from the causal event graph; it is
not imposed by a top-down plan before writing starts.

---

## Causal dependency types

- `PRECEDES` — chronological ordering.
- `CAUSES` — logical consequence (killing the king causes the succession crisis).
- `ENABLES` — precondition (gaining the heir's trust enables the betrayal reveal).

Build the graph as events are defined. For three or more events in sequence, delegate
deep paradox checking to **narrative-consistency** (`check_consistency.py`).

---

## Ripple-on-edit (RIPPLE-01)

When a past event is changed (story_time shifted, participants changed, projected_outcome
revised), propagate the change:
- Shift `story_time` on dependent events.
- Flag any fixed-time events that can no longer be met.
- Re-synthesize any chapter beat sheet that included the changed event.
- Re-project affected masks.

Delegate heavy diff scans to narrative-consistency. The architect's job is to resolve
narrative conflicts; consistency runs the deterministic check.

---

## Output checklist (per event = design gate)

- [ ] `ontology.json.events[]` — event defined with all fields including `beat_design`.
- [ ] `ontology.json.threads[]` — `event_ids` updated; new convergences noted if threads meet.
- [ ] `outline/beats/<ch>.json` — synthesized or re-synthesized for each affected chapter,
      with `events_covered` array.
- [ ] `masks/<pov_id>.json` — projected entry at this `story_time` with
      `projected_facts_to_learn`.
- [ ] Travel-time and state paradox spot-checked, or conflicts flagged to author.
- [ ] If new character introduced: `characters/<id>.json` + initial state + initial mask entry.
- [ ] If new lore required: `world/world_bible.json` + `ontology.json.entities[]` updated.
- [ ] If new plot hook planted: `memory/plot_threads.json` — new hook with seed chapter noted.

Hand to **narrative-execution Phase B** only when the above are complete for the
event's chapter(s).

---

## When to re-run the architect

- Prose in Phase B diverges from the beat design (ripple-on-edit).
- Phase C reveals a projected_outcome was wrong and breaks a future event.
- A new open hook needs a payoff event assigned.
- Author wants to plan ahead after completing a writing sprint.
- A character state after Phase C makes a planned event paradoxical.

On re-run: always Step 0 first. Then revise the affected event's `beat_design`,
re-synthesize chapter beat sheets, re-project masks. Do not re-plan events whose
chapters are already `status: drafted` unless a contradiction demands it.

---

## Reference files

- `references/architect_prompts.md` — PLOT-01 (event definition), PLOT-02 (beat design),
  LOGIC-01 (travel + paradox), POV-01 (POV selector), RIPPLE-01 (timeline shifter),
  with system roles and JSON contracts.
