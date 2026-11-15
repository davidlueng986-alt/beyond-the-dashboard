"""Bridge from the crew member to NASA's Astrobee free-flyer, through the Astrobee ROS/Gazebo simulator.

Status: written for the hackathon, NOT yet run against the simulator. The demo uses RobotSim.
Select it with CABIN_AI_ROBOT=astrobee; everything else (agent, gate, event log, MCP tools) is unchanged,
because AstrobeeROS has the same interface as cabin.RobotSim: .at, .docked, .pose, .goto(waypoint).

Target: the open-source Astrobee flight software (github.com/nasa/astrobee), ROS 1 Noetic, simulator started with
    roslaunch astrobee sim.launch dds:=false robot:=sim_pub rviz:=true
Interfaces used (the same ones the `teleop` tool uses):
    actionlib  /mob/motion   ff_msgs/MotionAction  command MOVE, flight_mode "nominal", one ControlState pose
    actionlib  /beh/dock     ff_msgs/DockAction    DOCK / UNDOCK, berth 1
    topic      /loc/pose     geometry_msgs/PoseStamped   localisation estimate
    topic      camera topic (CABIN_AI_ASTROBEE_CAMERA, default /hw/cam_nav) for an inspection frame

The lunar cabin does not exist in the simulator, so cabin waypoints are mapped onto poses inside the ISS
Japanese Experiment Module (JEM). The default poses below are placeholders: check them against your map before
flying, or pass your own file with CABIN_AI_ASTROBEE_WAYPOINTS=/path/waypoints.json
({"vent_b": [x, y, z, qx, qy, qz, qw], ...}).
"""
from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field

# x, y, z (m, world frame) and orientation quaternion qx, qy, qz, qw. Placeholders inside the JEM.
DEFAULT_WAYPOINTS: dict[str, tuple[float, ...]] = {
    "dock":         (9.82, -9.81, 4.29, 0.0, 0.0, 1.0, 0.0),
    "cabin_center": (10.90, -7.50, 4.80, 0.0, 0.0, 0.7071, 0.7071),
    "vent_b":       (10.95, -5.20, 4.80, 0.0, 0.0, 0.7071, 0.7071),
}
APPROACH_TOLERANCE_M = 0.25


def load_waypoints(path: str | None = None) -> dict[str, tuple[float, ...]]:
    path = path or os.environ.get("CABIN_AI_ASTROBEE_WAYPOINTS")
    if not path:
        return dict(DEFAULT_WAYPOINTS)
    with open(path) as f:
        raw = json.load(f)
    out = {}
    for name, v in raw.items():
        if len(v) != 7:
            raise ValueError(f"waypoint '{name}' needs 7 numbers: x y z qx qy qz qw")
        out[name] = tuple(float(x) for x in v)
    missing = set(DEFAULT_WAYPOINTS) - set(out)
    if missing:
        raise ValueError(f"waypoint file is missing {sorted(missing)}")
    return out


def _ros():
    """Import ROS lazily so the rest of cabin_ai (and the tests) run without a ROS install."""
    try:
        import actionlib  # type: ignore
        import rospy  # type: ignore
        from ff_msgs.msg import ControlState, DockAction, DockGoal, MotionAction, MotionGoal  # type: ignore
        from geometry_msgs.msg import PoseStamped  # type: ignore
    except ImportError as e:  # pragma: no cover - depends on the machine
        raise RuntimeError(
            "AstrobeeROS needs a sourced Astrobee workspace (rospy, actionlib, ff_msgs). "
            "Source astrobee/devel/setup.bash, or use the default simulated robot (unset CABIN_AI_ROBOT)."
        ) from e
    return rospy, actionlib, MotionAction, MotionGoal, ControlState, DockAction, DockGoal, PoseStamped


@dataclass
class AstrobeeROS:
    """Drop-in replacement for cabin.RobotSim that flies Astrobee in the Gazebo simulator."""
    waypoints: dict = field(default_factory=load_waypoints)
    move_timeout_s: float = float(os.environ.get("CABIN_AI_ASTROBEE_TIMEOUT", "120"))
    camera_topic: str = os.environ.get("CABIN_AI_ASTROBEE_CAMERA", "/hw/cam_nav")
    at: str = "dock"
    docked: bool = True
    pose: tuple = ()

    def __post_init__(self):
        (self._rospy, actionlib, MotionAction, self._MotionGoal, self._ControlState,
         DockAction, self._DockGoal, PoseStamped) = _ros()
        if not self._rospy.core.is_initialized():
            self._rospy.init_node("cabin_ai_crew", anonymous=True, disable_signals=True)
        self._motion = actionlib.SimpleActionClient("/mob/motion", MotionAction)
        self._dock = actionlib.SimpleActionClient("/beh/dock", DockAction)
        for name, client in (("/mob/motion", self._motion), ("/beh/dock", self._dock)):
            if not client.wait_for_server(self._rospy.Duration(15)):
                raise RuntimeError(f"Astrobee action server {name} not available. Is the simulator running?")
        self._last_pose = None
        self._rospy.Subscriber("/loc/pose", PoseStamped, self._on_pose, queue_size=1)
        self.pose = self.waypoints["dock"][:3]

    # ---- localisation ----
    def _on_pose(self, msg) -> None:
        p = msg.pose.position
        self._last_pose = (p.x, p.y, p.z)

    def _distance_to(self, target: tuple) -> float | None:
        if self._last_pose is None:
            return None
        return math.dist(self._last_pose, target[:3])

    # ---- docking ----
    def _dock_cmd(self, command: int) -> bool:
        goal = self._DockGoal()
        goal.command = command
        goal.berth = self._DockGoal.BERTH_1
        self._dock.send_goal(goal)
        if not self._dock.wait_for_result(self._rospy.Duration(self.move_timeout_s)):
            self._dock.cancel_goal()
            return False
        res = self._dock.get_result()
        return res is not None and getattr(res, "response", 1) > 0

    # ---- motion ----
    def _move_to(self, wp: tuple) -> bool:
        goal = self._MotionGoal()
        goal.command = self._MotionGoal.MOVE
        goal.flight_mode = "nominal"
        state = self._ControlState()
        state.pose.position.x, state.pose.position.y, state.pose.position.z = wp[:3]
        (state.pose.orientation.x, state.pose.orientation.y,
         state.pose.orientation.z, state.pose.orientation.w) = wp[3:]
        goal.states = [state]
        self._motion.send_goal(goal)
        if not self._motion.wait_for_result(self._rospy.Duration(self.move_timeout_s)):
            self._motion.cancel_goal()
            return False
        res = self._motion.get_result()
        return res is not None and getattr(res, "response", 1) > 0

    def goto(self, waypoint: str) -> dict:
        """Same contract as RobotSim.goto. Undocks if needed, flies to the waypoint, docks if it is 'dock'."""
        if waypoint not in self.waypoints:
            raise ValueError(f"Unknown waypoint '{waypoint}'. Valid: {sorted(self.waypoints)}")
        t0 = time.monotonic()
        steps = []
        if self.docked and waypoint != "dock":
            ok = self._dock_cmd(self._DockGoal.UNDOCK); steps.append(("undock", ok))
            if not ok:
                return self._result(waypoint, False, steps, t0, "undock failed")
            self.docked = False
        if waypoint == "dock":
            ok = self._dock_cmd(self._DockGoal.DOCK); steps.append(("dock", ok))
        else:
            ok = self._move_to(self.waypoints[waypoint]); steps.append(("move", ok))
        dist = self._distance_to(self.waypoints[waypoint])
        if ok and dist is not None and dist > APPROACH_TOLERANCE_M:
            ok = False
        if ok:
            self.at, self.docked = waypoint, waypoint == "dock"
            self.pose = self._last_pose or self.waypoints[waypoint][:3]
        return self._result(waypoint, ok, steps, t0, None if ok else "motion did not reach the waypoint", dist)

    def capture(self) -> dict:
        """Grab one frame from the inspection camera. Image analysis (smoke detection) is not implemented yet."""
        try:
            msg = self._rospy.wait_for_message(self.camera_topic, self._rospy.AnyMsg, timeout=5)
            return {"ok": True, "topic": self.camera_topic, "bytes": len(msg._buff), "at": self.at, "simulated": True}
        except Exception as e:  # pragma: no cover
            return {"ok": False, "topic": self.camera_topic, "error": str(e), "simulated": True}

    def _result(self, waypoint, ok, steps, t0, error=None, dist=None) -> dict:
        r = {"ok": ok, "at": self.at, "target": waypoint, "pose": self.pose, "steps": steps,
             "seconds": round(time.monotonic() - t0, 1), "backend": "astrobee-gazebo",
             # Gazebo is still a simulator: keep the flag so nothing downstream mistakes this for hardware.
             "simulated": True}
        if dist is not None:
            r["distance_to_target_m"] = round(dist, 3)
        if error:
            r["error"] = error
        return r


def make_robot():
    """Robot backend chosen by CABIN_AI_ROBOT: 'sim' (default, the in-process RobotSim) or 'astrobee'."""
    kind = os.environ.get("CABIN_AI_ROBOT", "sim").lower()
    if kind == "astrobee":
        return AstrobeeROS()
    if kind != "sim":
        raise ValueError("CABIN_AI_ROBOT must be 'sim' or 'astrobee'")
    from .cabin import RobotSim
    return RobotSim()
