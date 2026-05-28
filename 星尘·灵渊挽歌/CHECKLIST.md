# 星尘·灵渊挽歌 — 工作清单 (Work Checklist)

> **Status (after D2–D6 + E):** 25 chapters drafted (prose `ch_001`–`ch_025`),
> beat sheets through `ch_025`, ontology `current_chapter: 25`. **43 events** total
> (33 from before + 10 new for ch_018–025). Beat sheets ch_022–025 newly designed.
> vol_03 Sub-arc A 'A·告别路口' complete. 25 chapter summaries + 3 volume summaries
> (vol_03 updated). Plot hooks updated through ch_025. Masks: 4 POV characters.
> Tier: `long_novel`. Next: Sub-arc B planning (F1).
>
> Workflow: event-driven NovelForge cycle. See `.claude/agents/novelist/AGENT.md`.

---

## A. KB hygiene — retrofit existing 17 chapters to the event-driven schema

- [x] **A1.** Migrated `chapter_id` (string) → `chapter_ids` (array) on all 29 existing
      events. Mapping aligned with the existing structure.json `planned_events`.
- [x] **A2.** Added `beat_design` (pov / technique / scene_arc / key_moment /
      pov_constraint) to **all 33 events** (not just the recent ones — full coverage).
- [x] **A3.** Added `events_covered` to all 21 beat sheets (ch_001–ch_021), keyed off
      the ontology mapping.
- [x] **A4.** Promoted `vol_02` (ch_009–014, status `drafted`) and `vol_03` (ch_015–017,
      status `in_progress`) from `volumes_upcoming[]` into the canonical `volumes[]`.
      `vol_01` status set to `drafted`. `volumes_upcoming` is now empty.

## B. Memory & summary coverage

- [x] **B1.** Promoted ch_015–017 chapter summaries from `vol_03_drafting` staging block
      into the canonical `chapter_summaries[]` (17 entries total). Removed staging block.
- [x] **B2.** Added `vol_03 烬火向东` to `volume_summaries[]` (now: vol_01, vol_02, vol_03).
- [x] **B3.** Audited all 9 hooks in `memory/plot_threads.json` for ch_015–017 coverage;
      added the 4 missing occurrences (hook_shou_yan_memory_keeper@ch_015+017,
      hook_shou_yan_erosion@ch_017, hook_zhao_tactical_lead@ch_017,
      hook_lingyin_active_ability@ch_017). Marked `hook_huipo_vein_pact` as dormant
      post-灰珀 with a status_note.

## C. Mask & state coverage

- [x] **C1.** Created `masks/char_ling_yin.json` with 4 story_time entries (1, 14, 15, 16)
      covering her arc from baseline → frequency-exposed → sub-band testing.
- [x] **C2.** Created `masks/char_shou_yan.json` with 5 story_time entries
      (1, 11, 14, 15, 17) covering 戍长 → 活档案 → memory_keeper → 看见者 arc.
- [x] **C3.** Documented `char_wei_se`'s null-state design: created
      `characters/states/char_wei_se.json` with a single baseline anchor that explicitly
      says she has no runtime state (空壳 from pre-story; 余烬 lives in `elem_wei_se_core`).
      Cross-references `hook_wei_se_ember` for her appearances.

## D. Continue Sub-arc A (A·告别路口, ch_018–025) — per-event cycle

- [x] **D1.** Added 4 new events to ontology with full `beat_design` + `chapter_ids` +
      `dependencies`:
      - `evt_team_rhythm` (ch_018, thr_garrison) — 40分钟窗口成为队伍默认节律
      - `evt_lingyin_subband_test` (ch_018+ch_019, thr_hive, **multi-chapter via parallel
        technique**) — 聆音子频段a'假设与验证
      - `evt_zhao_asks_target` (ch_020, thr_garrison) — 昭从方向问到目标
      - `evt_yilan_first_half_confession` (ch_021, thr_yi_lan) — 伊岚第一次半开口
      Each thread's `event_ids` was updated. Existing ch_018–021 beat sheets already
      carry the matching `events_covered` (from A3).
- [x] **D2.** Write prose `chapters/ch_018.md` → then Phase C KB update.
- [x] **D3.** Write prose `chapters/ch_019.md` (Ling Yin POV) → then Phase C KB update.
- [x] **D4.** Write prose `chapters/ch_020.md` → then Phase C KB update.
- [x] **D5.** Write prose `chapters/ch_021.md` → then Phase C KB update.
- [x] **D6.** Design + write `ch_022`–`ch_025` to close Sub-arc A — including the
      foreshadowed payoff at **ch_024** (伊岚完整说出方向的真相; foreshadowed by
      ch_020/ch_021 half-confessions and ch_019's parallel structure).
      Beat sheets ch_022–025 created. Prose drafted. KB updated: summaries, plot_threads,
      structure.json (ch_018–025), timeline/events.json (10 new events).

## E. Validation & profiles

- [x] **E1.** Run `narrative-ontology/scripts/validate_narrative.py` and resolve flags.
      Result: 0 errors, 2 pre-existing warnings (invalid relation type names in old events).
      Fixed: added `elem_huipo_wasteland_east` entity; fixed location string in
      `evt_zhao_discovers_arrow_carving`.
- [x] **E2.** Run `narrative-consistency/scripts/check_consistency.py` (ripple/paradox)
      and resolve flags. Result: ✓ no consistency violations found.
- [x] **E3.** Generate chapter-masked profiles into `chapters/profiles/` beyond `ch_001`.
      Generated ch_002–ch_025 (24 profiles). ch_025 is ~9031 tokens, 16 active entities.

## F. Long-horizon (vol_03 sub-arcs B/C/D — plan when Sub-arc A is done)

- [ ] **F1.** Sub-arc B 东行深荒 (ch_026–050) — brief event sketch.
- [ ] **F2.** Sub-arc C 信标渐近 (ch_051–070) — brief event sketch.
- [ ] **F3.** Sub-arc D 烬火 (ch_071–090+) — brief event sketch; verify 80-ch/vol floor.
