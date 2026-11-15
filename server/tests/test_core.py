import json
from cabin_ai import evidence
from cabin_ai.agent import run_scripted
from cabin_ai.eventlog import EventLog
from cabin_ai.gate import OPTIONS, decide


def test_evidence_is_real_psi():
    rs = evidence.records()
    assert len(rs) == 24
    assert all(r["source"]["url"].startswith("https://psi.nasa.gov/") and r["id"].startswith("PSI-") for r in rs)


def test_search_flags_partial_gravity():
    res = evidence.search("flame spread solid fuel oxygen lunar cabin")
    assert res["results"], res
    assert all("extrapolation" in " ".join(r["applicability_notes"]) for r in res["results"])


def test_gaps_has_no_partial_gravity():
    g = evidence.gaps()
    assert g["partial_gravity_records"] == []


def test_external_agent_cannot_act():
    v = decide("SUPPRESS", {"o2_pct": 30.5}, list(OPTIONS), link_up=False, minutes_to_harm=1, caller="external-agent")
    assert v.outcome == "rejected"


def test_tier2_waits_when_ground_can_answer_and_acts_when_it_cannot():
    up = decide("CUT_VENT", {}, list(OPTIONS), link_up=True, minutes_to_harm=30, caller="cabin-agent")
    down = decide("CUT_VENT", {}, list(OPTIONS), link_up=False, minutes_to_harm=30, caller="cabin-agent")
    assert up.outcome == "queued_for_approval" and down.outcome == "executed"


def test_unknown_action_rejected():
    assert decide("VENT_TO_SPACE", {}, list(OPTIONS), False, 1, "cabin-agent").outcome == "rejected"


def test_retraction_cascades():
    log = EventLog()
    r = log.add("reading", "t", {})
    c1 = log.add("conclusion", "t", {}, [r.id])
    d1 = log.add("decision", "t", {}, [c1.id])
    c2 = log.add("conclusion", "t", {}, [d1.id])
    assert set(log.invalidate(r.id, "bad sensor")) == {c1.id, d1.id, c2.id}


def test_scripted_real_fire_uses_evidence_and_suppresses():
    c = run_scripted("smoke_vent_b")
    evs = c.log.dump()
    assert any(e["type"] == "retraction" and e["payload"]["retracted"] for e in evs)
    last = [e for e in evs if e["type"] == "decision"][-1]["payload"]
    assert last["action"] == "SUPPRESS" and last["gate"]["outcome"] == "executed"
    assert c.cabin.vents["vent_b"] == "closed"
    assert any("PSI-20" in json.dumps(e["payload"]) for e in evs)


def test_scripted_false_alarm_holds():
    c = run_scripted("smoke_sensor_fault")
    assert c.cabin.vents["vent_b"] == "open"
    assert [e for e in c.log.dump() if e["type"] == "decision"][-1]["payload"]["action"] == "HOLD"
