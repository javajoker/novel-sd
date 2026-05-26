# NovelForge workflow map + prompt catalog

The conductor's quick reference. Each phase is a skill; each operation is a prompt ID.

## Four-phase cycle

```
            ┌─────────────────────────── feedback loop ───────────────────────────┐
            ▼                                                                       │
  ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
  │ I. GENESIS        │──▶│ II. CHRONICLE     │──▶│ III. EXECUTION    │──▶│ IV. MEMORY        │
  │ narrative-genesis │   │ narrative-architect│  │ narrative-execution│  │ narrative-memory  │
  │ world + T=0 state │   │ threads + outline │   │ mask → write →    │   │ summaries + query │
  │                   │   │ + beats           │   │ extract → ripple  │   │ + plot threads    │
  └───────────────────┘   └───────────────────┘   └───────────────────┘   └───────────────────┘
            ▲                       ▲                       ▲                       ▲
            └───────────────────────┴───────────────────────┴───────────────────────┘
                         narrative-consistency  (cross-cutting logic police)
                         narrative-ontology      (shared data model + validator)
```

## Prompt-ID catalog

| ID | Name | Phase / skill | Function |
|---|---|---|---|
| GEN-01 | Socratic Muse | I / genesis | brainstorm a fuzzy idea via one-question-at-a-time interview |
| GEN-02 | World Structurer | I / genesis | concept → World Bible JSON + ontology triples |
| GEN-03 | Lore Conflict Guard | I / genesis (+consistency) | check new lore vs. existing rules |
| CHAR-01 | Profiler + State Engine | I / genesis | deep profile (Ghost + Lie) + frozen T=0 state + social graph |
| PLOT-01 | Event-block planner | II / architect | rough outline → causal event graph (PRECEDES/CAUSES/ENABLES) |
| PLOT-02 | Beat expander | II / architect | event block → beat sheet with emotional arc |
| LOGIC-01 | Paradox guard | II / architect (+consistency) | travel-time + location/status/item paradoxes |
| POV-01 | POV selector | II / architect | pick the POV that maximises effect |
| RIPPLE-01 | Timeline shifter | II / architect (+consistency) | propagate a plan-edit delay forward |
| WRITE-01a | Fog of War filter | III / execution | mask global truth to the POV's knowledge |
| WRITE-01b | State-driven writer | III / execution | draft prose using inventory + psychology |
| DB-01 | State extractor | III / execution | **core:** prose → inventory/status/knowledge/relation deltas |
| LORE-01 | Lore harvester | III / execution | capture improvised new lore back into the KB |
| RIPPLE-02 | Broken-link detector | III / execution (+consistency) | actual outcome vs. future outline |
| MEM-01 | Hierarchical summarizer | IV / memory | chapter → structured summary record |
| MEM-02 | Hybrid search router | IV / memory | question → graph / vector / summary retrieval |
| MEM-03 | Evidence synthesizer | IV / memory | retrieved fragments → cited answer |
| MEM-04 | Open-loop detector | IV / memory | track unresolved foreshadowing |
| REL-01 | Ontology guardian | guard / consistency | world-rule (relationship) validation |
| LOGIC-02 | Ripple manager | guard / consistency | butterfly-effect resolution across chapters |

## Per-phase data flow

| Data | Storage | Read when | Written when |
|---|---|---|---|
| World rules / lore | `world/` + `ontology.json.world_rules` | always (pre-check) | I genesis / III improvised lore |
| Entity nodes + state | `ontology.json.entities` + `characters/states/` | pre-write Graph-RAG | III extract |
| Relationship edges (temporal) | `ontology.json.relations` | pre-write Graph-RAG | I (T=0) / III extract |
| Knowledge masks | `masks/` | pre-write (fog of war) | I (T=0) / III reveal |
| Event graph + threads | `ontology.json` + `timeline/` | II planning / IV causal query | II plan / III update |
| Outline + beats | `outline/` | III drafting | II plan |
| Prose | `chapters/` | IV indexing | III draft + edit |
| Summaries + plot threads | `memory/` | IV query / II payoff scheduling | IV index |

## Validation gates

- After **any** edit: `narrative-ontology/scripts/validate_narrative.py <slug>/` (structure + cross-refs).
- Before a chapter is **final**: `narrative-consistency/scripts/check_consistency.py <slug>/` (continuity).
- Use `--as-of N` to evaluate the world only up to chapter N (e.g. when validating a chapter mid-novel).
