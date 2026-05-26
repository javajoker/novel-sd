---
name: narrative-locale
description: The language and locale layer for NovelForge — makes the novelist agent and every narrative-* phase write in the project's language (with a fully-developed Chinese / 中文 web-novel pack) while keeping the knowledge-base structure language-independent. Use this skill whenever a novel is NOT written in English, or whenever you need genre conventions, naming systems, power/cultivation systems, or serial-structure pacing for a specific tradition. Flagship support is Chinese web fiction (网文) — 玄幻 / 仙侠 / 武侠 / 都市 / 系统 / 穿越 / 重生 genres, cultivation realms (境界), sect/technique/person naming, the 黄金三章 plus 爽点 serial structure, and 百万字 character-counting. Defines the bilingual KB rule (ASCII IDs plus English predicates, in-language canonical_name and prose) and ships in-language prompt variants. Read narrative-ontology first.
---

# Narrative Locale

The cross-cutting language layer. The four phases (genesis / architect / execution /
memory) own the *workflow*; this skill tells them **what language to write in and which
genre/naming/structure conventions to honour**. It is consulted, not run as a phase.
**Read `narrative-ontology/SKILL.md` first** — especially its "Language conventions"
(the bilingual rule).

Flagship locale: **Chinese (中文)**. The skill is structured so other languages drop in
the same way, but the worked content here is Chinese web fiction (网文), the request that
created this skill.

## The bilingual rule (non-negotiable)

The novel's *prose* is in `source.language`; the KB's *structure* stays ASCII so tools,
validation, and merges are language-independent:

| Stays ASCII | In the project language |
|---|---|
| entity / event / thread / fact **IDs** (`char_ye_fan`) | `canonical_name` (`叶凡`) |
| relation **predicates** (`hates`, `member_of`, `PRECEDES`, `FORBIDS`) | `aliases`, `description`, `note`, `reason` |
| story-time integers | beat sheets, summaries, prose, dialogue |

Derive each ASCII id once from a romanization (pinyin for Chinese) and never churn it.
Keep the romanization in `attributes.pinyin`. This is what lets `validate_narrative.py`
and `search_novel.py` (with the CJK tokenizer) work unchanged on a Chinese novel.

## How each phase uses this skill

| Phase | What locale changes |
|---|---|
| **genesis** | World Bible, power system, factions, and character profiles written in-language; cultivation-realm ladder instead of generic "levels"; in-language names (see `references/zh_conventions.md`). The Socratic Muse interviews in the user's language. |
| **architect** | Beat sheets + emotional arcs in-language; pacing follows the locale's serial structure (for Chinese: 黄金三章, 爽点 cadence, 卷/章 sizing). |
| **execution** | Prose drafted in-language; the state extractor (DB-01) still emits ASCII predicates but reads in-language prose — the extraction test traps (metaphor vs. literal, 看 vs. 拿/取) apply per language. |
| **memory** | Summaries/loglines in-language; search uses the CJK-aware tokenizer; “million words” means **百万字** (characters), not English words. |
| **consistency** | World-rule triples keep ASCII relations; the rule *notes* and flagged-issue text are in-language. |

## Set the language

`init_kb.py ... --language zh-Hans --genre 仙侠` records it in `source.language` /
`source.genre`. Existing project? Set `source.language` in `ontology.json` and re-run any
profile builds. Tools read it automatically (e.g. `build_profile.py` stamps the profile
with `language` and budgets tokens with the CJK-aware estimator).

## Lock the terms first (pair with cognitive-alignment)

Invented vocabulary is load-bearing and easy to mistranslate. Before encoding rules, run
**cognitive-alignment** so author and agent agree on each term's meaning — e.g. does
"修为" mean cultivation *level* or cultivation *attainment*? Is "灵根" a spiritual *root*
(talent) or a *meridian*? Record the agreed term + its ASCII id + a gloss. A misunderstood
term poisons every downstream rule and extraction.

## Adding another language

Copy `references/zh_conventions.md` to `references/<lang>_conventions.md` and fill in:
genre list, naming conventions, any power/ranking ladder, serial-structure norms, and the
extraction traps specific to that language (e.g. honorifics, classifiers, idioms that
look like physical events). Set `--language` to its BCP-47 code. The bilingual rule and
the tooling are unchanged.

## Reference files

- `references/zh_conventions.md` — the Chinese web-fiction pack: genres, cultivation
  realm systems, naming (people / sects / techniques / places), serial structure
  (黄金三章 / 爽点 / 卷-章 / 百万字), and extraction traps in Chinese (成语 metaphors,
  看 vs. 拿, breakthrough vs. injury).
- `references/zh_prompts.md` — Chinese-language variants of the key phase prompts
  (世界观生成器, 人物画像, 分场详纲, 状态驱动写作, 状态提取器) so output stays in 中文.
