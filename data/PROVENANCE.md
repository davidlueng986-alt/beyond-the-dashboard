# Where the data comes from

| File | Source | How it was made |
| --- | --- | --- |
| `psi_combustion_raw.json` | NASA Physical Sciences Informatics (PSI), https://psi.nasa.gov/physci/repo/ | `fetch_psi.py` queries PSI's public search endpoint (`/geode-py/ws/repo/search`, the one the PSI web app uses) for *combustion, fire, flame, smoke, spacecraft fire safety* and keeps every record whose Research Area is **Combustion Science**. Fetched 15 Nov 2026: 24 records. |
| `evidence.json` | Built from the file above | Same fields, cleaned of extra whitespace. `gravity` is copied from PSI's *Project Type*. `oxygen_mentions` are sentences quoted from the PSI text that mention oxygen; no numbers are added or inferred. Each record links to its PSI page. |

## Figures used in the demo and where each one is stated

| Figure | Where it is stated |
| --- | --- |
| BASS-II varied oxygen **below 21 %** | PSI-25, *Approach*: "oxygen varied below 21% by adding nitrogen" |
| ACME BRE examined **34 % oxygen at 8.2 psia** (also 26.5 % at 10.2 psia, 21 % at 14.7 psia) | PSI-20, *Objectives* |
| In elevated-oxygen atmospheres, flames on BRE kept burning **with no air flow**, while at 21 % they self-extinguished | PSI-20, *Research Impacts/Earth Benefits* |
| No PSI combustion record is a partial-gravity investigation | All 24 records: Project Type is Microgravity Investigation (19) or Ground Investigation (5) |
| Cabin at 30.5 % O₂ and 70.3 kPa | Simulated scenario, chosen inside the range the challenge statement gives for future lunar habitats (30 % or more oxygen at 10.2 psi or less) |

Values that are **not** NASA data: every cabin reading, every robot result, every decision probability from the rule scorer, and the whole autonomous-control animation.
