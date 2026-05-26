#!/usr/bin/env python3
"""
search_novel.py — Two-stage semantic search inside a novel: KB-first, then KAG.

The design (per the NovelForge memory phase):
  STAGE 1 — KB-first. Search the structured ontology (entities, relations, events,
            world-rules, chapter summaries). Precise, cheap, and it tells you WHICH
            entities/threads the question is really about.
  STAGE 2 — KAG (Knowledge-Augmented Generation retrieval) over the sub-chapter prose.
            Graph-expand from the Stage-1 entity hits (related entities / co-events),
            scope the prose to a chapter-masked view (--as-of N, and/or only chapters
            where the matched entities are active), then rank passages by TF-IDF cosine.
            The KB hits become the "knowledge" that augments and focuses the text
            retrieval — so answers stay grounded and you never scan the whole 2M-word
            manuscript blindly.

Scoring is pure-stdlib TF-IDF cosine (no external deps), which is a solid offline
default. To upgrade to dense embeddings, replace `tfidf_vec`/`cosine` in narrative_kb.py
with an embedding backend — the two-stage structure is unchanged.

Usage:
  python search_novel.py <novel-slug>/ "why does the villain attack the city?"
  python search_novel.py <novel-slug>/ "Ye Fan and the sword" --as-of 50 --topk 5
  python search_novel.py <novel-slug>/ "betrayal" --kb-only
  python search_novel.py <novel-slug>/ "betrayal" --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from narrative_kb import (NarrativeKB, _int, tokenize, build_idf,  # noqa: E402
                          tfidf_vec, cosine)


# ----------------------------- STAGE 1: KB-first -----------------------------

def search_kb(kb: NarrativeKB, query: str, limit: int = 8) -> dict:
    q = set(tokenize(query))

    def overlap(text: str) -> float:
        toks = set(tokenize(text))
        if not toks:
            return 0.0
        return len(q & toks) / (len(q) ** 0.5 or 1)

    ent_hits = []
    for eid, e in kb.entities.items():
        blob = " ".join([e.get("canonical_name", ""), " ".join(e.get("aliases") or []),
                         e.get("description", ""), e.get("subtype", "") or ""])
        s = overlap(blob)
        if s > 0:
            ent_hits.append({"id": eid, "name": e.get("canonical_name"),
                             "type": e.get("type"), "subtype": e.get("subtype"), "score": round(s, 3)})
    ent_hits.sort(key=lambda x: -x["score"])

    evt_hits = []
    for e in kb.events:
        s = overlap(" ".join([e.get("name", ""), e.get("description", ""), e.get("context", "")]))
        if s > 0:
            evt_hits.append({"id": e.get("id"), "name": e.get("name"),
                             "story_time": _int(e.get("story_time"), 0), "score": round(s, 3)})
    evt_hits.sort(key=lambda x: -x["score"])

    rel_hits = []
    for r in kb.relations:
        blob = " ".join([r.get("predicate", ""), kb.name(r.get("subject")),
                         kb.name(r.get("object")), str((r.get("properties") or {}).get("reason", "")),
                         r.get("context", "")])
        s = overlap(blob)
        if s > 0:
            rel_hits.append({"subject": kb.name(r.get("subject")), "predicate": r.get("predicate"),
                             "object": kb.name(r.get("object")),
                             "since": r.get("valid_from_chapter"),
                             "properties": r.get("properties", {}), "score": round(s, 3)})
    rel_hits.sort(key=lambda x: -x["score"])

    rule_hits = []
    for r in kb.world_rules:
        s = overlap(" ".join([str(r.get("source")), str(r.get("relation")),
                              str(r.get("target")), r.get("note", "")]))
        if s > 0:
            rule_hits.append({"triple": f"({r.get('source')})-[{r.get('relation')}]->({r.get('target')})",
                              "note": r.get("note", ""), "score": round(s, 3)})
    rule_hits.sort(key=lambda x: -x["score"])

    return {"entities": ent_hits[:limit], "events": evt_hits[:limit],
            "relations": rel_hits[:limit], "world_rules": rule_hits[:limit]}


# ----------------------------- STAGE 2: KAG over prose -----------------------------

def chapters_for_entities(kb: NarrativeKB, entity_ids: set, as_of) -> set:
    """Chapters where any of these entities is active (from summaries.active_entities or
    by name appearing in prose), optionally capped at story-time as_of."""
    want = set(entity_ids)
    want_names = {kb.name(e).lower() for e in entity_ids}
    out = set()
    for c in (kb.summaries.get("chapter_summaries") or []):
        if as_of is not None and _int(c.get("story_time"), 0) > as_of:
            continue
        if set(c.get("active_entities") or []) & want:
            out.add(c.get("chapter_id"))
    for cf in kb.chapter_files():
        if as_of is not None and cf["story_time"] > as_of:
            continue
        low = kb.chapter_text(cf["chapter_id"]).lower()
        if any(n and n in low for n in want_names):
            out.add(cf["chapter_id"])
    return out


def split_paragraphs(text: str) -> list:
    paras, cur = [], []
    for line in text.splitlines():
        if line.strip():
            cur.append(line.strip())
        elif cur:
            paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    # drop markdown headers-only paragraphs
    return [p for p in paras if not (p.startswith("#") and len(p) < 80)]


def kag_search(kb: NarrativeKB, query: str, kb_hits: dict, as_of, topk: int,
               expand: bool) -> list:
    # seed entities from Stage 1
    seed = {h["id"] for h in kb_hits["entities"][:5]}
    if expand:
        for eid in list(seed):
            seed |= kb.neighbors(eid, as_of)
    scoped = chapters_for_entities(kb, seed, as_of) if seed else None

    # corpus: paragraphs of in-scope chapters (or all if no scope)
    candidates = []  # (chapter_id, story_time, para)
    for cf in kb.chapter_files():
        if as_of is not None and cf["story_time"] > as_of:
            continue
        if scoped is not None and cf["chapter_id"] not in scoped:
            continue
        for para in split_paragraphs(kb.chapter_text(cf["chapter_id"])):
            candidates.append((cf["chapter_id"], cf["story_time"], para))

    # fall back to summary synopses if no prose drafted yet
    used_summaries = False
    if not candidates:
        used_summaries = True
        for c in (kb.summaries.get("chapter_summaries") or []):
            if as_of is not None and _int(c.get("story_time"), 0) > as_of:
                continue
            text = " ".join([c.get("logline", ""), c.get("synopsis", "")])
            if text.strip():
                candidates.append((c.get("chapter_id"), _int(c.get("story_time"), 0), text))

    if not candidates:
        return []

    docs_tokens = [tokenize(p) for _, _, p in candidates]
    idf = build_idf(docs_tokens)
    qvec = tfidf_vec(tokenize(query), idf)

    scored = []
    for (cid, t, para), toks in zip(candidates, docs_tokens):
        s = cosine(qvec, tfidf_vec(toks, idf))
        if s > 0:
            snippet = para if len(para) <= 320 else para[:317] + "..."
            scored.append({"chapter_id": cid, "story_time": t, "score": round(s, 4),
                           "source": "summary" if used_summaries else "prose",
                           "snippet": snippet})
    scored.sort(key=lambda x: -x["score"])
    return scored[:topk]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("query")
    ap.add_argument("--as-of", type=int, default=None, help="only search the world up to this story-time")
    ap.add_argument("--topk", type=int, default=6, help="passages to return from Stage 2")
    ap.add_argument("--kb-only", action="store_true", help="Stage 1 only (structured KB)")
    ap.add_argument("--no-expand", action="store_true", help="skip graph expansion of KB hits")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr); sys.exit(2)
    kb = NarrativeKB(root)

    kb_hits = search_kb(kb, args.query)
    passages = [] if args.kb_only else kag_search(kb, args.query, kb_hits, args.as_of,
                                                  args.topk, expand=not args.no_expand)
    result = {"query": args.query, "as_of": args.as_of, "kb": kb_hits, "passages": passages}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2)); return

    print(f"🔎 “{args.query}”" + (f"  (as of story-time {args.as_of})" if args.as_of is not None else ""))
    print("\n── Stage 1: knowledge base ──")
    if kb_hits["entities"]:
        print("  Entities: " + ", ".join(f"{h['name']} ({h['score']})" for h in kb_hits["entities"]))
    if kb_hits["events"]:
        print("  Events:   " + "; ".join(f"{h['name']} @t{h['story_time']} ({h['score']})" for h in kb_hits["events"]))
    if kb_hits["relations"]:
        print("  Relations:")
        for h in kb_hits["relations"][:5]:
            print(f"    {h['subject']} --{h['predicate']}--> {h['object']} "
                  f"(since ch{h['since']}) {h.get('properties', {})}")
    if kb_hits["world_rules"]:
        print("  Rules:    " + "; ".join(h["triple"] for h in kb_hits["world_rules"]))
    if not any(kb_hits.values()):
        print("  (no structured matches)")

    if not args.kb_only:
        print("\n── Stage 2: KAG passages (graph-scoped prose) ──")
        if not passages:
            print("  (no prose/summary matches in scope)")
        for pgi in passages:
            print(f"  [{pgi['source']}] {pgi['chapter_id']} (t={pgi['story_time']}, score={pgi['score']})")
            print(f"      {pgi['snippet']}")


if __name__ == "__main__":
    main()
