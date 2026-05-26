#!/usr/bin/env python3
"""
check_consistency.py — Deterministic consistency checker for a NovelForge narrative KB.

Finds the mechanical continuity violations without an LLM, grouped into four classes:

  paradox    — a character participates in two events at the same story_time but
               different locations; or participates after a `death` status.
  possession — an event prerequisite of type "possession" requires an item the
               character does not hold (per reconstructed inventory) as of that time.
  knowledge  — an event prerequisite of type "knowledge" requires a fact the
               character's knowledge mask marks unknown as of that time.
  ripple     — a *future* (planned/outlined) event depends on an item that was
               permanently removed/destroyed at an earlier story_time.

It REPORTS only — it never edits the KB. A human (or the rule-judgement prompts in
references/consistency_prompts.md) decides whether each candidate is a real bug or an
intended twist.

Usage:
  python check_consistency.py <novel-slug>/
  python check_consistency.py <novel-slug>/ --as-of 45
  python check_consistency.py <novel-slug>/ --class paradox
  python check_consistency.py <novel-slug>/ --json

Exit: 0 clean, 1 violations found, 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CLASSES = ("paradox", "possession", "knowledge", "ripple")
FUTURE_STATUSES = {"planned", "outlined", "beats_ready"}
DEAD_STATUSES = {"death", "coma"}


def load(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def st_int(v, default=None):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


class KB:
    def __init__(self, root: Path):
        self.root = root
        g = load(root / "ontology.json") or {}
        self.entities = {e["id"]: e for e in g.get("entities", []) if "id" in e}
        self.events = g.get("events", [])
        self.relations = g.get("relations", [])
        # T=0 baseline inventory (story start, applies before every chapter): char_id -> set
        self.baseline_inv: dict[str, set] = {}
        # per-character chapter-delta inventory timeline: char_id -> list[(story_time, action, item)]
        self.inv_events: dict[str, list] = {}
        # per-character status timeline: char_id -> list[(story_time, type)]
        self.status_events: dict[str, list] = {}
        self._load_characters()
        self.masks = self._load_masks()

    def _load_characters(self):
        for eid in self.entities:
            prof = load(self.root / "characters" / f"{eid}.json")
            if isinstance(prof, dict):
                init = prof.get("initial_state", {})
                for it in init.get("inventory", []) or []:
                    item = it.get("item") if isinstance(it, dict) else it
                    if item:
                        self.baseline_inv.setdefault(eid, set()).add(item)
            states = load(self.root / "characters" / "states" / f"{eid}.json")
            if isinstance(states, dict):
                for snap in states.get("states", []) or []:
                    t = st_int(snap.get("story_time"), 0)
                    for d in snap.get("inventory_delta", []) or []:
                        self.inv_events.setdefault(eid, []).append((t, d.get("action"), d.get("item")))
                    for s in snap.get("status", []) or []:
                        self.status_events.setdefault(eid, []).append((t, s.get("type")))

    def _load_masks(self) -> dict:
        masks = {}
        mdir = self.root / "masks"
        if mdir.is_dir():
            for mf in mdir.glob("*.json"):
                data = load(mf)
                if isinstance(data, dict) and data.get("character_id"):
                    masks[data["character_id"]] = data.get("knowledge_at", [])
        return masks

    def inventory_as_of(self, char_id: str, t: int, inclusive: bool = True) -> set:
        """Inventory the character holds as of story_time t. The T=0 baseline always
        applies. When inclusive is False, chapter deltas AT t are excluded — use that
        for prerequisite checks, so an item the event itself consumes still counts as
        held when the event begins."""
        owned = set(self.baseline_inv.get(char_id, set()))
        for (ts, action, item) in sorted(self.inv_events.get(char_id, []), key=lambda x: x[0]):
            if not item:
                continue
            if (ts > t) or (not inclusive and ts == t):
                continue
            if action == "add":
                owned.add(item)
            elif action in ("remove", "destroyed"):
                owned.discard(item)
        return owned

    def removed_items(self, as_of=None) -> dict:
        """item -> earliest story_time it was removed/destroyed (and not re-added later).
        Only considers deltas with story_time <= as_of when as_of is set."""
        out = {}
        for char_id, evs in self.inv_events.items():
            timeline = sorted(evs, key=lambda x: x[0])
            held = {}
            for (ts, action, item) in timeline:
                if not item or (as_of is not None and ts > as_of):
                    continue
                if action == "add":
                    held[item] = True
                elif action in ("remove", "destroyed"):
                    held[item] = False
                    out[item] = ts
            # if re-added after removal, it's not permanently gone
            for item, present in held.items():
                if present and item in out:
                    del out[item]
        return out

    def is_dead_before(self, char_id: str, t: int):
        for (ts, typ) in self.status_events.get(char_id, []):
            if typ == "death" and ts <= t:
                return ts
        return None

    def knows_as_of(self, char_id: str, t: int):
        """Return (known:set, unknown:set) from the latest mask entry <= t."""
        entries = sorted(self.masks.get(char_id, []), key=lambda k: st_int(k.get("story_time"), 0))
        known, unknown = set(), set()
        for k in entries:
            if st_int(k.get("story_time"), 0) <= t:
                known = set(k.get("facts_known", []) or [])
                unknown = set(k.get("facts_unknown", []) or [])
        return known, unknown


def name(kb: KB, eid: str) -> str:
    e = kb.entities.get(eid)
    return e.get("canonical_name", eid) if e else eid


def check_paradox(kb: KB, as_of):
    out = []
    by_time: dict = {}
    for ev in kb.events:
        t = st_int(ev.get("story_time"))
        if t is None or (as_of is not None and t > as_of):
            continue
        by_time.setdefault(t, []).append(ev)
    # location-at-same-time
    for t, evs in by_time.items():
        loc_by_char: dict = {}
        for ev in evs:
            loc = ev.get("location")
            if not loc:
                continue
            for p in ev.get("participants", []) or []:
                if p in loc_by_char and loc_by_char[p][0] != loc:
                    prev_loc, prev_ev = loc_by_char[p]
                    out.append({
                        "class": "paradox", "severity": "high",
                        "issue": f"{name(kb,p)} is in two places at story_time {t}: "
                                 f"{name(kb,prev_loc)} ({prev_ev}) and {name(kb,loc)} ({ev.get('id')}).",
                    })
                else:
                    loc_by_char[p] = (loc, ev.get("id"))
    # acting after death
    for ev in kb.events:
        t = st_int(ev.get("story_time"))
        if t is None or (as_of is not None and t > as_of):
            continue
        for p in ev.get("participants", []) or []:
            dts = kb.is_dead_before(kb_char := p, t)
            if dts is not None and dts < t:
                out.append({
                    "class": "paradox", "severity": "critical",
                    "issue": f"{name(kb,p)} participates in {ev.get('id')} at story_time {t} "
                             f"but has a death status at story_time {dts}.",
                })
    return out


def check_possession(kb: KB, as_of):
    out = []
    for ev in kb.events:
        t = st_int(ev.get("story_time"))
        if t is None or (as_of is not None and t > as_of):
            continue
        for pre in ev.get("prerequisites", []) or []:
            if pre.get("type") != "possession":
                continue
            char, obj = pre.get("entity"), pre.get("object")
            if not char or not obj:
                continue
            if obj not in kb.inventory_as_of(char, t, inclusive=False):
                out.append({
                    "class": "possession", "severity": "high",
                    "issue": f"Event {ev.get('id')} (story_time {t}) requires {name(kb,char)} to "
                             f"possess {name(kb,obj)}, but they do not hold it entering that chapter.",
                })
    return out


def check_knowledge(kb: KB, as_of):
    out = []
    for ev in kb.events:
        t = st_int(ev.get("story_time"))
        if t is None or (as_of is not None and t > as_of):
            continue
        for pre in ev.get("prerequisites", []) or []:
            if pre.get("type") != "knowledge":
                continue
            char, fact = pre.get("entity"), pre.get("fact")
            if not char or not fact:
                continue
            known, unknown = kb.knows_as_of(char, t)
            if fact in unknown or (known and fact not in known):
                out.append({
                    "class": "knowledge", "severity": "high",
                    "issue": f"Event {ev.get('id')} (story_time {t}) needs {name(kb,char)} to know "
                             f"{fact!r}, but their knowledge mask marks it unknown as of then "
                             f"(possible god-view leak).",
                })
    return out


def check_ripple(kb: KB, as_of):
    out = []
    removed = kb.removed_items(as_of)
    for ev in kb.events:
        t = st_int(ev.get("story_time"))
        if t is None or (as_of is not None and t > as_of):
            continue
        future = ev.get("status") in FUTURE_STATUSES
        for pre in ev.get("prerequisites", []) or []:
            if pre.get("type") != "possession":
                continue
            obj = pre.get("object")
            if obj in removed and removed[obj] < t:
                out.append({
                    "class": "ripple", "severity": "critical" if future else "high",
                    "issue": f"{'Planned ' if future else ''}event {ev.get('id')} (story_time {t}) "
                             f"depends on {name(kb,obj)}, but it was removed/destroyed at story_time "
                             f"{removed[obj]}. The dependency is now broken.",
                })
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("root", help="novel KB root directory")
    p.add_argument("--as-of", type=int, default=None, help="evaluate state only up to this story_time")
    p.add_argument("--class", dest="cls", choices=CLASSES, help="run only one violation class")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        sys.exit(2)

    kb = KB(root)
    runners = {"paradox": check_paradox, "possession": check_possession,
               "knowledge": check_knowledge, "ripple": check_ripple}
    classes = [args.cls] if args.cls else list(CLASSES)

    findings = []
    for c in classes:
        findings.extend(runners[c](kb, args.as_of))

    if args.json:
        print(json.dumps({"violations": findings, "count": len(findings)}, ensure_ascii=False, indent=2))
    else:
        if not findings:
            print(f"✓ {root} — no consistency violations found"
                  + (f" (as of story_time {args.as_of})" if args.as_of is not None else ""))
        else:
            print(f"✗ {root} — {len(findings)} violation(s):")
            order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            for v in sorted(findings, key=lambda x: order.get(x["severity"], 9)):
                print(f"  [{v['severity'].upper():8}] ({v['class']}) {v['issue']}")

    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
