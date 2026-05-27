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

## C. KB data cleanup (pre-existing validator findings — surfaced, not yet fixed)

- [ ] **Event `location` as free-text (21 of 45 events).** Locations like
      `碎晶星域·维格拉斯北部高地·灵能族废弃前哨站` are strings, not declared `elem_` entities,
      so `validate_narrative.py` errors on them. Decide policy: (a) declare the recurring
      places as `elem_` location entities and reference by ID, or (b) relax the validator to
      allow free-text locations (warn, not error). Then apply across all events.
- [ ] **Duplicate `story_time` snapshots.** `char_aeon` (t=21 ×2 from ch_041+ch_042; t=12 ×2)
      and `char_liang` (t=12 ×2) trip the validator's duplicate check. Decide policy: allow
      multiple snapshots per story_time (two chapters can share a clock value) → relax the
      validator; or merge/relabel. Likely the validator should allow it (it's legitimate).
- [ ] After deciding, get `validate_narrative.py` to a clean PASS (or all-warnings) state so
      the Phase-C validation gate is meaningful again.

## D. Optional polish

- [ ] Backfill `timeline/calendar.json.chapter_to_world_day` for chapters where the in-world
      date/elapsed time matters (only `ch_001` has a detailed world-day string today; the
      rest now have accurate `chapter_to_story_time`).
- [ ] Consider a tiny `narrative-toolkit` helper / `view_kb.py --calendar` to print the
      story-clock window, now that the calendar carries `current_*` pointers.
- [ ] When vol_01 closes: volume-summary update in `memory/summaries.json` and a vol-level
      ripple/consistency pass before opening vol_02.

---

### Done this session (for reference)
- CTX-01 context-window discipline + LEN-01 prose floor added to skills/agent + all refs.
- Timeline event mirror sharded by thread (`timeline/events/` + `index.json`); toolkit
  scoped readers added; calendar made a per-chapter Phase-C write target (bug fix).
- Migrated live data: 45 events → 5 thread shards; calendar rebuilt (44 chapters mapped).
- Fixed `validate_narrative.py` crash on string-form event dependencies.
