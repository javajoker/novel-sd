#!/usr/bin/env python3
"""
init_kb.py — Initialize a full NovelForge novel WRITING PROJECT.

Scaffolds the complete project structure (not just the bare graph): the temporal
knowledge base, the chapter-masked profile directory, the reference-materials folder,
a README that documents the layout and the tools, and a .gitignore. After this, run
narrative-genesis to populate world/ and characters/.

Project structure created:
  <novel-slug>/
  ├── README.md                  project guide + tool cheat-sheet
  ├── .gitignore                 ignores the search-index cache
  ├── ontology.json              canonical temporal graph
  ├── world/world_bible.json     worldview (power system, geography, factions, rules)
  ├── characters/                profiles + T=0 states (states/ for per-chapter timelines)
  ├── timeline/                  threads (swimlanes), events, calendar
  ├── outline/                   Novel→Volume→Chapter tree + beats/ sheets
  ├── masks/                     per-character knowledge masks (fog of war)
  ├── chapters/                  prose drafts + profiles/ (chapter-masked KB profiles)
  ├── memory/                    hierarchical summaries + plot-thread tracker
  └── reference/                 reference docs / resources + index.json manifest

Usage:
  python init_kb.py <novel-slug-dir> --title "My Novel" --author "Me" [--unit chapter]
  python init_kb.py wuxia --title "九天剑诀" --author "我" --language zh-Hans --genre 仙侠
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", help="target KB directory (the novel slug)")
    p.add_argument("--title", required=True)
    p.add_argument("--author", default="")
    p.add_argument("--unit", choices=["chapter", "world_day"], default="chapter")
    p.add_argument("--language", default="en",
                   help="BCP-47 code for the PROSE language: en, zh-Hans, zh-Hant, ja, ... "
                        "(graph IDs + relation predicates stay ASCII regardless)")
    p.add_argument("--genre", default="",
                   help="optional genre tag, e.g. 玄幻 / 仙侠 / xianxia / epic_fantasy")
    args = p.parse_args()

    root = Path(args.root)
    for d in ("world", "characters/states", "timeline", "outline/beats",
              "masks", "chapters/profiles", "memory", "reference"):
        (root / d).mkdir(parents=True, exist_ok=True)

    write_json(root / "ontology.json", {
        "ontology_version": "1.0-narrative",
        "source": {
            "novel_title": args.title,
            "novel_author": args.author,
            "story_time_unit": args.unit,
            "current_chapter": 0,
            "language": args.language,
            "genre": args.genre,
        },
        "entities": [], "relations": [], "events": [],
        "themes": [], "threads": [], "world_rules": [],
    })

    write_json(root / "world" / "world_bible.json", {
        "world_name": "", "power_system": {}, "geography": {},
        "factions": [], "ontology_triples": [],
    })
    write_json(root / "timeline" / "threads.json", {"threads": []})
    write_json(root / "timeline" / "events.json", {"events": []})
    write_json(root / "timeline" / "calendar.json", {
        "story_time_unit": args.unit, "world_calendar": {},
        "chapter_to_world_day": {}, "travel_rules": [], "movement_speeds": {},
    })
    write_json(root / "outline" / "structure.json", {
        "novel_title": args.title, "logline": "", "volumes": [],
    })
    write_json(root / "memory" / "summaries.json", {
        "novel_summary": "", "volume_summaries": [],
        "chapter_summaries": [], "scene_chunks": [],
    })
    write_json(root / "memory" / "plot_threads.json", {"plot_hooks": []})

    # reference materials manifest
    write_json(root / "reference" / "index.json", {
        "description": "Manifest of external reference docs/resources for this novel "
                       "(research, real-world sources, style samples, maps, art). Drop "
                       "files into reference/ and register them here.",
        "resources": [
            # { "id": "ref_0001", "title": "...", "path": "reference/<file>",
            #   "kind": "research|style|map|art|notes|source_text", "note": "..." }
        ],
    })

    # README
    write_text(root / "README.md", README.format(
        title=args.title, unit=args.unit,
        language=args.language, genre=args.genre or "(unset)"))
    # .gitignore (search-index cache only; the KB itself is the product and is tracked)
    write_text(root / ".gitignore", ".index/\n*.pyc\n__pycache__/\n.DS_Store\n")

    print(f"✓ initialized novel project at {root}/")
    print("  Next: run narrative-genesis to populate world/ and characters/.")
    print("  Inspect:  python view_kb.py {root}/".format(root=root))


README = """# {title}

A NovelForge novel project — the manuscript is decoupled from the *world state*. Prose
lives in `chapters/`; the truth (who knows/holds what, who feels what about whom, when,
and why) lives in a temporal knowledge base. This is what keeps a million-word novel
consistent and lets it exceed an LLM's context window.

Story-time unit: **{unit}** · prose language: **{language}** · genre: **{genre}**.

> Prose (and `canonical_name` / `aliases`) are written in the project language. Graph
> **IDs** (`char_ye_fan`) and **relation predicates** (`hates`, `member_of`) stay ASCII
> snake_case regardless, so tooling and merges work across languages. For non-English
> projects, consult the **narrative-locale** skill for naming, genre, and structure
> conventions, and run **cognitive-alignment** to lock invented terms with the author.

## Layout

| Path | What |
|---|---|
| `ontology.json` | canonical temporal graph: entities, time-variant relations, events, threads, world rules |
| `world/` | worldview / World Bible (power system, geography, factions, logic rules) |
| `characters/` | character profiles + T=0 states; `states/` = per-chapter state timelines |
| `timeline/` | narrative threads (swimlanes), event graph, world calendar |
| `outline/` | Novel→Volume→Chapter write-ahead tree; `beats/` = per-chapter beat sheets |
| `masks/` | per-character knowledge masks (fog of war) |
| `chapters/` | prose drafts; `profiles/` = chapter-masked KB profiles (the memory primitive) |
| `memory/` | hierarchical summaries (L1–L4) + plot-thread / open-loop tracker |
| `reference/` | reference docs & resources + `index.json` manifest |

## Tools (from the narrative-toolkit skill)

```bash
# Inspect the KB
python view_kb.py .                       # overview
python view_kb.py . --timeline            # events as thread swimlanes
python view_kb.py . --character char_x    # one character across time
python view_kb.py . --snapshot 45         # world state as of chapter 45

# Build the chapter-masked memory profile (feed THIS to the writer, not the whole novel)
python build_profile.py . --chapter ch_045

# Search: knowledge base first, then KAG over the prose
python search_novel.py . "why does the villain attack?" --as-of 50

# Validate structure + continuity
python validate_narrative.py .
python check_consistency.py .
```

## How memory beats the token limit

For any chapter you write, `build_profile.py` materializes a few-KB snapshot of exactly
the world state as of that chapter, masked to the POV character's knowledge. You feed
that compact profile to the model instead of the manuscript. When you need actual prose,
`search_novel.py` does KB-first retrieval then pulls only the relevant passages (KAG).
The full text is never required in context at once.
"""


if __name__ == "__main__":
    main()
