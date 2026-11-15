"""MCP server: the product's primary interface, built for AI agents first.

One server, two kinds of caller:
  * the cabin agent (CABIN_AI_ROLE=cabin-agent) gets every tool, and cabin actions still pass the gate;
  * any other agent (default role) gets the read-only evidence tools.

Run:
    python -m cabin_ai.mcp_server                      # stdio, for local agents (pi, opencode, Claude Code, ...)
    python -m cabin_ai.mcp_server --http 8765          # streamable HTTP, for remote agents

Every result carries its source and whether it is simulated. Errors say what to try next.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:                                    # MCP Python SDK 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:                     # MCP Python SDK 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from . import evidence
from .cabin import Cabin
from .eventlog import EventLog
from .gate import OPTIONS, decide

ROLE = os.environ.get("CABIN_AI_ROLE", "external-agent")
RUNS = Path(__file__).resolve().parents[2] / "runs"

mcp = _Server(
    name="cabin-ai",
    instructions=(
        "Fire-safety evidence and cabin control for a simulated lunar transit vehicle. "
        "Evidence comes from NASA's Physical Sciences Informatics (PSI) combustion investigations; cite the PSI id. "
        "No PSI combustion test ran in partial gravity, so say so when applying results to the Moon or Mars. "
        "Cabin telemetry and the robot are simulated. Cabin actions go through a decision gate you cannot bypass."
    ),
)
CABIN = Cabin()
LOG = EventLog(RUNS / "live.jsonl")


def _ok(x) -> str:
    return json.dumps(x, ensure_ascii=False, indent=1)


def _err(msg: str, nxt: str) -> str:
    return _ok({"error": msg, "next": nxt})


# ---------------- evidence: read-only, open to every agent ----------------
@mcp.tool()
def evidence_search(query: str, gravity: str | None = None, k: int = 5) -> str:
    """Rank NASA PSI combustion investigations for a question or a cabin condition.
    Use for: 'which studies apply to a 30 % oxygen cabin', 'flame spread over solids', 'smoke detection'.
    gravity: optional 'microgravity' or 'partial gravity' to get applicability notes. Returns PSI ids, links, notes."""
    r = evidence.search(query, gravity, max(1, min(k, 10)))
    LOG.add("tool_call", ROLE, {"tool": "evidence_search", "query": query, "ids": [x["id"] for x in r["results"]]})
    return _ok(r)


@mcp.tool()
def evidence_get(record_id: str) -> str:
    """Full PSI record (objectives, approach, hypothesis, impacts, oxygen mentions, link) by PSI id like 'PSI-25' or acronym like 'BASS-II'."""
    try:
        r = evidence.get(record_id)
    except KeyError as e:
        return _err(str(e), "evidence_search with a topic, then use an id from its results")
    LOG.add("tool_call", ROLE, {"tool": "evidence_get", "id": r["id"]})
    return _ok(r)


@mcp.tool()
def evidence_compare(record_ids: list[str]) -> str:
    """Field-by-field comparison of two or more PSI records: what is the same, what differs, oxygen mentions, links."""
    try:
        return _ok(evidence.compare(record_ids))
    except KeyError as e:
        return _err(str(e), "check ids with evidence_search")


@mcp.tool()
def evidence_gaps() -> str:
    """What the PSI combustion record does not cover (for example partial gravity). Call before extrapolating to the Moon or Mars."""
    return _ok(evidence.gaps())


# ---------------- cabin: simulated vehicle ----------------
@mcp.tool()
def cabin_read() -> str:
    """Current simulated cabin telemetry: O2 %, pressure kPa, CO ppm, smoke %/m, link state, vents, robot position."""
    r = CABIN.read()
    LOG.add("reading", ROLE, r, simulated=True)
    return _ok(r)


def _cabin_only(tool: str):
    if ROLE != "cabin-agent":
        return _err(f"{tool} is limited to the cabin agent.", "use the evidence_* tools; cabin actions are not available to external agents")
    return None


@mcp.tool()
def robot_goto(waypoint: str) -> str:
    """Fly the free-flyer to a named waypoint: dock, cabin_center or vent_b. Reversible (tier 1)."""
    if (e := _cabin_only("robot_goto")):
        return e
    try:
        r = CABIN.robot.goto(waypoint)
    except ValueError as err:
        return _err(str(err), "pick a valid waypoint")
    LOG.add("tool_call", ROLE, {"tool": "robot_goto", **r}, simulated=True)
    return _ok(r)


@mcp.tool()
def robot_inspect(target: str) -> str:
    """Look at a target with the free-flyer's cameras. The robot must already be at that waypoint."""
    if (e := _cabin_only("robot_inspect")):
        return e
    try:
        r = CABIN.inspect(target)
    except ValueError as err:
        return _err(str(err), "call robot_goto first")
    LOG.add("reading", ROLE, {"tool": "robot_inspect", **r}, simulated=True)
    return _ok(r)


@mcp.tool()
def gate_propose(action: str, reason: str, minutes_to_harm: float | None = None) -> str:
    """Propose a cabin action. The gate scores options (Clef-flash if configured, else labelled rules), then code decides:
    tier 1 runs, tier 2 asks the ground when it can answer in time, anything off the list is rejected.
    action: INSPECT, REREAD, HOLD, CUT_VENT, SUPPRESS."""
    state = CABIN.read()
    v = decide(action, state, list(OPTIONS), CABIN.link == "up", minutes_to_harm, ROLE)
    ev = LOG.add("decision", ROLE, {"action": action, "agent_reason": reason, "gate": v.__dict__})
    if v.outcome == "executed" and action in ("CUT_VENT", "SUPPRESS"):
        CABIN.act("close_vent_b")
        LOG.add("tool_call", "system", {"tool": "cabin_act", "action": "close_vent_b", "via": ev.id}, simulated=True)
    return _ok(v.__dict__ | {"event": ev.id})


@mcp.tool()
def conclusion_record(text: str, depends_on: list[str]) -> str:
    """Record a conclusion and the event ids it rests on, so it can be retracted automatically if an input turns out wrong."""
    if (err := _cabin_only("conclusion_record")):
        return err
    e = LOG.add("conclusion", ROLE, {"text": text}, depends_on)
    return _ok({"event": e.id})


@mcp.tool()
def input_invalidate(event_id: str, reason: str) -> str:
    """Mark a reading or result as wrong. Every conclusion and decision that depended on it is retracted, transitively."""
    if (err := _cabin_only("input_invalidate")):
        return err
    if event_id not in LOG.events:
        return _err(f"No event {event_id}.", "read the log resource cabin://log for valid ids")
    return _ok({"retracted": LOG.invalidate(event_id, reason, ROLE)})


@mcp.tool()
def ui_render(layout: dict) -> str:
    """Ask the Intelligent UI to show a layout. layout = {"components": [{"type": "EvidenceRank"|"Brief"|"Implication"|"GapMap"|
    "Compare"|"Chart"|"CabinState"|"DecisionLog"|"ApprovalQueue"|"Timeline", "records": [PSI ids], "title": str}]}.
    Numbers are filled from the evidence file by code; a layout must not contain numbers of its own."""
    allowed = {"EvidenceRank", "Brief", "Implication", "GapMap", "Compare", "Chart", "CabinState", "DecisionLog", "ApprovalQueue", "Timeline"}
    comps = layout.get("components", [])
    bad = [c.get("type") for c in comps if c.get("type") not in allowed]
    if bad:
        return _err(f"Unknown component(s): {bad}", f"use one of {sorted(allowed)}")
    nums = [c for c in comps if any(isinstance(v, (int, float)) for v in c.values())]
    if nums:
        return _err("Layouts may not carry numbers; reference PSI ids and let the UI fill values.", "remove numeric fields")
    e = LOG.add("ui_render", ROLE, layout)
    return _ok({"accepted": True, "event": e.id})


@mcp.resource("cabin://log")
def log_resource() -> str:
    """The full event log: tool calls, readings, decisions, conclusions, retractions."""
    return _ok(LOG.dump())


def main() -> None:
    if "--http" in sys.argv:
        port = int(sys.argv[sys.argv.index("--http") + 1])
        try:
            mcp.run("streamable-http", port=port)
        except TypeError:
            mcp.settings.port = port; mcp.run("streamable-http")
    else:
        mcp.run("stdio")


if __name__ == "__main__":
    main()
