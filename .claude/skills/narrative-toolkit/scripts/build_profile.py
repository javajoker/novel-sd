#!/usr/bin/env python3
"""
build_profile.py — Materialize a CHAPTER-MASKED KB PROFILE.

This is the memory primitive that lets a novel exceed an LLM's context window. Instead
of feeding the whole manuscript, you feed this compact, self-contained snapshot of the
knowledge base *as of* a chapter, masked to the POV character's knowledge (fog of war).
A profile is a few KB, not a few hundred KB — so a 2M-word novel still fits the prompt.

What goes in a profile for chapter N (POV = P):
  - summary_context     : hierarchical summaries up to N (novel + volume + recent chapters)
  - active_entities     : entities relevant as of N, each with state-as-of-N
  - relations_in_effect : edges valid as of N (the social/world graph "now")
  - events_so_far       : events with story_time <= N
  - pov_knowledge_mask  : what P knows / does not know (fog of war)
  - visible_facts       : facts P may write from (knowledge masking applied)
  - open_plot_threads   : unresolved foreshadowing to keep live
  - world_rules         : the logic locks
  - token_estimate      : rough size, so you can budget the prompt

Writes to <novel-slug>/chapters/profiles/<chapter_id>.json (or stdout with --stdout).

Usage:
  python build_profile.py <novel-slug>/ --chapter ch_045
  python build_profile.py <novel-slug>/ --story-time 45 --pov char_ye_fan
  python build_profile.py <novel-slug>/ --chapter ch_045 --recent 3 --stdout
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from narrative_kb import NarrativeKB, _int, estimate_tokens  # noqa: E402


def resolve_chapter(kb: NarrativeKB, chapter_id: str):
    for vol in (kb.outline.get("volumes") or []):
        for ch in (vol.get("chapters") or []):
            if ch.get("id") == chapter_id:
                return ch, vol
    return None, None


def build(kb: NarrativeKB, t: int, pov: str | None, chapter_id: str | None,
          recent: int) -> dict:
    sums = kb.summaries_up_to(t)
    recent_chs = sums["chapters"][-recent:] if recent else sums["chapters"]
    # volume summary covering this story-time
    vol_summary = None
    for v in (kb.outline.get("volumes") or []):
        span = v.get("time_span") or {}
        if _int(span.get("from"), 0) <= t <= _int(span.get("to"), 10**9):
            for vs in (sums["volumes"] or []):
                if vs.get("volume_id") == v.get("id"):
                    vol_summary = vs.get("summary")

    # entities active as of N: participants of events so far + endpoints of live relations
    active_ids = set()
    for e in kb.events_up_to(t):
        active_ids.update(e.get("participants") or [])
        if e.get("location"):
            active_ids.add(e["location"])
    for r in kb.relations_as_of(t):
        active_ids.add(r.get("subject")); active_ids.add(r.get("object"))
    if pov:
        active_ids.add(pov)
    active_ids = {i for i in active_ids if i in kb.entities}

    active_entities = []
    for eid in sorted(active_ids):
        e = kb.entities[eid]
        item = {"id": eid, "name": e.get("canonical_name"), "type": e.get("type"),
                "subtype": e.get("subtype"), "description": e.get("description", "")}
        if e.get("type") == "Person":
            item["state"] = kb.character_state_as_of(eid, t)
        active_entities.append(item)

    relations = [{
        "subject": r.get("subject"), "subject_name": kb.name(r.get("subject")),
        "predicate": r.get("predicate"),
        "object": r.get("object"), "object_name": kb.name(r.get("object")),
        "properties": r.get("properties", {}),
        "since_chapter": r.get("valid_from_chapter"),
    } for r in kb.relations_as_of(t)]

    events = [{"id": e.get("id"), "name": e.get("name"),
               "story_time": _int(e.get("story_time"), 0),
               "thread_id": e.get("thread_id"),
               "participants": e.get("participants", [])}
              for e in kb.events_up_to(t)]

    pov_mask = kb.mask_as_of(pov, t) if pov else {}
    # knowledge masking: facts the POV may write from
    visible_facts = pov_mask.get("facts_known", []) if pov else []

    profile = {
        "chapter_id": chapter_id,
        "story_time": t,
        "pov_character": pov,
        "pov_character_name": kb.name(pov) if pov else None,
        "generated_as_of": t,
        "summary_context": {
            "novel": sums["novel"],
            "volume": vol_summary,
            "recent_chapters": [{"chapter_id": c.get("chapter_id"),
                                 "logline": c.get("logline"),
                                 "story_time": c.get("story_time")} for c in recent_chs],
        },
        "active_entities": active_entities,
        "relations_in_effect": relations,
        "events_so_far": events,
        "pov_knowledge_mask": pov_mask,
        "visible_facts": visible_facts,
        "open_plot_threads": [{"concept": h.get("concept"), "status": h.get("status"),
                               "last_mention": h.get("last_mention_chapter"),
                               "risk": h.get("risk")} for h in kb.open_threads()],
        "world_rules": kb.world_rules,
        "language": kb.source.get("language", "en"),
    }
    profile["token_estimate"] = estimate_tokens(json.dumps(profile, ensure_ascii=False))
    return profile


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--chapter", metavar="ID", help="resolve story-time + POV from the outline chapter")
    g.add_argument("--story-time", type=int, metavar="N")
    ap.add_argument("--pov", metavar="CHAR_ID", help="POV character (required with --story-time unless none)")
    ap.add_argument("--recent", type=int, default=5, help="how many recent chapter loglines to include")
    ap.add_argument("--stdout", action="store_true", help="print instead of writing to chapters/profiles/")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr); sys.exit(2)
    kb = NarrativeKB(root)

    chapter_id, pov = args.chapter, args.pov
    if args.chapter:
        ch, _vol = resolve_chapter(kb, args.chapter)
        if ch is None:
            print(f"chapter {args.chapter!r} not in outline", file=sys.stderr); sys.exit(2)
        t = _int(ch.get("story_time"), 0)
        pov = pov or ch.get("pov_character")
    else:
        t = args.story_time

    profile = build(kb, t, pov, chapter_id, args.recent)

    if args.stdout or not chapter_id:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
        if not chapter_id and not args.stdout:
            print("\n(no --chapter given, so not written to disk; pass --chapter to persist)",
                  file=sys.stderr)
    else:
        out = root / "chapters" / "profiles" / f"{chapter_id}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"✓ wrote {out}  (~{profile['token_estimate']} tokens, "
              f"{len(profile['active_entities'])} active entities, "
              f"{len(profile['relations_in_effect'])} live relations)")


if __name__ == "__main__":
    main()
