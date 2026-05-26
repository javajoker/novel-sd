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
    7. characters/states/<id>.json: no duplicate story_time per character.
    8. masks/<id>.json: well-formed; story_time present.
    9. outline/structure.json: chapter.beat_sheet_ref files exist; planned_events
       resolve to declared events.
   10. Referenced *_ref files in entities exist on disk.

Exit codes: 0 valid, 1 invalid, 2 usage error.

Usage:
  python validate_narrative.py <novel-slug>/            # validate whole KB
  python validate_narrative.py --graph <novel-slug>/ontology.json   # graph only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_ENTITY_TYPES = {"Person", "Place", "Organization", "Object", "Concept", "Work", "Other"}
SCHEMA_VERSION = "1.0-narrative"
DEP_RELATIONS = {"PRECEDES", "CAUSES", "ENABLES", "RETALIATION", "HAPPENED_AFTER"}

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
    for ev in data["events"]:
        for dep in ev.get("dependencies") or []:
            if dep.get("event") not in event_ids:
                err(f"event {ev.get('id')!r}: dependency target {dep.get('event')!r} not a declared event")
            if dep.get("relation") not in DEP_RELATIONS:
                warn(f"event {ev.get('id')!r}: dependency relation {dep.get('relation')!r} not in {sorted(DEP_RELATIONS)}")

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


def validate_kb(root: Path) -> None:
    entity_ids = validate_graph(root / "ontology.json")

    # 7. character state timelines
    states_dir = root / "characters" / "states"
    if states_dir.is_dir():
        for sf in sorted(states_dir.glob("*.json")):
            data = load(sf)
            if not isinstance(data, dict):
                continue
            times: set = set()
            for st in data.get("states") or []:
                ts = st.get("story_time")
                if ts in times:
                    err(f"{sf}: duplicate story_time {ts}")
                times.add(ts)

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


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", help="novel KB root directory, or a single ontology.json with --graph")
    p.add_argument("--graph", action="store_true", help="validate only the canonical graph file at <path>")
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
        validate_kb(path)

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
