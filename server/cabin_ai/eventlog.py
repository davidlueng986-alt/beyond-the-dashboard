"""Append-only event log with dependencies, so a conclusion can be retracted by code.

Every tool call, reading, decision and conclusion is one event. A conclusion lists the events it
depends on. When an input is invalidated, every conclusion downstream of it is marked RETRACTED
automatically; the model is never trusted to notice on its own.
"""
from __future__ import annotations

import itertools
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Event:
    id: str
    type: str                      # tool_call | reading | decision | conclusion | retraction | approval | report
    actor: str                     # cabin-agent | external-agent | human | system
    payload: dict
    depends_on: list[str] = field(default_factory=list)
    simulated: bool = False
    ts: float = field(default_factory=time.time)
    status: str = "active"         # active | invalid | retracted


class EventLog:
    def __init__(self, path: Path | None = None):
        self.events: dict[str, Event] = {}
        self._n = itertools.count(1)
        self.path = path
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("")

    def add(self, type: str, actor: str, payload: dict, depends_on=(), simulated=False) -> Event:
        e = Event(f"e{next(self._n)}", type, actor, payload, list(depends_on), simulated)
        self.events[e.id] = e
        self._write(e)
        return e

    def invalidate(self, event_id: str, reason: str, actor: str = "system") -> list[str]:
        """Mark an input invalid and retract every conclusion that depends on it, transitively."""
        tgt = self.events[event_id]
        tgt.status = "retracted" if tgt.type in ("conclusion", "decision") else "invalid"
        retracted, frontier = [], [event_id]
        while frontier:
            cur = frontier.pop()
            for e in self.events.values():
                if cur in e.depends_on and e.status == "active":
                    if e.type in ("conclusion", "decision"):
                        e.status = "retracted"; retracted.append(e.id)
                    frontier.append(e.id)
        self.add("retraction", actor, {"invalidated": event_id, "reason": reason, "retracted": retracted})
        return retracted

    def active_conclusions(self) -> list[Event]:
        return [e for e in self.events.values() if e.type == "conclusion" and e.status == "active"]

    def _write(self, e: Event) -> None:
        if self.path:
            with self.path.open("a") as f:
                f.write(json.dumps(asdict(e)) + "\n")

    def dump(self) -> list[dict]:
        return [asdict(e) for e in self.events.values()]
