"""Fetch NASA PSI combustion investigations and build data/evidence.json.

Source: NASA Physical Sciences Informatics (PSI) repository, https://psi.nasa.gov/physci/repo/
The PSI web app reads the same public search endpoint used here.

    python data/fetch_psi.py            # refresh raw records from PSI, then rebuild evidence.json
    python data/fetch_psi.py --offline  # rebuild evidence.json from data/psi_combustion_raw.json

Nothing in evidence.json is invented: every field is copied from a PSI record, and every record
keeps its PSI accession number and a link back to its PSI page. Fields PSI leaves empty stay empty.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "psi_combustion_raw.json"
OUT = HERE / "evidence.json"
API = "https://psi.nasa.gov/geode-py/ws/repo/search"
PAGE = "https://psi.nasa.gov/physci/repo/data/investigations/{acc}"
QUERIES = ["combustion", "fire", "flame", "smoke", "spacecraft fire safety"]
TEXT_FIELDS = ["Objectives", "Approach", "Hypothesis", "Research Impacts/Earth Benefits"]


def fetch_raw() -> list[dict]:
    found: dict[str, dict] = {}
    for q in QUERIES:
        url = API + "?" + urllib.parse.urlencode({"q": q, "size": 300, "from": 0})
        with urllib.request.urlopen(url, timeout=60) as r:
            hits = json.load(r)["hits"]["hits"]
        for h in hits:
            src = h["_source"]
            if "combustion" in (src.get("Research Area") or "").lower():
                found[src["Accession"]] = src
        time.sleep(0.5)
    return sorted(found.values(), key=lambda a: int(a["Accession"].split("-")[1]))


def clean(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def gravity_of(rec: dict) -> str:
    """Gravity level as PSI's own Project Type states it."""
    pt = clean(rec.get("Project Type")).lower()
    if "microgravity" in pt:
        return "microgravity"
    if "reduced gravity" in pt:
        return "reduced gravity"
    if "ground" in pt:
        return "ground (1 g analysis)"
    return "not stated"


def oxygen_mentions(text: str) -> list[str]:
    """Sentences in PSI text that mention oxygen. Quoted as text, never turned into numbers we did not read."""
    sents = re.split(r"(?<=[.!?])\s+", text)
    return [s for s in sents if re.search(r"\boxygen\b|\bO2\b|\bO₂\b", s, re.I)][:4]


def build(raw: list[dict]) -> list[dict]:
    out = []
    for r in raw:
        acc = r["Accession"]
        text = " ".join(clean(r.get(f)) for f in TEXT_FIELDS)
        out.append({
            "id": acc,
            "acronym": clean(r.get("Acronym")) or None,
            "title": clean(r.get("Title")),
            "sub_area": clean(r.get("SubResearch Area")) or None,
            "project_type": clean(r.get("Project Type")) or None,
            "gravity": gravity_of(r),
            "platform": clean(r.get("Flight Platform")) or None,
            "hardware": clean(r.get("Experiment Hardware")) or None,
            "start": clean(r.get("Investigation Start Date")) or None,
            "end": clean(r.get("Investigation End Date")) or None,
            "keywords": [clean(k) for k in re.split(r"\s{3,}|;", str(r.get("Keywords") or "")) if clean(k)],
            "objectives": clean(r.get("Objectives")) or None,
            "approach": clean(r.get("Approach")) or None,
            "hypothesis": clean(r.get("Hypothesis")) or None,
            "impacts": clean(r.get("Research Impacts/Earth Benefits")) or None,
            "related": re.findall(r"PSI-\d+", clean(r.get("Related Investigations"))),
            "publication": clean(r.get("Publication Title")) or None,
            "oxygen_mentions": oxygen_mentions(text),
            "source": {"repository": "NASA Physical Sciences Informatics (PSI)", "accession": acc, "url": PAGE.format(acc=acc)},
        })
    return out


def main() -> None:
    if "--offline" in sys.argv:
        raw = json.loads(RAW.read_text())
    else:
        raw = fetch_raw()
        RAW.write_text(json.dumps(raw, indent=1, ensure_ascii=False))
    ev = build(raw)
    OUT.write_text(json.dumps({"generated_from": "NASA PSI repository search API", "count": len(ev), "records": ev}, indent=1, ensure_ascii=False))
    print(f"{len(ev)} combustion investigations -> {OUT}")


if __name__ == "__main__":
    main()
