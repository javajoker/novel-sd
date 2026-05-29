#!/usr/bin/env python3
"""
sync_events.py — event-graph consistency for a NovelForge KB.

`ontology.json#events` is the SINGLE SOURCE OF TRUTH for the event graph. Three
classes of file relate to it, and all three drift:

  REFERENCES — point at event IDs; every ID must resolve to an ontology event:
    - outline/structure.json     volumes[].chapters[].planned_events[]
    - memory/summaries.json      chapter_summaries[].events_covered[]
    - outline/beats/ch_*.json    events_covered[]

  MIRRORS — deterministic projections of ontology#events (+ #threads), regenerated
  wholesale, never hand-edited. The events/ shards + index.json are AUTHORITATIVE:
    - timeline/events/thr_*.json   per-thread shard {id, name, story_time, chapter,
                                                     status, participants}
    - timeline/events/index.json   by_chapter / by_story_time / by_thread + cursors
    - timeline/threads.json        thin thread mirror {id, name, pov_character,
                                                       event_ids, convergences}
    - timeline/events.json         LEGACY flat {id, story_time, thread_id, chapter_ids,
                                   status}. Optional: kept synced only while it exists,
                                   never resurrected once dropped; remove it on a
                                   migrated KB with --drop-legacy-flat.

Invariants enforced:
  1. Every referenced event ID exists in ontology#events. (Orphan refs are the bug
     that slipped past validator check #9, which deliberately skipped resolving
     planned_events during early outlining — so an event referenced by a *written*
     chapter could silently never exist in the graph.)
  2. Every ontology event belongs to exactly ONE thread (thread.event_ids); no
     thread lists an event ID that has no ontology event.
  3. The four timeline mirrors are byte-faithful projections of ontology.

What --write fixes (deterministic):
  - Orphan refs → create an ontology event STUB ("_stub": true) deriving
    story_time / thread_id / chapter_ids / status / name from the referencing
    structure chapter + prose-on-disk. A stub is a PLACEHOLDER; its name,
    projected_outcome, participants, and dependencies need a human pass (same
    contract as summaries' "_autogen").
  - Thread membership → add any event missing from its thread_id's event_ids
    (inserted in story_time order).
  - Mirrors → regenerate all four files wholesale from the (now-fixed) ontology,
    preserving each file's "_note".

What it deliberately does NOT invent (needs authorial judgement — reported, never
auto-faked):
  - Which thread an event belongs to when structure gives no thread_id (a null /
    unknown thread_id stub is created but left UNplaced and flagged).
  - Event semantics: real name, projected_outcome, dependencies, full participants.
  - chapter_ids beyond the referencing chapter (an event may legitimately span
    chapters — mismatches are reported, not rewritten).

Modes:
  --check  (default)  read-only; report inconsistency; exit 1 if any, else 0.
                      Use as a gate at the end of every write batch.
  --write             apply the deterministic fixes in place.
  --drop-legacy-flat  remove the legacy flat timeline/events.json (deletes under --write).

This pass is ALSO run automatically whenever sync_kb.py is invoked (sync_kb chains
sync_events so a single command keeps both the chapter-level mirrors and the event
graph in sync). Call sync_events.py directly only when you need --drop-legacy-flat
or want the event graph alone.

Usage:
  python sync_events.py <novel-slug>/                       # check (default)
  python sync_events.py --write <novel-slug>/               # apply fixes
  python sync_events.py --write --drop-legacy-flat <slug>/  # apply + remove flat events.json
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

CH_NUM_RE = re.compile(r"ch_0*(\d+)")
DRAFTED_STATUSES = {"drafted", "final", "partially_drafted"}

FLAT_NOTE = ("Flat mirror of ontology.json#events — {id, story_time, thread_id, "
             "chapter_ids, status}. Authoritative source is ontology.json#events.")
SHARD_NOTE = ("Per-thread mirror of ontology.json#events. Authoritative source is "
              "ontology.json#events; regenerate with sync_events.py --write.")
INDEX_NOTE = ("Index of all timeline events. Authoritative source is "
              "ontology.json#events; shards are mirrors.")
THREADS_NOTE = ("Mirror of ontology.json#threads — thin stubs (id, name, pov, "
                "event_ids, convergences). Authoritative source is ontology.json.threads[].")


def ch_num(cid: str) -> int | None:
    m = CH_NUM_RE.search(cid or "")
    return int(m.group(1)) if m else None


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def written_chapter_ids(root: Path) -> set[str]:
    return {p.stem for p in (root / "chapters").glob("ch_*.md")}


def collect_references(root: Path) -> dict[str, set[str]]:
    """eid -> {source labels} across structure / summaries / beats."""
    refs: dict[str, set[str]] = {}

    def add(eid, src):
        if eid:
            refs.setdefault(eid, set()).add(src)

    struct = load_json(root / "outline" / "structure.json")
    for vol in (struct or {}).get("volumes", []) or []:
        for ch in vol.get("chapters", []) or []:
            for ev in ch.get("planned_events") or []:
                add(ev, f"structure:{ch.get('id')}")

    summ = load_json(root / "memory" / "summaries.json")
    for s in (summ or {}).get("chapter_summaries", []) or []:
        for ev in s.get("events_covered") or []:
            add(ev, f"summary:{s.get('chapter_id')}")

    for bp in sorted(glob.glob(str(root / "outline" / "beats" / "ch_*.json"))):
        b = load_json(Path(bp))
        for ev in (b or {}).get("events_covered") or []:
            add(ev, f"beat:{Path(bp).stem}")

    return refs


def structure_index(root: Path) -> dict[str, dict]:
    struct = load_json(root / "outline" / "structure.json")
    out: dict[str, dict] = {}
    for vol in (struct or {}).get("volumes", []) or []:
        for ch in vol.get("chapters", []) or []:
            if ch.get("id"):
                out[ch["id"]] = ch
    return out


def make_stub(eid: str, ref_chapters: list[dict], written: set[str]) -> dict:
    """Build a placeholder ontology event from the structure chapter(s) that
    reference it + whether prose exists on disk. Marked "_stub": true."""
    ref_chapters = sorted(ref_chapters, key=lambda c: ch_num(c.get("id")) or 0)
    src = ref_chapters[0] if ref_chapters else {}
    chapter_ids = [c.get("id") for c in ref_chapters if c.get("id")]
    st = src.get("story_time")
    if st is None and chapter_ids:
        st = ch_num(chapter_ids[0])
    status = "drafted" if any(cid in written for cid in chapter_ids) else "planned"
    name = src.get("title") or src.get("one_line") or eid
    pov = src.get("pov_character") or src.get("pov")
    return {
        "id": eid,
        "name": name,
        "story_time": st,
        "duration": 1,
        "location": None,
        "participants": [pov] if pov else [],
        "thread_id": src.get("thread_id"),
        "dependencies": [],
        "prerequisites": [],
        "projected_outcome": src.get("one_line") or "",
        "status": status,
        "chapter_ids": chapter_ids,
        "beat_design": {},
        "_stub": True,
    }


def st_key(ev: dict):
    st = ev.get("story_time")
    return (st if isinstance(st, int) else 10**9, ev.get("id") or "")


def regen_flat(events: list[dict]) -> dict:
    return {"_note": FLAT_NOTE, "events": [
        {"id": e["id"], "story_time": e.get("story_time"),
         "thread_id": e.get("thread_id"), "chapter_ids": e.get("chapter_ids") or [],
         "status": e.get("status")}
        for e in sorted(events, key=st_key)]}


def regen_shards(events: list[dict], threads: list[dict]) -> dict[str, dict]:
    by_thread: dict[str, list[dict]] = {}
    for e in events:
        by_thread.setdefault(e.get("thread_id"), []).append(e)
    shards: dict[str, dict] = {}
    for t in threads:
        tid = t["id"]
        evs = sorted(by_thread.get(tid, []), key=st_key)
        shards[tid] = {"_note": SHARD_NOTE, "thread_id": tid, "events": [
            {"id": e["id"], "name": e.get("name"), "story_time": e.get("story_time"),
             "chapter": (e.get("chapter_ids") or [None])[0], "status": e.get("status"),
             "participants": e.get("participants") or []}
            for e in evs]}
    return shards


def regen_index(events: list[dict], threads: list[dict],
                cur_ch: int | None) -> dict:
    by_chapter: dict[str, list[str]] = {}
    by_story_time: dict[str, list[str]] = {}
    for e in sorted(events, key=st_key):
        # key on the PRIMARY chapter (chapter_ids[0]) only — same convention as the
        # shard's single `chapter` field; a multi-chapter event is filed under its
        # first chapter, not duplicated across every chapter it spans.
        chap_ids = e.get("chapter_ids") or []
        if chap_ids:
            by_chapter.setdefault(chap_ids[0], []).append(e["id"])
        st = e.get("story_time")
        if st is not None:
            by_story_time.setdefault(str(st), []).append(e["id"])
    by_thread = {t["id"]: list(t.get("event_ids", []) or []) for t in threads}
    return {
        "_note": INDEX_NOTE,
        "last_story_time": cur_ch,
        "last_chapter": f"ch_{cur_ch:03d}" if isinstance(cur_ch, int) else None,
        "by_chapter": by_chapter,
        "by_story_time": by_story_time,
        "by_thread": by_thread,
    }


def _conv_tag(c: dict) -> str:
    """Compact convergence form 'thr_other@ch_050' (story_time → ch number)."""
    st = c.get("story_time")
    where = f"ch_{st:03d}" if isinstance(st, int) else (c.get("event_id") or "?")
    return f"{c.get('with_thread')}@{where}"


def regen_threads_mirror(threads: list[dict]) -> dict:
    return {"_note": THREADS_NOTE, "threads": [
        {"id": t["id"], "name": t.get("name"), "pov_character": t.get("pov_character"),
         "event_ids": list(t.get("event_ids", []) or []),
         "convergences_with": [_conv_tag(c) for c in t.get("convergences") or []],
         "current_time": t.get("current_time")}
        for t in threads]}


def canon(obj):
    """Order-insensitive canonical form for drift comparison (drops _note)."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def sync(root: Path, write: bool = False, drop_legacy_flat: bool = False) -> int:
    """Run the event-graph consistency pass. Returns 0 (consistent / fixed),
    1 (drift, --check only), or 2 (usage). Importable so sync_kb.py can chain it."""
    root = Path(root)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    onto_path = root / "ontology.json"
    onto = load_json(onto_path)
    if not isinstance(onto, dict):
        print(f"{onto_path}: missing or unreadable ontology", file=sys.stderr)
        return 2

    events = onto.setdefault("events", [])
    threads = onto.setdefault("threads", [])
    written = written_chapter_ids(root)
    cur_ch = onto.get("source", {}).get("current_chapter")
    drift: list[str] = []
    manual: list[str] = []
    onto_changed = False

    # ---- 1. orphan references -> stubs -----------------------------------
    refs = collect_references(root)
    struct_by_id = structure_index(root)
    event_ids = {e.get("id") for e in events}
    orphans = sorted(set(refs) - event_ids)
    for eid in orphans:
        # find structure chapters that planned this event
        ref_chapters = [ch for ch in struct_by_id.values()
                        if eid in (ch.get("planned_events") or [])]
        srcs = ", ".join(sorted(refs[eid]))
        drift.append(f"orphan event {eid!r} referenced by [{srcs}] but absent from ontology#events")
        stub = make_stub(eid, ref_chapters, written)
        events.append(stub)
        onto_changed = True
        if not stub.get("thread_id"):
            manual.append(f"stub {eid!r} has no derivable thread_id — assign it to a thread by hand")
    if orphans:
        event_ids |= set(orphans)

    # ---- 2. thread membership (exactly one) ------------------------------
    threads_by_id = {t.get("id"): t for t in threads}
    membership: dict[str, list[str]] = {}
    for t in threads:
        for eid in t.get("event_ids", []) or []:
            membership.setdefault(eid, []).append(t.get("id"))
    # dangling thread members (listed in a thread but no such event)
    for eid, tids in membership.items():
        if eid not in event_ids:
            drift.append(f"thread(s) {tids} list event {eid!r} which has no ontology#event")
            manual.append(f"thread member {eid!r} ({tids}) has no event — remove or create it by hand")
    # events in >1 thread
    for eid, tids in membership.items():
        if len(tids) > 1:
            drift.append(f"event {eid!r} appears in {len(tids)} threads {tids} (must be exactly one)")
            manual.append(f"event {eid!r} is in multiple threads {tids} — pick one by hand")
    # events missing from their thread
    st_of = {e["id"]: e.get("story_time") for e in events}
    for ev in events:
        eid, tid = ev.get("id"), ev.get("thread_id")
        if not tid:
            if eid not in membership:
                drift.append(f"event {eid!r} has no thread_id and is in no thread")
                manual.append(f"event {eid!r} has null thread_id — assign a thread by hand")
            continue
        t = threads_by_id.get(tid)
        if t is None:
            drift.append(f"event {eid!r}: thread_id {tid!r} is not a declared thread")
            manual.append(f"event {eid!r} points at unknown thread {tid!r} — fix by hand")
            continue
        ids = t.setdefault("event_ids", [])
        if eid not in ids:
            drift.append(f"event {eid!r} not listed in its thread {tid!r}.event_ids")
            ids.append(eid)
            ids.sort(key=lambda x: (st_of.get(x) if isinstance(st_of.get(x), int) else 10**9, x))
            onto_changed = True

    # ---- 3. timeline mirrors (deterministic projections) -----------------
    flat_path = root / "timeline" / "events.json"
    idx_path = root / "timeline" / "events" / "index.json"
    threads_mirror_path = root / "timeline" / "threads.json"
    shard_dir = root / "timeline" / "events"

    want_flat = regen_flat(events)
    want_shards = regen_shards(events, threads)
    want_index = regen_index(events, threads, cur_ch)
    want_threads = regen_threads_mirror(threads)

    mirror_changes: list[tuple[Path, dict]] = []

    # The flat timeline/events.json is an OPTIONAL LEGACY mirror — the events/ shards
    # + index.json are authoritative. Keep it synced only while it exists; never
    # resurrect it once dropped (so a migrated KB stays migrated). --drop-legacy-flat
    # removes it outright.
    flat_exists = flat_path.exists()
    flat_drop = drop_legacy_flat and flat_exists
    if flat_drop:
        drift.append("timeline/events.json (legacy flat mirror) present — removing "
                     "(events/ shards + index.json are authoritative)")
    elif flat_exists:
        cur_flat = load_json(flat_path)
        if not isinstance(cur_flat, dict) or canon({k: v for k, v in cur_flat.items() if k != "_note"}) \
                != canon({k: v for k, v in want_flat.items() if k != "_note"}):
            drift.append("timeline/events.json (legacy flat) out of sync with ontology#events "
                         "(or drop it with --drop-legacy-flat)")
            mirror_changes.append((flat_path, want_flat))

    for tid, want in want_shards.items():
        sp = shard_dir / f"{tid}.json"
        cur = load_json(sp)
        if not isinstance(cur, dict) or canon({k: v for k, v in cur.items() if k != "_note"}) \
                != canon({k: v for k, v in want.items() if k != "_note"}):
            drift.append(f"timeline/events/{tid}.json (shard) out of sync with ontology#events")
            mirror_changes.append((sp, want))
    # shard files for threads that no longer have any thread id (stale shard)
    want_shard_files = {shard_dir / f"{tid}.json" for tid in want_shards}
    for sp in shard_dir.glob("thr_*.json"):
        if sp not in want_shard_files:
            drift.append(f"timeline/events/{sp.name} is a stale shard (thread no longer in ontology)")
            manual.append(f"stale shard {sp.name} — delete by hand or restore its thread")

    cur_idx = load_json(idx_path)
    if not isinstance(cur_idx, dict) or canon({k: v for k, v in cur_idx.items() if k != "_note"}) \
            != canon({k: v for k, v in want_index.items() if k != "_note"}):
        drift.append("timeline/events/index.json out of sync with ontology")
        mirror_changes.append((idx_path, want_index))

    cur_thm = load_json(threads_mirror_path)
    if cur_thm is not None and (not isinstance(cur_thm, dict) or
            canon({k: v for k, v in cur_thm.items() if k != "_note"})
            != canon({k: v for k, v in want_threads.items() if k != "_note"})):
        drift.append("timeline/threads.json out of sync with ontology#threads")
        mirror_changes.append((threads_mirror_path, want_threads))

    # ---- apply / report ---------------------------------------------------
    if write:
        fixed: list[str] = []
        if onto_changed:
            dump_json(onto_path, onto)
            fixed.append("ontology.json")
        if flat_drop:
            flat_path.unlink()
            fixed.append("removed timeline/events.json (legacy flat)")
        for path, data in mirror_changes:
            dump_json(path, data)
            fixed.append(str(path.relative_to(root)))
        if not drift:
            print(f"✓ {root} — event graph already consistent ({len(events)} events)")
            return 0
        print(f"✗ {root} — FIXED ({len(drift)} issue(s)):", file=sys.stderr)
        for d in drift:
            print(f"  - {d}", file=sys.stderr)
        print(f"\n  wrote: {', '.join(fixed) if fixed else '(nothing — all remaining items need manual work)'}",
              file=sys.stderr)
        if manual:
            print("\n  STILL NEEDS A HUMAN (not auto-faked):", file=sys.stderr)
            for m in manual:
                print(f"    · {m}", file=sys.stderr)
        print('\n  NOTE: created stubs carry "_stub": true — flesh out name/outcome/participants by hand.',
              file=sys.stderr)
        return 0

    if not drift:
        print(f"✓ {root} — event graph consistent ({len(events)} events, "
              f"{len(threads)} threads, mirrors in sync)")
        return 0
    print(f"✗ {root} — EVENT-GRAPH DRIFT ({len(drift)} issue(s)):", file=sys.stderr)
    for d in drift:
        print(f"  - {d}", file=sys.stderr)
    print("\n  run with --write to apply deterministic fixes "
          "(orphan→stub, thread membership, mirror regen).", file=sys.stderr)
    if manual:
        print("  some items still need a human pass (thread assignment / semantics).", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="novel KB root directory")
    ap.add_argument("--write", action="store_true",
                    help="apply fixes in place (default is read-only --check)")
    ap.add_argument("--drop-legacy-flat", action="store_true",
                    help="remove the legacy flat timeline/events.json (the events/ shards "
                         "+ index.json are authoritative); only deletes under --write")
    args = ap.parse_args()
    return sync(Path(args.root), write=args.write, drop_legacy_flat=args.drop_legacy_flat)


if __name__ == "__main__":
    sys.exit(main())
