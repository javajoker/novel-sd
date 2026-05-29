#!/usr/bin/env python3
"""
validate_narrative.py — Validate a NovelForge narrative knowledge base.

Extends the base ontology checks with the temporal / state / mask / multi-thread
cross-file rules that the narrative schema (v1.0-narrative) adds.

Checks performed:
  Canonical graph (ontology.json):
    1. ontology_version == "1.0-narrative"; has 'source' (not 'chunk_id').
    2. entities/relations/events/themes/threads/world_rules are arrays.
    3. No duplicate IDs; entity types in base controlled vocab.
    4. relation.subject/object resolve to declared entities.
    5. relation.valid_to_chapter >= valid_from_chapter (when both set).
    6. event.thread_id resolves to a declared thread; participants/location resolve
       to entities; dependency target events exist.
  Cross-file:
    7. characters/states/<id>.json: snapshots ordered by story_time (duplicates OK when
       chapters share a clock value); each snapshot has story_time.
    8. masks/<id>.json: well-formed; story_time present.
    9. outline/structure.json: chapter.beat_sheet_ref files exist; planned_events
       resolve to declared events.
   10. Referenced *_ref files in entities exist on disk.
   11. Phase-C freshness (sync gate): the deterministic mirrors keep pace with the
       written prose — ontology.source.current_chapter, timeline/calendar.json
       (current_chapter + chapter_to_story_time coverage), memory/summaries.json
       (one entry per chapter), outline status, and narrated-event status. A frozen
       calendar / stale cursor is an ERROR (it breaks the next chapter's CTX-01
       context load). Open plot hooks with no occurrences are a WARNING (manual).
       Repair with narrative-execution/scripts/sync_kb.py --write. Skip with
       --no-freshness.
   12. Event-graph consistency (gate): ontology.json#events is the single source of
       truth. Every event ID referenced by structure.planned_events /
       summaries.events_covered / beats.events_covered must resolve to an
       ontology#event (orphan refs are ERRORS — check #9 skips this during early
       outlining, so a written chapter can reference a never-declared event); every
       ontology event must be in EXACTLY ONE thread.event_ids; and the timeline
       mirrors (thr_*.json shards, index.json, and the optional legacy flat
       events.json when present) must cover exactly the ontology event set. Repair
       with narrative-execution/scripts/sync_events.py --write (also chained by
       sync_kb.py). Skip with --no-events.

Exit codes: 0 valid, 1 invalid, 2 usage error.

Usage:
  python validate_narrative.py <novel-slug>/            # validate whole KB (incl. freshness + events)
  python validate_narrative.py --no-freshness <slug>/   # skip Phase-C freshness gate
  python validate_narrative.py --no-events <slug>/      # skip event-graph consistency gate
  python validate_narrative.py --graph <novel-slug>/ontology.json   # graph only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BASE_ENTITY_TYPES = {"Person", "Place", "Organization", "Object", "Concept", "Work", "Other"}
SCHEMA_VERSION = "1.0-narrative"
DEP_RELATIONS = {"PRECEDES", "CAUSES", "ENABLES", "RETALIATION", "HAPPENED_AFTER"}
CH_NUM_RE = re.compile(r"ch_0*(\d+)")
DRAFTED_STATUSES = {"drafted", "final", "partially_drafted"}

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def load(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        err(f"{path}: invalid JSON: {e}")
        return None


def validate_graph(path: Path) -> set[str]:
    """Validate ontology.json; return the set of declared entity IDs."""
    data = load(path)
    if data is None:
        err(f"{path}: missing or unreadable canonical graph")
        return set()
    if not isinstance(data, dict):
        err(f"{path}: top level must be an object")
        return set()

    if data.get("ontology_version") != SCHEMA_VERSION:
        err(f"{path}: ontology_version must be {SCHEMA_VERSION!r}, got {data.get('ontology_version')!r}")
    if "source" not in data:
        err(f"{path}: canonical graph must contain a 'source' object")
    if "chunk_id" in data:
        err(f"{path}: canonical graph must not contain 'chunk_id'")

    for key in ("entities", "relations", "events", "themes", "threads", "world_rules"):
        if key not in data:
            err(f"{path}: missing required array {key!r}")
        elif not isinstance(data[key], list):
            err(f"{path}: {key!r} must be an array")

    if errors:
        return set()

    seen: set[str] = set()
    entity_ids: set[str] = set()
    event_ids: set[str] = set()
    thread_ids: set[str] = set()

    def reg(item, kind):
        iid = item.get("id")
        if not isinstance(iid, str) or not iid:
            err(f"{kind}: missing/empty 'id'")
            return None
        if iid in seen:
            err(f"{kind}: duplicate id {iid!r}")
        seen.add(iid)
        return iid

    for e in data["entities"]:
        eid = reg(e, "entity")
        if eid:
            entity_ids.add(eid)
        if e.get("type") not in BASE_ENTITY_TYPES:
            err(f"entity {e.get('id')!r}: type must be one of {sorted(BASE_ENTITY_TYPES)}, got {e.get('type')!r}")
        if not isinstance(e.get("canonical_name"), str) or not e.get("canonical_name", "").strip():
            err(f"entity {e.get('id')!r}: canonical_name missing/empty")

    for t in data["threads"]:
        tid = reg(t, "thread")
        if tid:
            thread_ids.add(tid)

    for ev in data["events"]:
        evid = reg(ev, "event")
        if evid:
            event_ids.add(evid)
        if not isinstance(ev.get("name"), str) or not ev.get("name", "").strip():
            err(f"event {ev.get('id')!r}: name missing/empty")
        tid = ev.get("thread_id")
        if tid is not None and tid not in thread_ids:
            err(f"event {ev.get('id')!r}: thread_id {tid!r} not a declared thread")
        for pid in ev.get("participants") or []:
            if pid not in entity_ids:
                err(f"event {ev.get('id')!r}: participant {pid!r} not a declared entity")
        loc = ev.get("location")
        if loc is not None and loc not in entity_ids:
            err(f"event {ev.get('id')!r}: location {loc!r} not a declared entity")

    # second pass: event dependency targets (need full event_ids set)
    # Accepts three shapes: bare string "evt_x" (shorthand), schema object
    # {"event_id","type"}, and the legacy validator object {"event","relation"}.
    for ev in data["events"]:
        for dep in ev.get("dependencies") or []:
            if isinstance(dep, str):
                target, rel = dep, None
            else:
                target = dep.get("event_id") or dep.get("event")
                rel = dep.get("type") or dep.get("relation")
            if target not in event_ids:
                err(f"event {ev.get('id')!r}: dependency target {target!r} not a declared event")
            if rel is not None and rel not in DEP_RELATIONS:
                warn(f"event {ev.get('id')!r}: dependency relation {rel!r} not in {sorted(DEP_RELATIONS)}")

    for r in data["relations"]:
        rid = reg(r, "relation")
        pred = r.get("predicate")
        if not isinstance(pred, str) or not pred.strip():
            err(f"relation {rid!r}: predicate missing/empty")
        elif " " in pred or pred != pred.lower():
            err(f"relation {rid!r}: predicate {pred!r} must be snake_case lowercase")
        if r.get("subject") not in entity_ids:
            err(f"relation {rid!r}: subject {r.get('subject')!r} not a declared entity")
        if r.get("object") not in entity_ids:
            err(f"relation {rid!r}: object {r.get('object')!r} not a declared entity")
        vf, vt = r.get("valid_from_chapter"), r.get("valid_to_chapter")
        if vf is None:
            err(f"relation {rid!r}: valid_from_chapter is required")
        if vt is not None and vf is not None and vt < vf:
            err(f"relation {rid!r}: valid_to_chapter {vt} < valid_from_chapter {vf}")

    return entity_ids


def _ch_num(cid: str) -> int | None:
    m = CH_NUM_RE.search(cid or "")
    return int(m.group(1)) if m else None


def validate_freshness(root: Path) -> None:
    """Phase-C sync gate: the deterministic mirrors (cursors, calendar, summaries,
    outline status) must keep pace with the written prose. A frozen calendar or a
    stale current_chapter silently breaks the time-of-story context the NEXT chapter
    loads under CTX-01 — so these count as ERRORS, not cosmetic warnings.

    Run `narrative-execution/scripts/sync_kb.py --write <kb>` to repair the
    deterministic mirrors; plot-thread occurrences still need a manual pass.
    """
    chapters = sorted(p.stem for p in (root / "chapters").glob("ch_*.md"))
    nums = [n for n in (_ch_num(c) for c in chapters) if n is not None]
    if not nums:
        return  # nothing drafted yet
    max_num = max(nums)
    written_ids = set(chapters)

    # current_chapter cursor (ontology.json.source.current_chapter)
    onto = load(root / "ontology.json")
    if isinstance(onto, dict):
        cur = onto.get("source", {}).get("current_chapter")
        if cur != max_num:
            err(f"[freshness] ontology.source.current_chapter={cur} but latest written chapter is {max_num}")
        # events that were narrated in a chapter must not still be 'planned'
        beats_dir = root / "outline" / "beats"
        covered: set[str] = set()
        for cid in written_ids:
            b = load(beats_dir / f"{cid}.json")
            if isinstance(b, dict):
                covered.update(b.get("events_covered") or [])
        stale_events = [ev.get("id") for ev in onto.get("events", [])
                        if ev.get("id") in covered and ev.get("status") in ("planned", None)]
        if stale_events:
            err(f"[freshness] {len(stale_events)} event(s) narrated in written chapters still "
                f"status=planned: {', '.join(stale_events)}")

    # calendar (state-bearing — must not be frozen)
    cal = load(root / "timeline" / "calendar.json")
    if isinstance(cal, dict):
        if cal.get("current_chapter") != max_num:
            err(f"[freshness] calendar.current_chapter={cal.get('current_chapter')} but latest "
                f"written chapter is {max_num} (calendar is frozen)")
        cts = cal.get("chapter_to_story_time") or {}
        missing = sorted(written_ids - set(cts.keys()))
        if missing:
            err(f"[freshness] calendar.chapter_to_story_time missing {len(missing)} chapter(s): "
                f"{missing[0]}..{missing[-1]}")

    # memory summaries: one entry per written chapter
    summ = load(root / "memory" / "summaries.json")
    if isinstance(summ, dict):
        have = {e.get("chapter_id") for e in summ.get("chapter_summaries", [])}
        missing = sorted(written_ids - have)
        if missing:
            err(f"[freshness] memory/summaries.json missing {len(missing)} chapter summary/ies: "
                f"{missing[0]}..{missing[-1]}")

    # outline status: a written chapter should not still read planned/beats_ready
    struct = load(root / "outline" / "structure.json")
    if isinstance(struct, dict):
        lagging = []
        for vol in struct.get("volumes", []):
            for ch in vol.get("chapters", []):
                if ch.get("id") in written_ids and ch.get("status") not in DRAFTED_STATUSES:
                    lagging.append(ch.get("id"))
        if lagging:
            err(f"[freshness] outline/structure.json: {len(lagging)} written chapter(s) still "
                f"not marked drafted: {', '.join(sorted(lagging))}")

    # plot threads: open hooks with no occurrences — manual judgement, so WARN only
    pt = load(root / "memory" / "plot_threads.json")
    if isinstance(pt, dict):
        empty = [h.get("id") or h.get("hook_id") for h in pt.get("plot_hooks", [])
                 if h.get("status") == "open" and not (h.get("occurrences") or [])]
        if empty:
            warn(f"[freshness] {len(empty)} open plot hook(s) have no recorded occurrences "
                 f"(track manually as scenes touch them): {', '.join(str(x) for x in empty)}")


def validate_event_consistency(root: Path) -> None:
    """Event-graph consistency gate. ontology.json#events is the single source of
    truth; this enforces the three invariants that let an event silently exist in
    one file but not another:

      1. Every event ID referenced by outline/structure.json (planned_events),
         memory/summaries.json (events_covered), or outline/beats/ch_*.json
         (events_covered) resolves to an ontology#event. (Check #9 deliberately
         skips planned_events during early outlining, so a written chapter could
         reference an event that never made it into the graph — this catches it.)
      2. Every ontology event belongs to EXACTLY ONE thread (thread.event_ids), and
         no thread lists an event ID with no matching ontology#event.
      3. The timeline mirrors cover exactly the ontology event set: timeline/events/thr_*.json
         (shards), timeline/events/index.json, and timeline/events.json (the optional
         legacy flat mirror — checked only when present, so a migrated KB that dropped it
         is fine).

    Repair with narrative-execution/scripts/sync_events.py --write (also run automatically
    by sync_kb.py). Skip with --no-events.
    """
    onto = load(root / "ontology.json")
    if not isinstance(onto, dict):
        return
    event_ids = {e.get("id") for e in onto.get("events", []) if e.get("id")}

    # 1. referenced-but-undeclared (orphan references)
    refs: dict[str, set[str]] = {}
    struct = load(root / "outline" / "structure.json")
    for vol in (struct or {}).get("volumes", []) or []:
        for ch in vol.get("chapters", []) or []:
            for ev in ch.get("planned_events") or []:
                refs.setdefault(ev, set()).add(f"structure:{ch.get('id')}")
    summ = load(root / "memory" / "summaries.json")
    for s in (summ or {}).get("chapter_summaries", []) or []:
        for ev in s.get("events_covered") or []:
            refs.setdefault(ev, set()).add(f"summary:{s.get('chapter_id')}")
    for bp in sorted((root / "outline" / "beats").glob("ch_*.json")):
        b = load(bp)
        for ev in (b or {}).get("events_covered") or []:
            refs.setdefault(ev, set()).add(f"beat:{bp.stem}")
    for ev in sorted(set(refs) - event_ids):
        srcs = ", ".join(sorted(refs[ev]))
        err(f"[events] orphan event {ev!r} referenced by [{srcs}] but absent from ontology#events "
            f"(run sync_events.py --write)")

    # 2. thread membership: exactly one
    membership: dict[str, list[str]] = {}
    for t in onto.get("threads", []) or []:
        for eid in t.get("event_ids", []) or []:
            membership.setdefault(eid, []).append(t.get("id"))
    for eid in sorted(event_ids):
        owners = membership.get(eid, [])
        if not owners:
            err(f"[events] event {eid!r} is in no thread.event_ids (must be exactly one)")
        elif len(owners) > 1:
            err(f"[events] event {eid!r} is in {len(owners)} threads {owners} (must be exactly one)")
    for eid in sorted(set(membership) - event_ids):
        err(f"[events] thread(s) {membership[eid]} list event {eid!r} which has no ontology#event")

    # 3. timeline mirror coverage
    flat = load(root / "timeline" / "events.json")
    if isinstance(flat, dict):
        flat_ids = {e.get("id") for e in flat.get("events", []) or []}
        if flat_ids != event_ids:
            miss, extra = sorted(event_ids - flat_ids), sorted(flat_ids - event_ids)
            if miss:
                err(f"[events] timeline/events.json missing {len(miss)} ontology event(s): {', '.join(miss)}")
            if extra:
                err(f"[events] timeline/events.json has {len(extra)} stale event(s) not in ontology: {', '.join(extra)}")
    shard_ids: set[str] = set()
    shard_dir = root / "timeline" / "events"
    if shard_dir.is_dir():
        for sp in sorted(shard_dir.glob("thr_*.json")):
            sh = load(sp)
            for e in (sh or {}).get("events", []) or []:
                shard_ids.add(e.get("id"))
        if shard_ids and shard_ids != event_ids:
            miss, extra = sorted(event_ids - shard_ids), sorted(shard_ids - event_ids)
            if miss:
                err(f"[events] timeline/events/ shards missing {len(miss)} ontology event(s): {', '.join(miss)}")
            if extra:
                err(f"[events] timeline/events/ shards have {len(extra)} stale event(s) not in ontology: {', '.join(extra)}")
    idx = load(shard_dir / "index.json")
    if isinstance(idx, dict):
        idx_ids = {e for ids in (idx.get("by_thread") or {}).values() for e in ids}
        if idx_ids and idx_ids != event_ids:
            miss, extra = sorted(event_ids - idx_ids), sorted(idx_ids - event_ids)
            if miss:
                err(f"[events] timeline/events/index.json by_thread missing {len(miss)} event(s): {', '.join(miss)}")
            if extra:
                err(f"[events] timeline/events/index.json by_thread has {len(extra)} stale event(s): {', '.join(extra)}")


def validate_kb(root: Path, check_freshness: bool = True, check_events: bool = True) -> None:
    entity_ids = validate_graph(root / "ontology.json")

    # 7. character state timelines
    states_dir = root / "characters" / "states"
    if states_dir.is_dir():
        for sf in sorted(states_dir.glob("*.json")):
            data = load(sf)
            if not isinstance(data, dict):
                continue
            # Every snapshot needs a story_time. Multiple snapshots at the SAME story_time
            # are allowed — two chapters can share a clock value (e.g. ch_041 and ch_042
            # both at story_time 21), each contributing its own append-only delta. On-disk
            # order is not load-bearing: snapshots are stored newest-first by convention and
            # the toolkit folds them in sorted order regardless.
            for st in data.get("states") or []:
                if st.get("story_time") is None:
                    err(f"{sf}: a state snapshot is missing story_time")

    # 8. masks
    masks_dir = root / "masks"
    if masks_dir.is_dir():
        for mf in sorted(masks_dir.glob("*.json")):
            data = load(mf)
            if not isinstance(data, dict):
                continue
            for k in data.get("knowledge_at") or []:
                if "story_time" not in k:
                    err(f"{mf}: a knowledge_at entry is missing story_time")

    # 9. outline
    outline = load(root / "outline" / "structure.json")
    if isinstance(outline, dict):
        for vol in outline.get("volumes") or []:
            for ch in vol.get("chapters") or []:
                ref = ch.get("beat_sheet_ref")
                if ref and not (root / ref).exists():
                    warn(f"outline: beat_sheet_ref {ref!r} for {ch.get('id')} does not exist yet")
                for ev in ch.get("planned_events") or []:
                    # planned events may not yet be in the graph during early outlining
                    pass

    # 10. entity *_ref files
    graph = load(root / "ontology.json")
    if isinstance(graph, dict):
        for e in graph.get("entities") or []:
            for ref_key in ("profile_ref", "state_ref", "mask_ref"):
                ref = e.get(ref_key)
                if ref and not (root / ref).exists():
                    warn(f"entity {e.get('id')}: {ref_key} {ref!r} does not exist yet")

    # 11. Phase-C freshness: deterministic mirrors must keep pace with the prose
    if check_freshness:
        validate_freshness(root)

    # 12. Event-graph consistency: refs resolve, one-thread membership, mirror coverage
    if check_events:
        validate_event_consistency(root)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", help="novel KB root directory, or a single ontology.json with --graph")
    p.add_argument("--graph", action="store_true", help="validate only the canonical graph file at <path>")
    p.add_argument("--no-freshness", action="store_true",
                   help="skip the Phase-C freshness gate (cursors/calendar/summaries/status "
                        "vs. written chapters); structural checks only")
    p.add_argument("--no-events", action="store_true",
                   help="skip the event-graph consistency gate (orphan refs / one-thread "
                        "membership / timeline mirror coverage)")
    args = p.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"path not found: {path}", file=sys.stderr)
        sys.exit(2)

    if args.graph:
        validate_graph(path)
    else:
        if not path.is_dir():
            print(f"expected a KB directory (or use --graph for a single file): {path}", file=sys.stderr)
            sys.exit(2)
        validate_kb(path, check_freshness=not args.no_freshness,
                    check_events=not args.no_events)

    for w in warnings:
        print(f"  ⚠ {w}", file=sys.stderr)
    if errors:
        print(f"✗ {path} — {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print(f"✓ {path} valid" + (f" ({len(warnings)} warning(s))" if warnings else ""))
    sys.exit(0)


if __name__ == "__main__":
    main()
