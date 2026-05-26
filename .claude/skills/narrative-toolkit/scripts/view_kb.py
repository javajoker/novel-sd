#!/usr/bin/env python3
"""
view_kb.py — Inspect a NovelForge narrative knowledge base from the command line.

Views:
  (default)            overview: counts, threads, volumes, current chapter.
  --timeline           events ordered by story-time, grouped into thread swimlanes.
  --character <id>     one character: profile, state timeline, relations over time.
  --events             the event graph: each event with its causal dependencies.
  --snapshot N         full world state as of story-time N (locations, relations, statuses).
  --chapter <id>       same as --snapshot, resolved from the chapter's story-time.

Add --json for machine-readable output. Pure standard library.

Usage:
  python view_kb.py <novel-slug>/ --timeline
  python view_kb.py <novel-slug>/ --character char_ye_fan
  python view_kb.py <novel-slug>/ --snapshot 45
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from narrative_kb import NarrativeKB, _int  # noqa: E402


def overview(kb: NarrativeKB) -> dict:
    return {
        "novel": kb.source.get("novel_title", "(untitled)"),
        "author": kb.source.get("novel_author", ""),
        "story_time_unit": kb.source.get("story_time_unit", "chapter"),
        "current_chapter": kb.source.get("current_chapter", 0),
        "counts": {
            "entities": len(kb.entities), "relations": len(kb.relations),
            "events": len(kb.events), "threads": len(kb.threads),
            "world_rules": len(kb.world_rules), "themes": len(kb.themes),
            "chapters_drafted": len(kb.chapter_files()),
        },
        "threads": [{"id": t.get("id"), "name": t.get("name"),
                     "pov": t.get("pov_character"), "events": len(t.get("event_ids") or [])}
                    for t in kb.threads],
        "volumes": [{"id": v.get("id"), "title": v.get("title"),
                     "chapters": len(v.get("chapters") or [])}
                    for v in (kb.outline.get("volumes") or [])],
        "open_plot_threads": [{"concept": h.get("concept"), "status": h.get("status"),
                               "last_mention": h.get("last_mention_chapter")}
                              for h in kb.open_threads()],
    }


def timeline(kb: NarrativeKB) -> dict:
    lanes: dict = {}
    for t in kb.threads:
        lanes[t.get("id")] = {"name": t.get("name"), "pov": t.get("pov_character"), "events": []}
    lanes.setdefault(None, {"name": "(unassigned)", "pov": None, "events": []})
    for e in sorted(kb.events, key=lambda e: _int(e.get("story_time"), 0)):
        lane = e.get("thread_id") if e.get("thread_id") in lanes else None
        lanes[lane]["events"].append({
            "id": e.get("id"), "name": e.get("name"),
            "story_time": _int(e.get("story_time"), 0),
            "location": kb.name(e.get("location")) if e.get("location") else None,
            "participants": [kb.name(p) for p in (e.get("participants") or [])],
            "status": e.get("status", ""),
        })
    return {"swimlanes": {k: v for k, v in lanes.items() if v["events"] or k is not None}}


def character_view(kb: NarrativeKB, cid: str) -> dict:
    if cid not in kb.entities:
        return {"error": f"no entity {cid!r}"}
    prof = kb.profile(cid)
    snaps = kb.state_snapshots(cid)
    # relations grouped by validity
    rels = []
    for r in kb.relations:
        if r.get("subject") == cid or r.get("object") == cid:
            rels.append({
                "subject": kb.name(r.get("subject")), "predicate": r.get("predicate"),
                "object": kb.name(r.get("object")),
                "from": r.get("valid_from_chapter"), "to": r.get("valid_to_chapter"),
                "properties": r.get("properties", {}),
            })
    return {
        "id": cid, "name": kb.name(cid),
        "subtype": kb.entities[cid].get("subtype"),
        "base_profile": prof.get("base_profile", {}),
        "initial_state": prof.get("initial_state", {}),
        "state_timeline": [{"story_time": _int(s.get("story_time"), 0),
                            "chapter": s.get("chapter_id"),
                            "location": s.get("location"),
                            "inventory_delta": s.get("inventory_delta", []),
                            "status": s.get("status", []),
                            "knowledge_gained": s.get("knowledge_gained", [])}
                           for s in snaps],
        "relations": sorted(rels, key=lambda r: _int(r["from"], 0)),
    }


def events_view(kb: NarrativeKB) -> dict:
    return {"events": [{
        "id": e.get("id"), "name": e.get("name"),
        "story_time": _int(e.get("story_time"), 0), "thread": e.get("thread_id"),
        "location": kb.name(e.get("location")) if e.get("location") else None,
        "participants": [kb.name(p) for p in (e.get("participants") or [])],
        "dependencies": [f"{d.get('relation')} {d.get('event')}" for d in (e.get("dependencies") or [])],
        "prerequisites": e.get("prerequisites", []),
        "projected_outcome": e.get("projected_outcome", {}),
        "status": e.get("status", ""),
    } for e in sorted(kb.events, key=lambda e: _int(e.get("story_time"), 0))]}


def snapshot(kb: NarrativeKB, t: int) -> dict:
    chars = [eid for eid, e in kb.entities.items() if e.get("type") == "Person"]
    return {
        "as_of_story_time": t,
        "characters": [{
            "id": c, "name": kb.name(c),
            **kb.character_state_as_of(c, t),
            "knows": kb.mask_as_of(c, t),
        } for c in chars],
        "relations_in_effect": [{
            "subject": kb.name(r.get("subject")), "predicate": r.get("predicate"),
            "object": kb.name(r.get("object")), "properties": r.get("properties", {}),
        } for r in kb.relations_as_of(t)],
        "events_so_far": [{"id": e.get("id"), "name": e.get("name"),
                           "story_time": _int(e.get("story_time"), 0)}
                          for e in kb.events_up_to(t)],
    }


def chapter_to_time(kb: NarrativeKB, chapter_id: str):
    for vol in (kb.outline.get("volumes") or []):
        for ch in (vol.get("chapters") or []):
            if ch.get("id") == chapter_id:
                return _int(ch.get("story_time"), 0)
    return None


# --------- pretty printers ---------

def p(s=""):
    print(s)


def print_overview(d):
    p(f"📖 {d['novel']}" + (f" — {d['author']}" if d['author'] else ""))
    p(f"   story-time unit: {d['story_time_unit']} · current chapter: {d['current_chapter']}")
    c = d["counts"]
    p(f"   {c['entities']} entities · {c['relations']} relations · {c['events']} events · "
      f"{c['threads']} threads · {c['world_rules']} rules · {c['chapters_drafted']} chapters drafted")
    if d["threads"]:
        p("\n  Threads:")
        for t in d["threads"]:
            p(f"    • {t['name']} ({t['id']}) pov={t['pov']} — {t['events']} events")
    if d["volumes"]:
        p("\n  Volumes:")
        for v in d["volumes"]:
            p(f"    • {v['title']} ({v['id']}) — {v['chapters']} chapters")
    if d["open_plot_threads"]:
        p("\n  ⚠ Open plot threads:")
        for h in d["open_plot_threads"]:
            p(f"    • [{h['status']}] {h['concept']} (last: {h['last_mention']})")


def print_timeline(d):
    p("🕓 Timeline (thread swimlanes)\n")
    for lane_id, lane in d["swimlanes"].items():
        p(f"━━ {lane['name']} ({lane_id}) pov={lane['pov']}")
        for e in lane["events"]:
            who = ", ".join(e["participants"]) or "—"
            loc = e["location"] or "—"
            p(f"   t={e['story_time']:>4}  {e['name']}  @{loc}  [{who}]  ({e['status']})")
        p()


def print_character(d):
    if "error" in d:
        p(d["error"]); return
    p(f"👤 {d['name']} ({d['id']}) — {d.get('subtype')}")
    bp = d["base_profile"]
    if bp.get("the_ghost"):
        p(f"   Ghost: {bp['the_ghost']}")
    if bp.get("the_lie"):
        p(f"   Lie:   {bp['the_lie']}")
    p("\n  State timeline:")
    for s in d["state_timeline"]:
        inv = ", ".join(f"{x.get('action')}:{x.get('item')}" for x in s["inventory_delta"]) or "—"
        st = ", ".join(x.get("desc", x.get("type", "")) for x in s["status"]) or "—"
        p(f"    t={s['story_time']:>4} ({s['chapter']}) loc={s['location']}  inv[{inv}]  status[{st}]")
    p("\n  Relations over time:")
    for r in d["relations"]:
        span = f"ch{r['from']}→" + (str(r['to']) if r['to'] is not None else "now")
        props = " ".join(f"{k}={v}" for k, v in (r["properties"] or {}).items())
        p(f"    {r['subject']} --{r['predicate']}--> {r['object']}  [{span}] {props}")


def print_events(d):
    p("🔗 Event graph\n")
    for e in d["events"]:
        who = ", ".join(e["participants"]) or "—"
        p(f"  {e['id']}  t={e['story_time']}  {e['name']}  @{e['location'] or '—'}  [{who}]  ({e['status']})")
        for dep in e["dependencies"]:
            p(f"      ↳ depends: {dep}")
        for pre in e["prerequisites"]:
            p(f"      ↳ requires: {pre.get('type')} {pre.get('object') or pre.get('fact')}")


def print_snapshot(d):
    p(f"📸 World snapshot as of story-time {d['as_of_story_time']}\n")
    for c in d["characters"]:
        st = ", ".join(x.get("desc", x.get("type", "")) for x in c["status"]) or "—"
        p(f"  👤 {c['name']}  @{c['location'] or '—'}")
        p(f"       inventory: {', '.join(c['inventory']) or '—'}")
        p(f"       status: {st}")
        if c["psychology"]:
            p(f"       psychology: {c['psychology']}")
        known = c["knows"]["facts_known"]
        unknown = c["knows"]["facts_unknown"]
        if known or unknown:
            p(f"       knows: {', '.join(known) or '—'}   unknown: {', '.join(unknown) or '—'}")
    p("\n  Relations in effect:")
    for r in d["relations_in_effect"]:
        props = " ".join(f"{k}={v}" for k, v in (r["properties"] or {}).items())
        p(f"    {r['subject']} --{r['predicate']}--> {r['object']}  {props}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--timeline", action="store_true")
    g.add_argument("--character", metavar="ID")
    g.add_argument("--events", action="store_true")
    g.add_argument("--snapshot", type=int, metavar="N")
    g.add_argument("--chapter", metavar="ID")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr); sys.exit(2)
    kb = NarrativeKB(root)

    if args.timeline:
        d, pr = timeline(kb), print_timeline
    elif args.character:
        d, pr = character_view(kb, args.character), print_character
    elif args.events:
        d, pr = events_view(kb), print_events
    elif args.snapshot is not None:
        d, pr = snapshot(kb, args.snapshot), print_snapshot
    elif args.chapter:
        t = chapter_to_time(kb, args.chapter)
        if t is None:
            print(f"chapter {args.chapter!r} not found in outline", file=sys.stderr); sys.exit(2)
        d, pr = snapshot(kb, t), print_snapshot
    else:
        d, pr = overview(kb), print_overview

    if args.json:
        print(json.dumps(d, ensure_ascii=False, indent=2))
    else:
        pr(d)


if __name__ == "__main__":
    main()
