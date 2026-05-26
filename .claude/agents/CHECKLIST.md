# Agents — progress checklist

A single place to track the state of the agent layer. Update this file as
work lands. Status vocabulary matches `skills/share/scenario-checklist/`:

- **shipped** — defined, all dependent skills exist, scenario in SCENARIOS.md.
- **draft** — AGENT.md exists but is partially specified or under review.
- **stub** — AGENT.md exists as a placeholder with frontmatter + intent only.
- **missing** — referenced but not yet created.

For dependent skills, status uses the same vocabulary plus `proposed` (a
named gap with no skill folder yet).

---

## Per-agent status

### 1. novelist — Long-form fiction (NovelForge)

- [x] `agents/novelist/AGENT.md` — **shipped**
- [x] Reference files for the agent — **shipped** (`references/workflow.md`, `references/kb_layout.md`)
- [x] kb-ontology series wired in: `ontology-qa`, `ontology-extraction`, `ontology-merging`, `ontology-storage`, `book-to-knowledge-graph`, `book-chunking`, `memory-ontology`, `cognitive-alignment`
- [x] **Narrative skill series (NovelForge four phases + foundation + guard + toolkit + locale) — all 8 fleshed out:**
  - [x] `narrative-ontology` — foundation: temporal-graph schema (entity/relation/event/theme core + temporal validity / state / mask / thread layers), KB layout, `init_kb.py` scaffold, `validate_narrative.py` structural validator — **shipped**
  - [x] `narrative-genesis` — Phase I: World Bible + ontology-triple world rules + character profiles + T=0 states + initial social graph + initial knowledge masks — **shipped**
  - [x] `narrative-architect` — Phase II: multi-thread event graph (swimlanes) + write-ahead Novel→Volume→Chapter outline + beat sheets + travel-time/paradox validation — **shipped**
  - [x] `narrative-execution` — Phase III: masked-context drafting → author edit → reverse state-delta extraction → lore-back write → ripple check — **shipped**
  - [x] `narrative-memory` — Phase IV: hierarchical summary index + hybrid (graph / semantic / summary) query routing + as-of-chapter queries + plot-thread / open-loop tracker — **shipped**
  - [x] `narrative-consistency` — cross-cutting logic police: world-rule triples + state paradoxes + knowledge violations + butterfly/ripple analysis; deterministic `check_consistency.py` — **shipped**
  - [x] `narrative-toolkit` — runnable CLI tools: `view_kb.py` (timeline/character/event/snapshot views), `build_profile.py` (chapter-masked memory snapshot), `search_novel.py` (KB-first → KAG retrieval, CJK-aware tokenizer) — **shipped**
  - [x] `narrative-locale` — language/locale layer; flagship Chinese 中文 web fiction (玄幻/仙侠/武侠/系统/穿越/重生, 境界 ladder, naming systems, 网文 serial structure, 黄金三章 + 爽点 cadence, 百万字 budgeting); bilingual KB rule (ASCII IDs + English predicates, in-language `canonical_name`/prose); `references/zh_prompts.md` — **shipped**
- [ ] Scenario in `SCENARIOS.md` — *not present in this install* (SCENARIOS.md is a framework-root file; not shipped in this flattened `agents/` + `skills/` snapshot). Live routing instead via `skill-orchestrator/references/workflow-patterns.md` (Shape 5 single-agent entry).

## Summary counts

| Group | Total | Shipped | Stub | Missing |
|---|---|---|---|---|
| Agents | 1 | 1 | 0 | 0 |

