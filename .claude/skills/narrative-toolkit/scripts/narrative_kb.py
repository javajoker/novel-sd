#!/usr/bin/env python3
"""
narrative_kb.py — Shared loader + "as-of story-time" folding engine for a NovelForge
narrative knowledge base. Imported by view_kb.py, build_profile.py, and search_novel.py.

Pure standard library. Reads the KB layout defined by the narrative-ontology skill and
exposes time-aware queries: the state of the world *as of* any chapter / story-time.

Folding rules (best-effort, documented):
  - inventory: T=0 baseline (characters/<id>.json initial_state.inventory) + chapter
    deltas (characters/states/<id>.json inventory_delta) with story_time <= t.
  - relations: an edge holds at t iff valid_from_chapter <= t and
    (valid_to_chapter is None or valid_to_chapter > t).
  - status: injuries/buffs accumulate; a recovery/cleansing/healed delta clears a
    matching prior injury by keyword; death persists.
  - psychology: latest non-null fields win.
  - knowledge: initial_state.knowledge ∪ knowledge_gained deltas with story_time <= t.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

STOP_STATUS_CLEAR = {"recovery", "cleansing", "healed"}


def _load(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _int(v, default=None):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _item_key(it):
    return it.get("item") if isinstance(it, dict) else it


class NarrativeKB:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        g = _load(self.root / "ontology.json") or {}
        self.source = g.get("source", {})
        self.entities = {e["id"]: e for e in g.get("entities", []) if "id" in e}
        self.relations = g.get("relations", []) or []
        self.events = g.get("events", []) or []
        self.threads = g.get("threads", []) or []
        self.world_rules = g.get("world_rules", []) or []
        self.themes = g.get("themes", []) or []
        self.outline = _load(self.root / "outline" / "structure.json") or {}
        self.summaries = _load(self.root / "memory" / "summaries.json") or {}
        self.plot_threads = (_load(self.root / "memory" / "plot_threads.json") or {}).get("plot_hooks", [])
        self.calendar = _load(self.root / "timeline" / "calendar.json") or {}
        self._profiles_cache: dict = {}
        self._states_cache: dict = {}
        self._masks_cache: dict = {}

    # ---- names ----
    def name(self, eid: str) -> str:
        e = self.entities.get(eid)
        return e.get("canonical_name", eid) if e else eid

    # ---- raw per-character files (cached) ----
    def profile(self, char_id: str) -> dict:
        if char_id not in self._profiles_cache:
            self._profiles_cache[char_id] = _load(self.root / "characters" / f"{char_id}.json") or {}
        return self._profiles_cache[char_id]

    def state_snapshots(self, char_id: str) -> list:
        if char_id not in self._states_cache:
            data = _load(self.root / "characters" / "states" / f"{char_id}.json") or {}
            self._states_cache[char_id] = sorted(data.get("states", []) or [],
                                                 key=lambda s: _int(s.get("story_time"), 0))
        return self._states_cache[char_id]

    def mask_file(self, char_id: str) -> list:
        if char_id not in self._masks_cache:
            data = _load(self.root / "masks" / f"{char_id}.json") or {}
            self._masks_cache[char_id] = sorted(data.get("knowledge_at", []) or [],
                                                key=lambda k: _int(k.get("story_time"), 0))
        return self._masks_cache[char_id]

    # ---- as-of queries ----
    def relations_as_of(self, t: int) -> list:
        out = []
        for r in self.relations:
            vf = _int(r.get("valid_from_chapter"))
            vt = _int(r.get("valid_to_chapter"))
            if vf is None or vf > t:
                continue
            if vt is not None and vt <= t:
                continue
            out.append(r)
        return out

    def events_up_to(self, t: int) -> list:
        return sorted([e for e in self.events if _int(e.get("story_time")) is not None
                       and _int(e.get("story_time")) <= t],
                      key=lambda e: _int(e.get("story_time"), 0))

    def character_state_as_of(self, char_id: str, t: int) -> dict:
        prof = self.profile(char_id)
        init = prof.get("initial_state", {}) or {}
        # inventory
        inv = set(_item_key(it) for it in (init.get("inventory") or []) if _item_key(it))
        # status (folded), psychology, location, knowledge
        status_active: dict = {}
        psychology = dict(init.get("psychology") or {})
        location = init.get("location")
        knowledge = set()
        for k in (init.get("knowledge") or []):
            fact = k.get("fact") if isinstance(k, dict) else k
            if fact:
                knowledge.add(fact)
        for snap in self.state_snapshots(char_id):
            if _int(snap.get("story_time"), 0) > t:
                break
            if snap.get("location"):
                location = snap["location"]
            for d in (snap.get("inventory_delta") or []):
                key = _item_key(d)
                if not key:
                    continue
                if d.get("action") == "add":
                    inv.add(key)
                elif d.get("action") in ("remove", "destroyed"):
                    inv.discard(key)
            for s in (snap.get("status") or []):
                typ = s.get("type")
                desc = (s.get("desc") or "").lower()
                if typ in STOP_STATUS_CLEAR:
                    # clear any active injury/debuff whose desc overlaps
                    for key in list(status_active):
                        if any(w in key for w in desc.split()) or any(w in desc for w in key.split()):
                            del status_active[key]
                elif typ == "psychology":
                    pass  # captured via psychology dict below
                else:
                    status_active[desc or typ] = s
            if snap.get("psychology"):
                psychology.update(snap["psychology"])
            for kg in (snap.get("knowledge_gained") or []):
                fact = kg.get("fact") if isinstance(kg, dict) else kg
                if fact:
                    knowledge.add(fact)
        return {
            "location": location,
            "inventory": sorted(inv),
            "status": list(status_active.values()),
            "psychology": psychology,
            "knowledge": sorted(knowledge),
        }

    def mask_as_of(self, char_id: str, t: int) -> dict:
        known, unknown, beliefs, perception = set(), set(), [], {}
        for k in self.mask_file(char_id):
            if _int(k.get("story_time"), 0) > t:
                break
            known = set(k.get("facts_known", []) or [])
            unknown = set(k.get("facts_unknown", []) or [])
            beliefs = k.get("beliefs_held", []) or []
            perception = k.get("perception", {}) or {}
        return {"facts_known": sorted(known), "facts_unknown": sorted(unknown),
                "beliefs_held": beliefs, "perception": perception}

    def summaries_up_to(self, t: int) -> dict:
        chs = [c for c in (self.summaries.get("chapter_summaries") or [])
               if _int(c.get("story_time"), 0) <= t]
        chs.sort(key=lambda c: _int(c.get("story_time"), 0))
        return {
            "novel": self.summaries.get("novel_summary", ""),
            "volumes": self.summaries.get("volume_summaries", []),
            "chapters": chs,
        }

    def open_threads(self) -> list:
        return [h for h in self.plot_threads if h.get("status") in ("open", "dormant", "at_risk")]

    # ---- graph expansion (for KAG) ----
    def neighbors(self, entity_id: str, t: int | None = None) -> set:
        """Entity IDs directly linked to entity_id via relations (as-of t if given) or
        via co-participation in events."""
        out = set()
        rels = self.relations_as_of(t) if t is not None else self.relations
        for r in rels:
            if r.get("subject") == entity_id and r.get("object") in self.entities:
                out.add(r["object"])
            elif r.get("object") == entity_id and r.get("subject") in self.entities:
                out.add(r["subject"])
        evs = self.events_up_to(t) if t is not None else self.events
        for e in evs:
            parts = e.get("participants") or []
            if entity_id in parts:
                out.update(p for p in parts if p != entity_id and p in self.entities)
                if e.get("location") in self.entities:
                    out.add(e["location"])
        out.discard(entity_id)
        return out

    # ---- chapter prose ----
    def chapter_files(self) -> list:
        d = self.root / "chapters"
        if not d.is_dir():
            return []
        out = []
        ch_time = {}
        for vol in (self.outline.get("volumes") or []):
            for ch in (vol.get("chapters") or []):
                ch_time[ch.get("id")] = _int(ch.get("story_time"), 0)
        for p in sorted(d.glob("*.md")):
            out.append({"chapter_id": p.stem, "path": p, "story_time": ch_time.get(p.stem, 0)})
        return out

    def chapter_text(self, chapter_id: str) -> str:
        p = self.root / "chapters" / f"{chapter_id}.md"
        try:
            return p.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""


# ----------------------- shared lexical / TF-IDF helpers -----------------------

# Latin/digit words, and CJK ideograph runs handled separately. Chinese prose has no
# spaces, so a single regex run would collapse "叶凡走进黑森林" into one useless token.
# We therefore emit Latin tokens + CJK unigrams + CJK bigrams (overlapping), which gives
# TF-IDF enough granularity to match queries against space-less Chinese text.
_LATIN = re.compile(r"[A-Za-z0-9_]+")
_CJK_RUN = re.compile(r"[㐀-䶿一-鿿豈-﫿]+")


def tokenize(text: str) -> list:
    text = (text or "").lower()
    toks = _LATIN.findall(text)
    for run in _CJK_RUN.findall(text):
        toks.extend(run)                                   # unigrams
        toks.extend(run[i:i + 2] for i in range(len(run) - 1))  # overlapping bigrams
    return toks


def estimate_tokens(text: str) -> int:
    """Rough LLM-token estimate that is sane for both English and CJK. CJK chars are
    ~1 token each (often less with modern tokenizers, but budget conservatively); other
    text averages ~4 chars/token."""
    if not text:
        return 0
    cjk_chars = sum(len(r) for r in _CJK_RUN.findall(text))
    other = len(text) - cjk_chars
    return int(cjk_chars * 1.0 + other / 4)


def tf(tokens: list) -> dict:
    out: dict = {}
    for w in tokens:
        out[w] = out.get(w, 0) + 1
    return out


def build_idf(docs_tokens: list) -> dict:
    import math
    n = len(docs_tokens) or 1
    df: dict = {}
    for toks in docs_tokens:
        for w in set(toks):
            df[w] = df.get(w, 0) + 1
    return {w: math.log((n + 1) / (c + 1)) + 1.0 for w, c in df.items()}


def cosine(qvec: dict, dvec: dict) -> float:
    import math
    if not qvec or not dvec:
        return 0.0
    dot = sum(v * dvec.get(w, 0.0) for w, v in qvec.items())
    qn = math.sqrt(sum(v * v for v in qvec.values()))
    dn = math.sqrt(sum(v * v for v in dvec.values()))
    return dot / (qn * dn) if qn and dn else 0.0


def tfidf_vec(tokens: list, idf: dict) -> dict:
    counts = tf(tokens)
    return {w: c * idf.get(w, 1.0) for w, c in counts.items()}
