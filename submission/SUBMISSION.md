# Project submission text

Team: **The Talents**. Copy each section into the matching field on the Space Apps project page. Replace every `[bracket]`.

---

## Project name

Beyond the Dashboard (The Talents)

## High-level summary

Before people live on the Moon, engineers have to decide what is fire-safe there. NASA's microgravity combustion experiments hold much of the answer, but they are scattered across investigations, and none in NASA's PSI archive ran in lunar gravity. We built the dashboard the challenge asks for, designed for AI agents first: an MCP server that summarizes, ranks and interprets NASA's 24 PSI combustion investigations for any cabin condition, cites each record, and flags where the evidence runs out. Then we went beyond it. On a mission, the same decision can come during a real fire with no time to call Earth, so we built an AI crew member for a simulated lunar cabin that uses the same evidence to inspect, decide and act through a decision gate that code controls, and reports back for human review.

## Demo

[Link to the 30-second video]

## Project repository

[GitHub link]

## Detailed description

**The decision problem.** Fire safety for lunar and Martian habitats rests on combustion results gathered in microgravity on the ISS and in 1 g on Earth. Planned habitat atmospheres differ from both: the challenge notes that future Moon bases may run at 30 % oxygen or more and 10.2 psi or less, where materials are much more flammable. An engineer, or a crew, has to decide which results apply, how far, and what to do.

**Part 1: the dashboard, for AI first.** We pulled all 24 Combustion Science investigations from NASA's Physical Sciences Informatics repository and exposed them through an MCP server, so any AI agent can use them:

- `evidence_search` ranks investigations for a question or a cabin condition and attaches applicability notes (for example: tested in microgravity, so applying it at lunar gravity is an extrapolation).
- `evidence_get` and `evidence_compare` return full records and side-by-side comparisons, with oxygen-related sentences quoted from PSI.
- `evidence_gaps` reports what the record does not cover. No PSI combustion investigation was run in partial gravity.

[One or two sentences about your conversational dashboard: a person types or speaks a question and the crew AI builds and edits a panel, using these tools.]

**Part 2: beyond the dashboard.** A smoke alarm in a simulated 30.5 % oxygen lunar cabin, with the ground link down. The AI crew member:

1. reads the cabin and pulls the relevant NASA evidence;
2. first suspects a sensor fault, because the carbon-monoxide reading is normal, and sends a free-flying robot to look;
3. when the robot finds a real smoke source, the first conclusion is retracted automatically by code, because it depended on the reading the robot contradicted;
4. it retrieves PSI-20 (ACME Burning Rate Emulator), which reports that in elevated-oxygen atmospheres flames kept burning with no air flow, while at 21 % oxygen they self-extinguished. Cutting ventilation is a standard step in putting out spacecraft fires, so the crew member does not rely on it alone and proposes suppression;
5. the decision gate allows it: a hard-to-reverse action normally waits for ground approval, but with the link down and harm imminent it runs and is flagged for review;
6. it files a report that cites the PSI records and states which conclusions extrapolate beyond tested conditions.

**Safety by design.** A decision model (Cloudflare's open-weight Clef-flash, or a labelled rule scorer when it is not configured) only scores fixed options. Code decides what may run, by tier. External agents get read-only tools. Every tool call, decision and retraction goes into an event log.

**What is simulated.** The cabin, its telemetry, the robot and the fault scenarios are simulated. The autonomous-control sequence in the video is a scripted three.js concept animation of this control flow, not a screen recording of the agent. [Dashboard sequence: if it is a screen recording of our working product, say so; if it is the animated stand-in from `web/concept-dashboard`, say that instead.] The first ten seconds are our team; the rest of the narration is synthetic speech. The same flow runs in code: `python -m cabin_ai.agent --scripted`.

**Why it matters.** Crewed missions beyond low Earth orbit will face communication delays and outages. A crew member, human or AI, has to make fire decisions from evidence that was never gathered in their exact conditions. Our system makes that evidence usable by machines, keeps its limits visible, and keeps humans in charge of what is hard to undo.

## NASA data

| Data | Link | How we used it |
| --- | --- | --- |
| NASA Physical Sciences Informatics (PSI) repository, Combustion Science investigations (24 records) | https://psi.nasa.gov/physci/repo/ | Evidence base for every tool: search, ranking, comparison, gap analysis, and the decision in the demo (PSI-20, PSI-25) |

Records named in the demo: PSI-25 BASS-II, PSI-20 ACME BRE, plus BASS (PSI-26), SAFFIRE-I/II/III (PSI-98/99/100), FLEX (PSI-69), FLEX-2 (PSI-68), CFI (PSI-39), SAME (PSI-102), DAFT (PSI-47), SPICE (PSI-107), SLICE (PSI-106).

## Use of AI

See `AI_USAGE.md` and paste its short version here.

## Tags

#fire-safety #microgravity #combustion #MCP #AI-agents #lunar-habitat #human-in-the-loop
