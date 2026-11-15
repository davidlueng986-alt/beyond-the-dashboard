"""Decision gate: every cabin action passes through here, whoever asks for it.

Two parts, kept apart on purpose:
1. A scorer gives probabilities over a fixed set of options. The default is Clef-flash, Cloudflare's
   open-weight decision model, called on Workers AI when credentials are set; otherwise a transparent
   rule scorer is used and labelled as such in every result.
2. Code, not the model, decides whether an action may run. Tiers live in TIERS below; a model's
   confidence never raises an action's tier or skips approval.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass

# 0 read/analyse · 1 reversible · 2 hard to reverse · 3 not allowed
TIERS = {
    "INSPECT": 1, "REREAD": 1, "HOLD": 1, "RESUME": 1,
    "CUT_VENT": 2, "SUPPRESS": 2, "ABORT_EXPERIMENT": 2,
}
OPTIONS = {
    "INSPECT": "Send the free-flyer to look at the suspected source before acting",
    "REREAD": "Re-read the sensors and wait for a second reading",
    "HOLD": "Hold the current state and keep monitoring",
    "CUT_VENT": "Close the vent in the affected bay to starve the fire of airflow",
    "SUPPRESS": "Trigger fire suppression in the affected bay",
}


@dataclass
class Verdict:
    action: str
    tier: int
    outcome: str          # executed | queued_for_approval | rejected
    reason: str
    probabilities: dict
    scorer: str


def rule_scorer(state: dict, options: list[str]) -> tuple[dict, str]:
    """Transparent fallback. Not a model: hand-written weights, shown as such."""
    smoke = state.get("smoke_pct_per_m", 0) > 1.0
    confirmed = state.get("inspection", {}).get("visual_smoke")
    # PSI-20 (ACME BRE): in elevated-oxygen atmospheres flames kept burning with no air flow,
    # so at high oxygen, cutting ventilation alone is not trusted to put a fire out.
    high_o2 = state.get("o2_pct", 21) > 23.5
    raw = {o: 0.05 for o in options}
    if smoke and confirmed is None:
        raw.update(INSPECT=.81, REREAD=.12, HOLD=.07)
    elif confirmed and high_o2:
        raw.update(SUPPRESS=.86, CUT_VENT=.11)
    elif confirmed:
        raw.update(CUT_VENT=.86, HOLD=.14)
    elif confirmed is False:
        raw.update(HOLD=.7, REREAD=.3)
    p = {o: raw.get(o, .01) for o in options}
    z = sum(p.values())
    return {o: round(v / z, 2) for o, v in p.items()}, "rules-fallback (not a model)"


def clef_scorer(state: dict, options: list[str]) -> tuple[dict, str]:
    """Clef-flash on Cloudflare Workers AI. Request shape follows Cloudflare's Clef 'choice' question;
    check it against the current Workers AI docs before relying on it."""
    acct, tok = os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"]
    body = {"state": state, "questions": {"next_action": {"type": "choice", "options": {o: OPTIONS.get(o, o) for o in options}}}}
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/@cf/cloudflare/clef-flash",
                                 data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        res = json.load(r)["result"]
    probs = res["next_action"]["probabilities"]
    return {o: round(float(probs.get(o, 0)), 2) for o in options}, "clef-flash (Workers AI)"


def score(state: dict, options: list[str]) -> tuple[dict, str]:
    if os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_API_TOKEN"):
        try:
            return clef_scorer(state, options)
        except Exception as e:  # never let a model outage block the safety path
            p, _ = rule_scorer(state, options)
            return p, f"rules-fallback (Clef call failed: {type(e).__name__})"
    return rule_scorer(state, options)


def decide(action: str, state: dict, options: list[str], link_up: bool, minutes_to_harm: float | None, caller: str) -> Verdict:
    probs, scorer = score(state, options)
    tier = TIERS.get(action, 3)
    if caller != "cabin-agent":
        return Verdict(action, tier, "rejected", "Only the cabin agent may act; external agents get read-only tools.", probs, scorer)
    if tier >= 3:
        return Verdict(action, tier, "rejected", f"'{action}' is not on the allowed action list.", probs, scorer)
    if tier == 1:
        return Verdict(action, tier, "executed", "Reversible action: runs autonomously, logged for review.", probs, scorer)
    # tier 2: ask the ground if it can answer in time, otherwise act and request review afterwards
    round_trip_min = 0.05  # Earth-Moon light time plus handling; set per mission
    if link_up and (minutes_to_harm is None or minutes_to_harm > round_trip_min * 20):
        return Verdict(action, tier, "queued_for_approval", "Hard-to-reverse action with the ground link up: waiting for human approval.", probs, scorer)
    return Verdict(action, tier, "executed", "Hard-to-reverse action with no time to ask (link down or harm imminent): executed, flagged for ground review.", probs, scorer)
