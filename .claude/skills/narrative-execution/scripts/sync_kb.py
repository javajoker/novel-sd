#!/usr/bin/env python3
"""
sync_kb.py — Phase-C deterministic-mirror sync for a NovelForge KB.

Phase C of narrative-execution has ~12 steps. Several of them are *deterministic
mirrors* of canon (the chapter prose + beat sheets) — they carry no authorial
judgement and were getting silently skipped batch-after-batch, leaving the
calendar, cursors, structure statuses, and memory summaries frozen dozens of
chapters behind the prose. This script regenerates exactly those deterministic
mirrors from canon so they can never drift again.

It does NOT invent story truth. It only propagates facts already present in:
  - chapters/ch_*.md          (the authoritative prose; `siege_day N` = world clock)
  - outline/beats/ch_*.json   (title, pov, siege_day, beats, key_changes, events_covered)

What it syncs (the deterministic subset of Phase C C-3/C-5/C-6/C-7):
  1. ontology.json   → source.current_chapter; events_covered → status planned→drafted
  2. timeline/calendar.json → current_chapter, current_story_time,
                              chapter_to_story_time, chapter_to_world_day (siege_day)
  3. outline/structure.json → chapters with prose: status planned/beats_ready → drafted
  4. memory/summaries.json  → SKELETON chapter_summaries for any chapter missing one
                              (marked "_autogen": true — enrich by hand later)

It then CHAINS sync_events.py (the event-graph pass) so one command keeps both the
chapter-level mirrors and the event graph in sync: orphan-event refs → ontology
stubs, one-thread membership, and the timeline event mirrors (events/ shards +
index.json + threads.json) regenerated from ontology. The combined exit code is
non-zero if EITHER pass reports drift in --check mode.

What it deliberately does NOT do (needs human/authorial judgement — left to the
writer, never auto-faked):
  - memory/plot_threads.json occurrences (which hook a scene advances)
  - relation edges, world_rules, convergences, ripple resolution
  - rewriting existing hand-written summaries (only fills MISSING ones)
  - event semantics behind a sync_events stub (name/outcome/participants)

Modes:
  --check  (default)  read-only; report drift; exit 1 if anything is stale, else 0.
                      Use this as a gate at the end of every write batch.
  --write             apply the deterministic fixes in place.

Usage:
  python sync_kb.py <novel-slug>/            # check kb + event graph (default)
  python sync_kb.py --write <novel-slug>/    # apply fixes to both
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# sync_events.py lives beside this script; chain it so one command keeps both the
# chapter-level mirrors (here) and the event graph (there) in sync.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_events  # noqa: E402

SIEGE_RE = re.compile(r"siege_day\s+(\d+)")
CH_NUM_RE = re.compile(r"ch_0*(\d+)")
# Canonical terminal statuses for a chapter that has prose on disk. Anything else
# on a written chapter (planned, beats_ready, the off-vocabulary "written", or None)
# is normalized to "drafted" so the status vocabulary stays consistent + queryable.
DRAFTED_STATUSES = {"drafted", "final", "partially_drafted"}


def chap_num(chapter_id: str) -> int | None:
    m = CH_NUM_RE.search(chapter_id or "")
    return int(m.group(1)) if m else None


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def discover_chapters(root: Path) -> list[tuple[int, str, Path]]:
    out = []
    for p in sorted((root / "chapters").glob("ch_*.md")):
        n = chap_num(p.stem)
        if n is not None:
            out.append((n, p.stem, p))
    return sorted(out)


def parse_siege_day(prose_path: Path, beat: dict | None) -> int | None:
    """Authoritative clock = first `siege_day N` in prose; fall back to beat field."""
    try:
        m = SIEGE_RE.search(prose_path.read_text(encoding="utf-8"))
        if m:
            return int(m.group(1))
    except OSError:
        pass
    if beat and isinstance(beat.get("siege_day"), int):
        return beat["siege_day"]
    return None


def beat_for(root: Path, chapter_id: str) -> dict | None:
    return load_json(root / "outline" / "beats" / f"{chapter_id}.json")


def skeleton_summary(chapter_id: str, num: int, beat: dict | None,
                     struct_ch: dict | None, siege_day: int | None) -> dict:
    title = (beat or {}).get("title") or (struct_ch or {}).get("title") or chapter_id
    one_line = (struct_ch or {}).get("one_line")
    beats = (beat or {}).get("beats") or []
    labels = [b.get("label", "").strip() for b in beats if b.get("label")]
    synopsis = "；".join(labels) if labels else (one_line or "")
    if siege_day is not None and synopsis:
        synopsis = f"siege_day {siege_day}：{synopsis}"
    pov = (beat or {}).get("pov") or (struct_ch or {}).get("pov_character")
    events = (beat or {}).get("events_covered") or (struct_ch or {}).get("planned_events") or []
    tags = list(((beat or {}).get("key_changes") or {}).keys())
    active = [pov] if pov else []
    return {
        "chapter_id": chapter_id,
        "story_time": num,
        "title": title,
        "logline": one_line or (labels[0] if labels else ""),
        "synopsis": synopsis,
        "active_entities": active,
        "events_covered": events,
        "tags": tags,
        "_autogen": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="novel KB root directory")
    ap.add_argument("--write", action="store_true",
                    help="apply fixes in place (default is read-only --check)")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    chapters = discover_chapters(root)
    if not chapters:
        print("no chapters found — chapter-level mirrors skipped", file=sys.stderr)
        print("\n— event-graph sync (sync_events) —", file=sys.stderr)
        return sync_events.sync(root, write=args.write)
    max_num = chapters[-1][0]
    drift: list[str] = []
    fixed: list[str] = []

    # ---- 1. ontology.json -------------------------------------------------
    onto_path = root / "ontology.json"
    onto = load_json(onto_path)
    onto_changed = False
    covered_event_ids: set[str] = set()
    for num, cid, _ in chapters:
        b = beat_for(root, cid)
        for ev in (b or {}).get("events_covered") or []:
            covered_event_ids.add(ev)
    if isinstance(onto, dict):
        cur = onto.get("source", {}).get("current_chapter")
        if cur != max_num:
            drift.append(f"ontology.source.current_chapter={cur} but latest chapter is {max_num}")
            onto.setdefault("source", {})["current_chapter"] = max_num
            onto_changed = True
        for ev in onto.get("events", []):
            if ev.get("id") in covered_event_ids and ev.get("status") in ("planned", None):
                drift.append(f"event {ev.get('id')} appears in a written chapter but status={ev.get('status')}")
                ev["status"] = "drafted"
                onto_changed = True

    # ---- 2. timeline/calendar.json ---------------------------------------
    cal_path = root / "timeline" / "calendar.json"
    cal = load_json(cal_path)
    cal_changed = False
    if isinstance(cal, dict):
        if cal.get("current_chapter") != max_num:
            drift.append(f"calendar.current_chapter={cal.get('current_chapter')} but latest is {max_num}")
            cal["current_chapter"] = max_num
            cal_changed = True
        if cal.get("current_story_time") != max_num:
            cal["current_story_time"] = max_num
            cal_changed = True
        cts = cal.setdefault("chapter_to_story_time", {})
        cwd = cal.setdefault("chapter_to_world_day", {})
        missing_cts = 0
        for num, cid, ppath in chapters:
            if cts.get(cid) != num:
                cts[cid] = num
                missing_cts += 1
                cal_changed = True
            sd = parse_siege_day(ppath, beat_for(root, cid))
            if sd is not None:
                entry = cwd.get(cid)
                want_note = ((beat_for(root, cid) or {}).get("title")) or ""
                if not entry or entry.get("siege_day") != sd or entry.get("story_time") != num:
                    cwd[cid] = {"story_time": num, "siege_day": sd,
                                "note": (entry or {}).get("note") or want_note}
                    cal_changed = True
        if missing_cts:
            drift.append(f"calendar.chapter_to_story_time missing/wrong for {missing_cts} chapter(s)")

    # ---- 3. outline/structure.json ---------------------------------------
    struct_path = root / "outline" / "structure.json"
    struct = load_json(struct_path)
    struct_changed = False
    struct_by_id: dict[str, dict] = {}
    if isinstance(struct, dict):
        for vol in struct.get("volumes", []):
            for ch in vol.get("chapters", []):
                struct_by_id[ch.get("id")] = ch
        written_ids = {cid for _, cid, _ in chapters}
        stale_status = 0
        for cid in written_ids:
            ch = struct_by_id.get(cid)
            if ch and ch.get("status") not in DRAFTED_STATUSES:
                ch["status"] = "drafted"
                stale_status += 1
                struct_changed = True
        if stale_status:
            drift.append(f"structure: {stale_status} written chapter(s) not marked drafted "
                         f"(planned/beats_ready/written/none → drafted)")

    # ---- 4. memory/summaries.json ----------------------------------------
    sum_path = root / "memory" / "summaries.json"
    summ = load_json(sum_path)
    summ_changed = False
    if isinstance(summ, dict):
        existing = {e.get("chapter_id") for e in summ.get("chapter_summaries", [])}
        missing = [(n, c) for n, c, _ in chapters if c not in existing]
        if missing:
            drift.append(f"summaries: {len(missing)} chapter(s) have no entry "
                         f"({missing[0][1]}..{missing[-1][1]})")
            cs = summ.setdefault("chapter_summaries", [])
            sd_by_id = {}
            for num, cid, ppath in chapters:
                sd_by_id[cid] = parse_siege_day(ppath, beat_for(root, cid))
            for num, cid in missing:
                cs.append(skeleton_summary(cid, num, beat_for(root, cid),
                                           struct_by_id.get(cid), sd_by_id.get(cid)))
            cs.sort(key=lambda e: chap_num(e.get("chapter_id", "")) or 0)
            summ_changed = True

    # ---- 5. plot_threads.json (report only — needs authorial judgement) ---
    pt = load_json(root / "memory" / "plot_threads.json")
    if isinstance(pt, dict):
        empty = [h.get("id") or h.get("hook_id")
                 for h in pt.get("plot_hooks", [])
                 if not (h.get("occurrences") or [])]
        if empty:
            drift.append(f"plot_threads: {len(empty)} open hook(s) have ZERO recorded "
                         f"occurrences — needs manual tracking, not auto-synced: "
                         f"{', '.join(str(x) for x in empty)}")

    # ---- apply / report ---------------------------------------------------
    if args.write:
        if onto_changed:
            dump_json(onto_path, onto); fixed.append("ontology.json")
        if cal_changed:
            dump_json(cal_path, cal); fixed.append("timeline/calendar.json")
        if struct_changed:
            dump_json(struct_path, struct); fixed.append("outline/structure.json")
        if summ_changed:
            dump_json(sum_path, summ); fixed.append("memory/summaries.json (skeletons)")

    if not drift:
        print(f"✓ {root} — KB mirrors in sync with {len(chapters)} chapters (latest ch_{max_num:03d})")
        rc_kb = 0
    else:
        head = "FIXED" if args.write else "DRIFT DETECTED"
        print(f"✗ {root} — {head} ({len(drift)} issue(s)):", file=sys.stderr)
        for d in drift:
            print(f"  - {d}", file=sys.stderr)
        if args.write:
            print(f"\n  wrote: {', '.join(fixed) if fixed else '(deterministic mirrors already current; '
                  'remaining items need manual work)'}", file=sys.stderr)
            print("  NOTE: auto-generated summaries carry \"_autogen\": true — enrich by hand.",
                  file=sys.stderr)
            rc_kb = 0
        else:
            print("\n  run with --write to apply the deterministic fixes "
                  "(summaries/threads still need a human pass).", file=sys.stderr)
            rc_kb = 1

    # ---- chain the event-graph sync (single entry point) ------------------
    # sync_events re-reads ontology.json from disk, so in --write mode it sees the
    # status/current_chapter advances we just wrote and regenerates the timeline
    # event mirrors on top of them.
    print("\n— event-graph sync (sync_events) —", file=sys.stderr)
    rc_ev = sync_events.sync(root, write=args.write)
    return rc_kb or rc_ev


if __name__ == "__main__":
    sys.exit(main())
