# Use of AI

Space Apps 2026 allows AI-generated content if all AI use is disclosed and described. This is ours. Replace every `[bracket]`.

## Short version (paste into the project page)

We used AI throughout. Claude (Anthropic) helped plan the project, write code (MCP server, decision gate, simulated cabin, agent loop, tests, data pipeline, and a bridge to NASA's Astrobee simulator that we have not yet run), write the three.js scenes and the video tooling, and draft this text; team members reviewed and edited the results. [Add any other assistants you used.] Inside the product, an open-weight LLM can drive the AI crew member, and Cloudflare's open-weight Clef-flash decision model can score options at the decision gate; when it is not configured, a labelled rule scorer is used. In the video, the first two lines are spoken by our team; the remaining narration is synthetic speech from the open-weight Kokoro-82M model. Team footage was cleaned up with conventional tools (stabilisation, colour, noise reduction, EQ); one teammate's mouth was replaced with a still frame of himself for four seconds to hide chewing gum. The video's 3D scenes and dashboard animation were rendered from code we wrote with AI help; no image or video generation model was used. The music bed and sound effects were synthesised from code. No NASA logos, flags or mission identifiers appear in any AI-made material. All NASA figures come from the PSI repository and are traced in `data/PROVENANCE.md`.

## Detail

| Where | Tool or model | What it did | Human role |
| --- | --- | --- | --- |
| Planning, specs, scripts | Claude (Anthropic) | Drafted the system design, task split, video script and submission text | Chose the direction and every decision; edited the text |
| Code | Claude (Anthropic) [+ others] | Wrote `server/` (including the untested Astrobee bridge `astrobee.py`), `data/fetch_psi.py`, `sim/`, `web/concept-dashboard/` | Reviewed, ran tests, integrated with our dashboard |
| Our dashboard | [tools used] | [what AI did] | [what the team did] |
| Runtime: crew member | Open-weight LLM via an OpenAI-compatible endpoint (e.g. Qwen3.6-27B) | Plans and calls tools during a scenario | Sets the tools, the gate and what may run |
| Runtime: decision gate | Clef-flash (Cloudflare, Apache-2.0 weights), optional | Scores a fixed set of actions | Code decides by tier; humans review tier-2 actions |
| Video narration, lines 3-5 | Kokoro-82M (open-weight text-to-speech) | Spoke the script | Wrote and approved the script; lines 1-2 are spoken by the team |
| Team footage clean-up | ffmpeg, OpenCV (no generative model) | Stabilisation, colour, denoise, EQ; a 4-second still-mouth patch on one teammate | Filmed the footage, approved the edit |
| Video visuals | three.js and HTML rendered in a headless browser | 3D vehicle, cabin and dashboard animation | Directed and approved every shot |
| Music and sound | Python synthesis code | Original bed and effects; no samples | Approved the mix |

## What is simulated or scripted

- The lunar cabin, telemetry, robot and fault scenarios are simulated.
- The autonomous-control sequence in the video is a scripted concept animation, not a recording of the agent.
- [Dashboard sequence: screen recording of our working product / animated stand-in. Pick one.]
