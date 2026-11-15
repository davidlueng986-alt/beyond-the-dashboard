# Project submission text

Team: **The Talents**. Copy each section into the matching field on the Space Apps project page. Replace every `[bracket]`.

---

## Project name

Beyond the Dashboard (The Talents)

## High-level summary

Before people live on the Moon, engineers have to decide what is fire-safe there. NASA's microgravity combustion experiments hold much of the answer, but they are scattered across investigations, and none in NASA's PSI archive ran in lunar gravity. The real problem behind this challenge is a decision: which results apply, how far, and what to do. We built the dashboard the challenge asks for in two layers. For AI agents, who will increasingly be the ones reading NASA's data, an MCP server summarizes, ranks and interprets NASA's 24 PSI combustion investigations for any cabin condition, cites each record, and flags where the evidence runs out. For people, an Intelligent UI turns a typed or spoken question into only the panels needed to decide, so the reader spends attention on the decision, not on the data. Then we went beyond the dashboard. On a mission, the same decision can come during a real fire with no time to call Earth, so we built an AI crew member for a simulated lunar cabin that uses the same evidence to inspect, decide and act through a decision gate that code controls, and reports back for human review. We also wrote a bridge to NASA's Astrobee robot simulator, so the same crew member can fly a real NASA free-flyer design next.

## Demo

https://github.com/davidlueng986-alt/beyond-the-dashboard/blob/main/media/TheTalents_30s.mp4  [replace with a YouTube/Vimeo link if the form requires one]

## Project repository

https://github.com/davidlueng986-alt/beyond-the-dashboard

## Detailed description

**The decision problem.** Fire safety for lunar and Martian habitats rests on combustion results gathered in microgravity on the ISS and in 1 g on Earth. Planned habitat atmospheres differ from both: the challenge notes that future Moon bases may run at 30 % oxygen or more and 10.2 psi or less, where materials are much more flammable. An engineer, or a crew, has to decide which results apply, how far, and what to do. A dashboard that only shows the data leaves that decision, and the risk of misreading the data, with the reader.

**Why we went beyond a dashboard.** We could have built another set of charts. We did not want to stop there. The next era of exploration will be carried out together by people, AI and robots: crews far from Earth, habitats that run for months without anyone on board, robots that inspect and repair. The reader of NASA's data will more and more often be an AI, and the moment that matters will often be a real emergency with no one on the ground to ask. So we designed for that future from the start: the data layer is built for machines, the interface is built to protect human attention, and the autonomy is built so that people stay in charge of what cannot be undone.

**Part 1a: the dashboard, for AI first.** We pulled all 24 Combustion Science investigations from NASA's Physical Sciences Informatics repository and exposed them through an MCP server, so any AI agent can use them:

- `evidence_search` ranks investigations for a question or a cabin condition and attaches applicability notes (for example: tested in microgravity, so applying it at lunar gravity is an extrapolation).
- `evidence_get` and `evidence_compare` return full records and side-by-side comparisons, with oxygen-related sentences quoted from PSI.
- `evidence_gaps` reports what the record does not cover. No PSI combustion investigation was run in partial gravity.

**Part 1b: the Intelligent UI, for people.** AI agents are our first user, but the people who make the final call need something different from more data: less to read and less to hold in their head. The Intelligent UI works like a conversation that builds its own dashboard. [Check: delete anything below that your dashboard does not do yet.]

- **Ask, don't search.** A researcher, engineer or student types or speaks a question, such as "What do we know about flames at 34 % oxygen and low pressure?", and the agent answers by building panels instead of a wall of text.
- **Only what the decision needs.** The agent picks from a fixed set of panels (evidence ranking, brief, implications, evidence gaps, comparison, chart, cabin state, decision log, approval queue, timeline) and shows only the ones the question needs. Follow-up questions edit the dashboard in place, so the context is never lost.
- **No invented numbers.** The agent chooses records and panels; every number is filled in by code from the PSI file. A layout that carries its own numbers is rejected.
- **Limits always visible.** Every panel shows where its evidence came from and whether applying it to the question is an extrapolation, so a confident-looking chart cannot hide a gap.
- **Humans approve what is hard to undo.** Actions the crew member proposes appear in an approval queue with the evidence behind them, so a person can approve or reject in seconds.

**Part 2: beyond the dashboard.** A smoke alarm in a simulated 30.5 % oxygen lunar cabin, with the ground link down. The AI crew member:

1. reads the cabin and pulls the relevant NASA evidence;
2. first suspects a sensor fault, because the carbon-monoxide reading is normal, and sends a free-flying robot to look;
3. when the robot finds a real smoke source, the first conclusion is retracted automatically by code, because it depended on the reading the robot contradicted;
4. it retrieves PSI-20 (ACME Burning Rate Emulator), which reports that in elevated-oxygen atmospheres flames kept burning with no air flow, while at 21 % oxygen they self-extinguished. Cutting ventilation is a standard step in putting out spacecraft fires, so the crew member does not rely on it alone and proposes suppression;
5. the decision gate allows it: a hard-to-reverse action normally waits for ground approval, but with the link down and harm imminent it runs and is flagged for review;
6. it files a report that cites the PSI records and states which conclusions extrapolate beyond tested conditions.

**Toward a real robot: Astrobee.** The robot in the demo is simulated in our own code, but its interface follows NASA's Astrobee free-flyer, which operates on the ISS. We wrote a bridge (`server/cabin_ai/astrobee.py`, notes in `docs/ASTROBEE.md`) that flies Astrobee in NASA's open-source Astrobee ROS/Gazebo simulator: undock, move to a pose, check arrival from localisation, take a camera frame, dock. One setting switches the crew member from our simulated robot to Astrobee without changing the agent or the decision gate. The bridge was written during the hackathon and is not shown in the demo; we have not yet run it against the simulator.

**Safety by design.** A decision model (Cloudflare's open-weight Clef-flash, or a labelled rule scorer when it is not configured) only scores fixed options. Code decides what may run, by tier. External agents get read-only tools. Every tool call, decision and retraction goes into an event log.

**What is simulated.** The cabin, its telemetry, the robot and the fault scenarios are simulated. The autonomous-control sequence in the video is a scripted three.js concept animation of this control flow, not a screen recording of the agent. [Dashboard sequence: if it is a screen recording of our working product, say so; if it is the animated stand-in from `web/concept-dashboard`, say that instead.] The opening of the video is our team; the rest of the narration is synthetic speech. The same flow runs in code: `python -m cabin_ai.agent --scripted`.

**Why it matters.** Crewed missions beyond low Earth orbit will face communication delays and outages. A crew member, human or AI, has to make fire decisions from evidence that was never gathered in their exact conditions. Our system makes that evidence usable by machines, keeps its limits visible to people, and keeps humans in charge of what is hard to undo. The same pattern (evidence an AI can read, an interface that saves human attention, autonomy behind a gate) applies well beyond fire: life support, power, medical events, any decision where the data was gathered somewhere else. That is the future we want to help build: people, AI and robots exploring together, and every decision traceable to the evidence behind it.

## NASA data

| Data | Link | How we used it |
| --- | --- | --- |
| NASA Physical Sciences Informatics (PSI) repository, Combustion Science investigations (24 records) | https://psi.nasa.gov/physci/repo/ | Evidence base for every tool: search, ranking, comparison, gap analysis, and the decision in the demo (PSI-20, PSI-25) |
| NASA Astrobee flight software and simulator (open source) | https://github.com/nasa/astrobee | Target of our robot bridge: the crew member's robot commands map onto Astrobee's motion and docking interfaces (written, not yet run) |

Records named in the demo: PSI-25 BASS-II, PSI-20 ACME BRE, plus BASS (PSI-26), SAFFIRE-I/II/III (PSI-98/99/100), FLEX (PSI-69), FLEX-2 (PSI-68), CFI (PSI-39), SAME (PSI-102), DAFT (PSI-47), SPICE (PSI-107), SLICE (PSI-106).

## Use of AI

See `AI_USAGE.md` and paste its short version here.

## Tags

#fire-safety #microgravity #combustion #MCP #AI-agents #intelligent-UI #Astrobee #lunar-habitat #human-in-the-loop
