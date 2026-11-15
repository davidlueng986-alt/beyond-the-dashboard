# Beyond the Dashboard

**The Talents · NASA Space Apps Challenge 2026 · Flame in Freefall**

Before people live on the Moon, engineers have to decide what is fire-safe there. NASA's microgravity combustion experiments hold much of the answer, but the results are scattered across investigations, and none of them were run in lunar gravity.

This repository has two parts:

1. **The dashboard, for AI first.** An MCP server that summarizes, ranks and interprets NASA's Physical Sciences Informatics (PSI) combustion investigations for any cabin condition, and flags where the evidence runs out. Any MCP-capable agent can use it; our conversational dashboard is built on the same tools.
2. **Beyond the dashboard.** An AI crew member for a simulated lunar cabin. When the ground link drops and a smoke alarm goes off, it reads the cabin, pulls the NASA evidence, sends a robot to look, retracts its first guess when the robot contradicts it, and acts through a decision gate that code controls.

```
data/        NASA PSI combustion records (real) + fetch script + provenance
server/      cabin_ai: MCP server, evidence tools, decision gate, event log with retraction, simulated cabin, autonomous agent, tests
sim/         three.js concept scenes for the video (simulated lunar vehicle) + rendering, narration and sound scripts
web/         concept-dashboard: animated stand-in of the dashboard used in the backup video
submission/  project page text, AI-use disclosure, video script
```

## Run it

```bash
cd server
pip install -e ".[test]"
pytest                                   # 9 tests

python -m cabin_ai.agent --scripted --scenario smoke_vent_b        # real smoke: inspect, retract, suppress
python -m cabin_ai.agent --scripted --scenario smoke_sensor_fault  # false alarm: inspect, hold

# drive the crew member with an open-weight model on any OpenAI-compatible endpoint (not yet run end-to-end in this build)
OPENAI_BASE_URL=http://localhost:11434/v1 CABIN_AI_MODEL=qwen3.6:27b python -m cabin_ai.agent --llm

# MCP server for other agents (read-only evidence tools by default)
python -m cabin_ai.mcp_server                     # stdio
python -m cabin_ai.mcp_server --http 8765         # streamable HTTP
CABIN_AI_ROLE=cabin-agent python -m cabin_ai.mcp_server   # full tool set, actions still gated
```

Refresh the NASA data: `python data/fetch_psi.py` (or `--offline` to rebuild from the saved raw file).

## How a decision is made

| Step | Who | Rule |
| --- | --- | --- |
| Score the options | Clef-flash on Workers AI if `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` are set; otherwise a rule scorer that says so in every result | Probabilities only |
| Decide whether it may run | Code (`server/cabin_ai/gate.py`) | Tier 1 (inspect, reread, hold) runs. Tier 2 (cut vent, suppress) waits for the ground when it can answer in time, and runs with a review flag when it cannot. Anything else is rejected. External agents can never act. |
| Undo a wrong conclusion | Code (`eventlog.py`) | Each conclusion records the events it depends on; invalidating an input retracts everything downstream. |

The evidence changes the action. PSI-20 (ACME BRE) reports that in elevated-oxygen atmospheres flames kept burning with no air flow, while at 21 % oxygen they self-extinguished. In a 30.5 % oxygen cabin the crew member therefore does not trust a vent cut-off alone and chooses suppression.

## What is real and what is simulated

- **Real:** the 24 NASA PSI combustion records and every figure quoted from them (see `data/PROVENANCE.md`), the MCP server, the gate, the retraction logic, the agent loop and tests.
- **Simulated:** the lunar cabin, its telemetry, the robot, the fault scenarios, and the rule scorer's probabilities. The robot interface mirrors the NASA Astrobee simulator's teleop commands so a ROS/Gazebo bridge can replace it.
- **Concept animation:** the autonomous-control sequence in the video is a scripted three.js scene that shows this control flow; it is not a recording of the agent running.

## Licence

MIT for our code. NASA PSI data is public; see the PSI repository for its terms.
