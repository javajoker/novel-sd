---
name: narrative-consistency
description: The cross-cutting consistency guard for the NovelForge novel-writing workflow — the "logic police" that every phase calls to catch continuity errors before they compound. Use this skill to validate a narrative-ontology knowledge base against world-rule ontology triples (a Water-element mage can't learn fire; a Sword-Sect disciple can't use forbidden Blood Magic), detect state paradoxes (a character in two places at one story-time, acting while comatose, or using an item they don't possess yet), check knowledge violations (a POV acting on a fact their mask says they don't know), and run the butterfly/ripple analysis (an item destroyed or a limb lost in one chapter that a future outlined chapter still depends on). Ships a deterministic checker script plus the rule-judgement prompts. Read narrative-ontology first; this skill operates over that KB layout.
---

# Narrative Consistency (cross-cutting guard)

> *The logic police. Used by every phase — genesis (lore conflicts), architect
> (paradox / ripple-on-edit), execution (ontology pre-check, post-write ripple),
> memory (contradiction flags) all delegate the heavy checking here.*

Two layers:

1. **Deterministic checks** — `scripts/check_consistency.py` runs over the KB and finds
   the mechanical violations (location/time, possession, knowledge, dangling future
   deps) without an LLM. Run it after any batch of edits and before declaring a chapter
   final. Fast, reproducible, no false-creativity flags.
2. **Rule judgement** — `references/consistency_prompts.md` (REL-01, LOGIC-01,
   LOGIC-02) for the cases that need narrative reasoning: is this a world-rule
   *violation* or a sanctioned *exception*? How should a detected ripple be resolved?

**Read `narrative-ontology/SKILL.md` first.** This skill assumes that KB layout.

**Language:** the deterministic checker is language-agnostic (it compares IDs and ASCII
predicates, which never localize). For non-English novels, world-rule `note`s and the
human-facing flagged-issue text are written in the project language; rule *relations*
(`FORBIDS`, `RANKS_HIGHER_THAN`) stay ASCII. See **narrative-locale** — e.g. enforce the
境界 realm ladder via `RANKS_HIGHER_THAN` triples.

## The four violation classes

| Class | What it catches | Layer |
|---|---|---|
| **Ontology / world-rule** (REL-01) | Abilities or relations that contradict `world_rules` triples — fire mage learning water, disciple using a forbidden art. | rule judgement (+ partial deterministic) |
| **State paradox** (LOGIC-01) | Character in two places at one `story_time`; acting while `status: coma/death`; an event `prerequisite` (possession/location) unmet as of that time. | deterministic |
| **Knowledge violation** | A POV character acting on a fact their `masks/<id>.json` marks `facts_unknown` at that story_time (god-view leak). | deterministic |
| **Ripple / butterfly** (LOGIC-02) | Something consumed/lost/destroyed (or a status like a lost limb) that a *future* outlined chapter or event still requires. | deterministic detect + rule judgement to resolve |

## Running the deterministic checker

```bash
python scripts/check_consistency.py <novel-slug>/
```

It reads `ontology.json`, `characters/states/*.json`, `masks/*.json`,
`timeline/calendar.json`, and `outline/structure.json`, then reports violations grouped
by class with severity. Options:

- `--as-of N` — evaluate the world state only up to story_time N (default: all).
- `--class paradox|possession|knowledge|ripple` — run one class.
- `--json` — machine-readable output (for wiring into execution's post-write step).

Exit code 0 = clean, 1 = violations found, 2 = usage error. It is conservative: it
flags *candidates* and explains the evidence; a human (or the rule-judgement prompts)
decides whether each is a real bug or an intended twist.

## How each phase uses this skill

- **Genesis** → before saving new lore, REL-01 (lore conflict guard) checks the
  proposed setting against `world_rules`.
- **Architect** → after planning, LOGIC-01 paradox/travel-time validation; on a plan
  edit, the ripple analysis projects the delay downstream.
- **Execution** → before writing, REL-01 pre-check warns if a beat breaks a rule;
  after writing, the deterministic checker + LOGIC-02 ripple compare the actual outcome
  against the future outline.
- **Memory** → MEM-03 surfaces contradictions the checker found across chapters.

## What "violation" means here

A violation is a place where the **stored state** and the **narrative** disagree:

- The graph says Ye Fan owns the Iron Sword (no `lost`/`destroyed` edge before Ch.45),
  but Ch.45's prose has him sword-less — fix the graph or the prose.
- A future chapter's `planned_events` require an item whose latest state delta is
  `remove` — the payoff is now impossible; rewrite one side.
- A POV scene references a fact the character's mask says they don't know yet — either
  the mask is stale (add the reveal) or the scene is a god-view leak.

The checker never *fixes* anything — it reports. Resolution is an author decision,
optionally guided by the rule-judgement prompts.

## Reference files

- `scripts/check_consistency.py` — the deterministic KB checker (paradox, possession,
  knowledge, ripple).
- `references/consistency_prompts.md` — REL-01 (ontology/relationship validator),
  LOGIC-01 (paradox guard), LOGIC-02 (ripple manager), with system roles and the
  resolve-this-flag decision shape.
