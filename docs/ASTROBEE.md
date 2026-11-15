# Astrobee bridge (written, not yet run)

`server/cabin_ai/astrobee.py` lets the AI crew member fly NASA's Astrobee free-flyer in the official
Astrobee ROS/Gazebo simulator instead of the in-process `RobotSim`. It has the same interface, so the agent,
decision gate, event log and MCP tools do not change. It was written during the hackathon and has not been
run against the simulator yet; the demo video uses `RobotSim`.

## Try it

1. Build the Astrobee flight software and simulator (github.com/nasa/astrobee, ROS 1 Noetic) and start it:
   `roslaunch astrobee sim.launch dds:=false robot:=sim_pub rviz:=true`
2. In a second shell, source the Astrobee workspace, install this package, and run the agent with the bridge:
   ```bash
   source ~/astrobee/devel/setup.bash
   cd server && pip install -e .
   CABIN_AI_ROBOT=astrobee python -m cabin_ai.agent --scripted --scenario smoke_vent_b
   ```

## How it maps

| Crew member call | Astrobee interface |
| --- | --- |
| `robot_goto("vent_b")` from the dock | `/beh/dock` UNDOCK, then `/mob/motion` MOVE (flight mode `nominal`) to the vent_b pose |
| `robot_goto("dock")` | `/beh/dock` DOCK, berth 1 |
| arrival check | `/loc/pose` must be within 0.25 m of the target |
| `capture()` | one frame from `CABIN_AI_ASTROBEE_CAMERA` (default `/hw/cam_nav`) |

The lunar cabin does not exist in the simulator, so cabin waypoints are mapped to poses inside the ISS
Japanese Experiment Module. The defaults are placeholders; supply checked poses with
`CABIN_AI_ASTROBEE_WAYPOINTS=waypoints.json` (`{"dock": [x, y, z, qx, qy, qz, qw], "cabin_center": [...], "vent_b": [...]}`).

## Not done yet

- Smoke detection from camera frames (the cabin's inspection result is still simulated).
- Running it end to end against the simulator, and choosing verified JEM poses.
- ROS 2 port, if the Astrobee ROS 2 branch is the target.
