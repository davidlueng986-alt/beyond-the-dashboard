"""Evidence tools over NASA PSI combustion investigations (data/evidence.json).

Ranking is plain BM25 over the PSI text fields. It is a retrieval aid, not a judgement of
scientific quality, and every result carries the PSI accession and link so a person or an
agent can check it.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "evidence.json"
FIELDS = {"title": 3.0, "acronym": 3.0, "keywords": 2.5, "sub_area": 2.0, "objectives": 1.0, "approach": 1.0, "hypothesis": 1.0, "impacts": .6}
STOP = set("the a an of and or to in on for with by at from as is are be this that these those was were it its into than then can may".split())
GRAVITY_WORDS = {"lunar": "partial gravity", "moon": "partial gravity", "mars": "partial gravity", "martian": "partial gravity",
                 "partial": "partial gravity", "microgravity": "microgravity", "orbit": "microgravity", "iss": "microgravity"}


def _tok(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9\-]+", s.lower()) if w not in STOP]


@lru_cache(maxsize=1)
def records() -> tuple[dict, ...]:
    return tuple(json.loads(DATA.read_text())["records"])


@lru_cache(maxsize=1)
def _index():
    docs = []
    for r in records():
        tf: Counter = Counter()
        for f, w in FIELDS.items():
            v = r.get(f)
            text = " ".join(v) if isinstance(v, list) else (v or "")
            for t in _tok(text):
                tf[t] += w
        docs.append(tf)
    n = len(docs)
    df = Counter(t for d in docs for t in d)
    idf = {t: math.log(1 + (n - c + .5) / (c + .5)) for t, c in df.items()}
    avg = sum(sum(d.values()) for d in docs) / n
    return docs, idf, avg


def _brief(r: dict) -> dict:
    return {"id": r["id"], "acronym": r["acronym"], "title": r["title"], "gravity": r["gravity"], "platform": r["platform"],
            "sub_area": r["sub_area"], "source": r["source"]["url"]}


def get(record_id: str) -> dict:
    for r in records():
        if r["id"].lower() == record_id.lower() or (r["acronym"] or "").lower() == record_id.lower():
            return r
    raise KeyError(f"No PSI combustion record '{record_id}'. Call evidence_search to find valid ids (format PSI-<number>).")


def search(query: str, gravity: str | None = None, k: int = 5) -> dict:
    """Rank PSI combustion investigations for a question or a cabin condition."""
    docs, idf, avg = _index()
    q = _tok(query)
    want = gravity or next((g for w, g in GRAVITY_WORDS.items() if w in q), None)
    scored = []
    for r, d in zip(records(), docs):
        dl = sum(d.values()); s = 0.0; hit = []
        for t in set(q):
            if t in d:
                f = d[t]; s += idf.get(t, 0) * f * 2.2 / (f + 1.2 * (.25 + .75 * dl / avg)); hit.append(t)
        if s > 0:
            notes = []
            if want == "partial gravity":
                notes.append("tested in " + r["gravity"] + ", not partial gravity: applying it to the Moon or Mars is an extrapolation")
            elif want and want not in r["gravity"]:
                notes.append(f"tested in {r['gravity']}, query asks about {want}")
            scored.append((s, r, hit, notes))
    scored.sort(key=lambda x: -x[0])
    top = scored[:k]
    return {
        "query": query,
        "ranking_method": "BM25 over PSI text fields; relevance only, not a quality rating",
        "results": [dict(_brief(r), rank=i + 1, score=round(s, 2), matched_terms=sorted(h), applicability_notes=n,
                         oxygen_mentions=r["oxygen_mentions"][:2]) for i, (s, r, h, n) in enumerate(top)],
        "next": None if top else "No match. Try broader words such as 'flame spread', 'solid fuel', 'smoke', 'extinction'.",
    }


def compare(ids: list[str]) -> dict:
    rs = [get(i) for i in ids]
    fields = ["acronym", "title", "gravity", "platform", "hardware", "sub_area", "start", "end", "keywords"]
    rows = {f: [r.get(f) for r in rs] for f in fields}
    same = [f for f, v in rows.items() if len({json.dumps(x) for x in v}) == 1]
    return {"ids": [r["id"] for r in rs], "fields": rows, "same": same, "different": [f for f in fields if f not in same],
            "oxygen_mentions": {r["id"]: r["oxygen_mentions"] for r in rs}, "sources": {r["id"]: r["source"]["url"] for r in rs}}


def gaps() -> dict:
    """What the PSI combustion record does not cover."""
    rs = records()
    by = Counter(r["gravity"] for r in rs)
    return {
        "records": len(rs),
        "by_gravity": dict(by),
        "partial_gravity_records": [r["id"] for r in rs if "reduced" in r["gravity"] or "partial" in r["gravity"]],
        "statement": "No PSI combustion investigation was run in partial (lunar or Martian) gravity; conclusions for a lunar cabin extrapolate from microgravity and 1 g work.",
        "records_mentioning_oxygen": [r["id"] for r in rs if r["oxygen_mentions"]],
    }
