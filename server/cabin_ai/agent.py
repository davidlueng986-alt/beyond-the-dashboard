"""The AI crew member: an autonomous loop over the same tools the MCP server exposes.

Two modes:
  --llm       an open-weight model on any OpenAI-compatible endpoint drives the loop with tool calls
              (vLLM, Ollama, LM Studio, OpenRouter...). Set OPENAI_BASE_URL, OPENAI_API_KEY, CABIN_AI_MODEL.
  --scripted  a fixed plan, for tests and a reproducible demo. It is labelled 'scripted' in every log line.

    python -m cabin_ai.agent --scripted --scenario smoke_vent_b
    python -m cabin_ai.agent --llm --scenario smoke_sensor_fault

The loop never acts on the cabin directly: actions go through gate.decide, and conclusions are
recorded with their inputs so a later contradiction retracts them by code.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

from . import evidence
from .cabin import Cabin
from .eventlog import EventLog
from .gate import OPTIONS, decide

RUNS = Path(__file__).resolve().parents[2] / "runs"
SYSTEM = """You are the AI crew member of a lunar transit vehicle. The ground link may be down.
A smoke alarm has gone off. Use the tools to: read the cabin; find NASA PSI evidence for this cabin's conditions
(high oxygen, low pressure, partial gravity); decide whether to inspect, hold or act; act only through propose_action;
record each conclusion with the event ids it depends on; finish with a short report that cites PSI ids and says
which conclusions extrapolate beyond tested conditions. Never invent numbers; quote PSI text."""


class Crew:
    def __init__(self, scenario: str, actor_label: str):
        self.cabin = Cabin()
        self.log = EventLog(RUNS / f"{scenario}_{actor_label}.jsonl")
        self.scenario = scenario
        self.label = actor_label
        self.cabin.inject("link_loss")
        self.cabin.inject(scenario)

    # tools ------------------------------------------------------------
    def read_cabin(self):
        r = self.cabin.read(); e = self.log.add("reading", self.label, r, simulated=True); return {"event": e.id, **r}

    def search_evidence(self, query: str):
        r = evidence.search(query, "partial gravity", 5)
        e = self.log.add("tool_call", self.label, {"tool": "evidence_search", "query": query, "ids": [x["id"] for x in r["results"]]})
        return {"event": e.id, **r}

    def get_evidence(self, record_id: str):
        r = evidence.get(record_id); e = self.log.add("tool_call", self.label, {"tool": "evidence_get", "id": r["id"]})
        return {"event": e.id, "id": r["id"], "acronym": r["acronym"], "impacts": r["impacts"], "oxygen_mentions": r["oxygen_mentions"], "source": r["source"]["url"]}

    def send_robot(self, waypoint: str):
        r = self.cabin.robot.goto(waypoint); e = self.log.add("tool_call", self.label, {"tool": "robot_goto", **r}, simulated=True); return {"event": e.id, **r}

    def inspect(self, target: str):
        r = self.cabin.inspect(target); e = self.log.add("reading", self.label, {"tool": "robot_inspect", **r}, simulated=True); return {"event": e.id, **r}

    def conclude(self, text: str, depends_on: list[str]):
        e = self.log.add("conclusion", self.label, {"text": text}, depends_on); return {"event": e.id}

    def invalidate(self, event_id: str, reason: str):
        return {"retracted": self.log.invalidate(event_id, reason, self.label)}

    def propose_action(self, action: str, reason: str, depends_on: list[str], inspection: dict | None = None, evidence_flags: list[str] | None = None):
        state = {**self.cabin.read(), "inspection": inspection or {}, "evidence_flags": evidence_flags or []}
        v = decide(action, state, list(OPTIONS), self.cabin.link == "up", 2.0, "cabin-agent")
        e = self.log.add("decision", self.label, {"action": action, "agent_reason": reason, "gate": v.__dict__}, depends_on)
        if v.outcome == "executed" and action in ("CUT_VENT", "SUPPRESS"):
            self.cabin.act("close_vent_b")
        return {"event": e.id, **v.__dict__}

    def report(self, text: str):
        e = self.log.add("report", self.label, {"text": text, "awaiting": "ground review"}); return {"event": e.id}


def run_scripted(scenario: str) -> Crew:
    c = Crew(scenario, "scripted")
    r0 = c.read_cabin()
    ev = c.search_evidence("smoke alarm spacecraft fire flame spread solid fuel oxygen ventilation")
    first = c.conclude("Smoke alarm with normal CO: possible sensor fault. Inspect before acting.", [r0["event"]])
    d1 = c.propose_action("INSPECT", "readings conflict", [first["event"]])
    c.send_robot("vent_b")
    insp = c.inspect("vent_b")
    if insp["visual_smoke"]:
        c.invalidate(first["event"], "robot inspection found a real smoke source at vent B")
        bre = c.get_evidence("PSI-20")      # ACME BRE: elevated oxygen, flames persisted without airflow
        flag = "PSI-20: in elevated-oxygen atmospheres flames continued without air flow"
        conc = c.conclude(f"Active smoke source at vent B. Cabin O2 {r0['o2_pct']} % is elevated; {flag}, so cutting ventilation alone may not extinguish it.",
                          [insp["event"], bre["event"], r0["event"]])
        d2 = c.propose_action("SUPPRESS", "confirmed source in elevated oxygen", [conc["event"]], insp, [flag])
        c.report(f"Vent B: confirmed smoke, suppression released and vent closed ({d2['outcome']}). Evidence: PSI-20 (ACME BRE), "
                 f"plus {', '.join(x['id'] for x in ev['results'][:3])}. All PSI combustion tests are microgravity or 1 g; applying them at lunar gravity is an extrapolation.")
    else:
        c.conclude("No smoke at the source: detector fault confirmed.", [insp["event"], first["event"]])
        c.propose_action("HOLD", "false alarm", [insp["event"]], insp)
        c.report("False alarm at vent B: detector flagged for maintenance. No action taken on the cabin.")
    return c


# ---------------- LLM loop (OpenAI-compatible tool calling) ----------------
TOOLS = [
    ("read_cabin", "Read simulated cabin telemetry.", {}),
    ("search_evidence", "Search NASA PSI combustion investigations.", {"query": {"type": "string"}}),
    ("get_evidence", "Get one PSI record by id, e.g. PSI-20.", {"record_id": {"type": "string"}}),
    ("send_robot", "Fly the free-flyer to a waypoint: dock, cabin_center, vent_b.", {"waypoint": {"type": "string"}}),
    ("inspect", "Inspect a waypoint with the robot's cameras.", {"target": {"type": "string"}}),
    ("conclude", "Record a conclusion with the event ids it depends on.", {"text": {"type": "string"}, "depends_on": {"type": "array", "items": {"type": "string"}}}),
    ("invalidate", "Mark an event wrong; dependent conclusions are retracted.", {"event_id": {"type": "string"}, "reason": {"type": "string"}}),
    ("propose_action", "Propose INSPECT, REREAD, HOLD, CUT_VENT or SUPPRESS through the decision gate.",
     {"action": {"type": "string"}, "reason": {"type": "string"}, "depends_on": {"type": "array", "items": {"type": "string"}}}),
    ("report", "Final report for ground review.", {"text": {"type": "string"}}),
]


def run_llm(scenario: str, max_steps: int = 24) -> Crew:
    base, key, model = os.environ["OPENAI_BASE_URL"].rstrip("/"), os.environ.get("OPENAI_API_KEY", "none"), os.environ["CABIN_AI_MODEL"]
    c = Crew(scenario, "llm")
    tools = [{"type": "function", "function": {"name": n, "description": d, "parameters": {"type": "object", "properties": p, "required": list(p)}}} for n, d, p in TOOLS]
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "Alarm. Begin."}]
    for _ in range(max_steps):
        req = urllib.request.Request(f"{base}/chat/completions", data=json.dumps({"model": model, "messages": msgs, "tools": tools}).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            m = json.load(r)["choices"][0]["message"]
        msgs.append(m)
        calls = m.get("tool_calls") or []
        if not calls:
            break
        for tc in calls:
            name, args = tc["function"]["name"], json.loads(tc["function"]["arguments"] or "{}")
            try:
                out = getattr(c, name)(**args)
            except Exception as e:
                out = {"error": str(e), "next": "check the arguments and try again"}
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(out, ensure_ascii=False)})
            if name == "report":
                return c
    return c


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="smoke_vent_b", choices=["smoke_vent_b", "smoke_sensor_fault"])
    g = ap.add_mutually_exclusive_group(); g.add_argument("--scripted", action="store_true"); g.add_argument("--llm", action="store_true")
    a = ap.parse_args()
    c = run_llm(a.scenario) if a.llm else run_scripted(a.scenario)
    for e in c.log.dump():
        tag = f"[{e['status']}]" if e["status"] != "active" else ""
        print(f"{e['id']:>4} {e['type']:<11} {tag:<12} {json.dumps(e['payload'], ensure_ascii=False)[:150]}")
    print(f"\nlog: {c.log.path}")


if __name__ == "__main__":
    main()
