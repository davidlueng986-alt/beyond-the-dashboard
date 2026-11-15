"""Simulated lunar transit cabin: telemetry, faults, a free-flying inspection robot, a vent.

Everything here is simulated and every reading says so (simulated=True). The robot interface
mirrors the NASA Astrobee simulator's teleop commands (undock, move to a pose, dock), so a bridge to
the real Astrobee ROS/Gazebo simulator can replace RobotSim without touching the agent or the gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Lunar-base cabin atmosphere cited in the challenge statement: 30 % oxygen or more at 10.2 psi or less.
SCENARIOS = {
    "lunar_cabin": {"o2_pct": 30.5, "pressure_kpa": 70.3, "co_ppm": 2.0, "smoke_pct_per_m": 0.1, "gravity": "partial gravity (lunar, 1/6 g)"},
}
WAYPOINTS = {"dock": (-1.32, -0.15, -5.2), "cabin_center": (0.0, 0.0, -12.0), "vent_b": (0.55, 0.05, -18.2)}


@dataclass
class RobotSim:
    pose: tuple = WAYPOINTS["dock"]
    docked: bool = True
    at: str = "dock"

    def goto(self, waypoint: str) -> dict:
        if waypoint not in WAYPOINTS:
            raise ValueError(f"Unknown waypoint '{waypoint}'. Valid: {sorted(WAYPOINTS)}")
        self.docked, self.pose, self.at = waypoint == "dock", WAYPOINTS[waypoint], waypoint
        return {"ok": True, "at": waypoint, "pose": self.pose, "simulated": True}


@dataclass
class Cabin:
    scenario: str = "lunar_cabin"
    link: str = "up"
    vents: dict = field(default_factory=lambda: {"vent_b": "open"})
    robot: RobotSim = field(default_factory=RobotSim)
    faults: set = field(default_factory=set)
    readings: dict = field(default_factory=dict)

    def __post_init__(self):
        self.readings = dict(SCENARIOS[self.scenario])

    # ---- fault injection (used by the demo and tests) ----
    def inject(self, kind: str) -> dict:
        if kind == "link_loss":
            self.link = "down"
        elif kind == "smoke_vent_b":                 # real smoke near vent B; CO sensor lags
            self.faults.add(kind); self.readings["smoke_pct_per_m"] = 2.6
        elif kind == "smoke_sensor_fault":           # false alarm: smoke detector reads high, nothing burning
            self.faults.add(kind); self.readings["smoke_pct_per_m"] = 2.6
        else:
            raise ValueError("kind must be link_loss, smoke_vent_b or smoke_sensor_fault")
        return {"ok": True, "injected": kind}

    def restore_link(self) -> None:
        self.link = "up"

    def read(self) -> dict:
        return {**self.readings, "link": self.link, "vents": dict(self.vents), "robot": {"at": self.robot.at, "docked": self.robot.docked},
                "units": {"o2_pct": "%", "pressure_kpa": "kPa", "co_ppm": "ppm", "smoke_pct_per_m": "%/m"}, "simulated": True}

    def inspect(self, target: str) -> dict:
        if self.robot.at != target:
            raise ValueError(f"Robot is at '{self.robot.at}', not '{target}'. Call robot_goto first.")
        smoke = "smoke_vent_b" in self.faults
        return {"target": target, "visual_smoke": smoke, "surface_temp_c": 61.0 if smoke else 24.0,
                "finding": "smoke source confirmed" if smoke else "no smoke at source; detector likely faulty", "simulated": True}

    def act(self, action: str) -> dict:
        if action == "close_vent_b":
            self.vents["vent_b"] = "closed"
            if "smoke_vent_b" in self.faults:
                self.readings["smoke_pct_per_m"] = 0.3
        elif action == "open_vent_b":
            self.vents["vent_b"] = "open"
        else:
            raise ValueError("Unknown cabin action. Valid: close_vent_b, open_vent_b")
        return {"ok": True, "action": action, "state": self.read()}
