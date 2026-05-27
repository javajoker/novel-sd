# 星尘·孤鸣 — Outstanding Work Checklist

Tracking items deferred for later. Pick any item and ask me to do it; each has enough
context to start cold. Current state: **44 chapters drafted (vol_01), KB through ch_044.**

---

## A. Novel content — finish vol_01 (highest-level goal)

- [ ] **Reach the 80-chapter floor for vol_01** — currently at 44, need **36 more**
      (ch_045 → ch_080). `long_novel` tier = 80 ch/vol hard floor.
- [ ] Each new chapter runs the full A-B-C-D cycle (beat sheet → prose → KB update → commit),
      one commit per chapter, under the new rules:
  - **CTX-01**: draft from the chapter-scoped working set (beats + masked POV profile +
    last 1–3 summaries + targeted hooks + calendar window + POV event-thread shard). Do not
    load the full manuscript / full event graph.
  - **LEN-01**: each chapter ≥ 1,500 字 (target 2,000–3,000; major events 3,000–5,000+),
    fully realized — not a beat transcription.
  - **Phase C**: now also update `timeline/calendar.json` (current_*/chapter_to_story_time)
    and the sharded `timeline/events/<thr>.json` + `index.json` every chapter.
- [ ] Next planned chapters (from prior planning notes — confirm/adjust at design time):
  - ch_045 `源质歌` (thr_aeon, t≈23) · ch_046 `记录（一）` (thr_theta) ·
    ch_047 `被感知` (thr_aeon) · ch_048 `虚空扩散` (thr_ulos) ·
    ch_049 `联邦总部（一）` (thr_chen_ming) · ch_050 `足够了` (thr_aeon) · …
- [ ] Keep the 5-thread POV cadence (~aeon 60% / ulos 15% / theta 10% / chen_ming 10% /
      qixing 5%).
- [ ] Create KB entries for every new character who appears (mandatory char-coverage rule),
      main or supporting.

## B. Chapter-length remediation (LEN-01 back-fill)

- [ ] **ch_042 `断频器` is below the floor (1,292 字).** Expand with fuller scene
      realization (grounding, dialogue, interiority) to ≥ 1,500 字; re-run Phase C if any
      state/extraction changes. (User chose "leave for now" earlier — revisit when ready.)
- [ ] Optional: spot-check ch_041/043/044 for sparse realization even though they clear the
      字 count (short lines / whitespace can inflate `wc -m`).

## C. KB data cleanup (pre-existing validator findings) — DONE

- [x] **Event `location` as free-text (21 events).** Chose option (a): declared 6 `elem_`
      location entities (`elem_psionic_outpost`, `elem_perception_network`,
      `elem_northern_front`, `elem_vigras_south`, `elem_void_outpost`, `elem_trijoint_node`),
      remapped all 21 events to entity IDs, preserved the original strings as entity aliases
      + per-event `location_detail`, and added `located_in → 碎晶星域` relations.
- [x] **Duplicate `story_time` snapshots.** Confirmed legitimate (two chapters can share a
      clock value; snapshots are stored newest-first and the toolkit sorts on load).
      Relaxed the validator: allow same/any-order story_time, require only that each snapshot
      *has* a story_time. Updated validator docstring + decision recorded here.
- [x] `validate_narrative.py` now a clean PASS (`✓ 星尘·孤鸣 valid`).
- [x] Bonus: fixed `view_kb.py --events` which crashed on the same string-form
      `dependencies` (mirrors the validator fix from the prior PR).

## D. Optional polish — DONE / one blocked

- [x] **`chapter_to_world_day` backfill — declined fabrication; documented instead.** The
      novel deliberately runs *parallel* clocks (世界年「第84X年」, 战争日「第3XX天」 Θ-7,
      七星个体日「第1XX天」, plus the internal `story_time`). Forcing them into one world-day
      map would conflate incompatible clocks and could mislead the paradox guard. Added an
      accurate `clocks` block to `timeline/calendar.json` (grounded in prose markers) and to
      the schema/init scaffold. `chapter_to_world_day` stays for a single canonical world-date
      only where one genuinely exists (currently ch_001).
- [x] **`view_kb.py --calendar`** added — prints the story-clock window (current time, world
      calendar, parallel clocks, recent chapter→story_time, travel rules, movement speeds).
      Also made `chapter_to_time` fall back to the calendar's `chapter_to_story_time` map.
- [ ] **BLOCKED — vol_01 not yet complete (44/80 chapters).** Volume-summary update in
      `memory/summaries.json` + a vol-level ripple/consistency pass belong at vol close;
      cannot run meaningfully until vol_01 reaches its 80-chapter floor (see section A).

---

### Done this session (for reference)
- CTX-01 context-window discipline + LEN-01 prose floor added to skills/agent + all refs.
- Timeline event mirror sharded by thread (`timeline/events/` + `index.json`); toolkit
  scoped readers added; calendar made a per-chapter Phase-C write target (bug fix).
- Migrated live data: 45 events → 5 thread shards; calendar rebuilt (44 chapters mapped).
- Fixed `validate_narrative.py` crash on string-form event dependencies.
