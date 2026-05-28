# 星尘·诸族之战 — 工作清单 (Work Checklist)

> **Status (after Phase II build):** Phase I + Phase II complete. World Bible + 27 entities
> + 16 world rules; 6 character profiles + 6 T=0 states; 2 POV masks (柯炎 + 虚影);
> 18 events with `beat_design` mapped to vol_01 chapters; 3 threads populated with
> event_ids + convergences; outline structure with vol_01 (planned, 19 anchored ch over
> 80-ch span, 4 sub-arcs) + 3 upcoming volumes sketched; 10 plot hooks seeded; calendar
> with siege-day mapping + travel rules + movement speeds; 黄金三章 beat sheets
> (ch_001–003) synthesized and write-ready.
>
> Tier: `long_novel`, `target_word_count: 1,200,000`. `current_chapter: 0`.
>
> Workflow: event-driven NovelForge cycle. See `.claude/agents/novelist/AGENT.md`.
> This novel is the source game/fandom for 星尘·灵渊挽歌.

---

## Pre-flight — reconcile config

- [x] **P1.** Reconcile `ontology.json.source` — kept tier `long_novel`, raised
      target_word_count to 1,200,000 (matches web-serial scale; user chose this scope).
- [x] **P2.** Set the `logline` in both `ontology.json.source` and `outline/structure.json`;
      added `pov_roster: [char_ke_yan, char_void_echo]` + `omniscient_thread: thr_war_strategy`.

## Phase I — finish Genesis

- [x] **G1.** Wrote `characters/char_swarm_herald.json` (异种先驱) and
      `characters/char_psi_elder.json` (艾薇儿).
- [x] **G2.** Created T=0 anchor state snapshots in `characters/states/` for all 6
      main characters (柯炎, 刘霜, 周恒, 虚影, 异种先驱, 艾薇儿).
- [x] **G3.** Created initial knowledge masks for the 2 POV characters:
      `masks/char_ke_yan.json` + `masks/char_void_echo.json`, with `facts_known` /
      `facts_unknown` / `beliefs_held` / `projected_facts_to_learn` / `perception`.

## Phase II — Architect (timeline first, brief)

- [x] **A1.** Built 18-event causal graph in `ontology.json.events[]` with `beat_design`
      sub-objects, dependencies (PRECEDES/CAUSES/ENABLES), `chapter_ids`,
      `projected_outcome`, `status: planned`. Covers the full vol_01 80-ch arc.
- [x] **A2.** Populated all 3 threads with `event_ids` + `convergences`
      (thr_protagonist × thr_void_echo @ ch_050; thr_protagonist × thr_war_strategy @ ch_058
      and @ ch_070; symmetric record on thr_void_echo).
- [x] **A3.** Built `outline/structure.json`: vol_01 「第四十三日」 status `planned`,
      4 sub-arcs (围困/裂痕/暗影/突围), 19 anchored chapter entries with
      `planned_events`/`pov_character`/`story_time`, plus 3 sketched upcoming volumes
      (源质之心/诸族/原点).
- [x] **A4.** Seeded 10 hooks in `memory/plot_threads.json` covering every open mystery:
      keyan_potential, void_echo_identity, theta_secret, herald_evolving, liushuang_secret,
      zhou_despair_directive, federation_losing, psi_elder_mission, an_yuan_plan,
      keyan_parents_death.
- [x] **A5.** Filled `timeline/calendar.json` with siege-day clock, 19 chapter→day
      mappings, 5 travel rules between key locations, 7 movement-speed entries.
- [x] **Mirrors.** Synced `timeline/events.json` and `timeline/threads.json` with thin
      stubs referencing the ontology.
- [x] **黄金三章.** Synthesized `outline/beats/ch_001.json`, `ch_002.json`, `ch_003.json`
      from event beat_designs — write-ready (each with 4 beats, foreshadowing,
      projected_masks, ripple_risk, world_rule_checks, lore_improvised).

## Phase III — Write (per-event A→B→C cycle) — NEXT

- [ ] **W1.** Write prose `chapters/ch_001.md` from the synthesized beat sheet (黄金三章
      opening). Then Phase C KB update.
- [ ] **W2.** Write `chapters/ch_002.md`. Phase C KB update.
- [ ] **W3.** Write `chapters/ch_003.md` (爽点：第一张蓝卡). Phase C KB update.
- [ ] **W4+.** Continue chapter-by-chapter via the per-event design→write→update→adjust
      loop. Next events to synthesize beat sheets for: ch_005 (evt_liushuang_anomaly),
      ch_006 (evt_void_echo_observes — first POV switch to 虚影), ch_008, ch_010, ch_012,
      ch_015, ch_019–020 (sub-arc A climax). Then sub-arcs B/C/D, and the un-anchored
      chapters (61 of 80) defined per-event as the timeline grows.

## Validation

- [ ] **V1.** Run `narrative-ontology/scripts/validate_narrative.py`.
- [ ] **V2.** Run `narrative-consistency/scripts/check_consistency.py`.
