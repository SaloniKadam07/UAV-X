import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from swarm.mission_manager import assign_mission

uavs_path = BASE_DIR / "config" / "uavs.json"
mission_path = BASE_DIR / "config" / "mission.json"

with open(uavs_path, "r") as f:
    uavs = json.load(f)

with open(mission_path, "r") as f:
    mission_points = json.load(f)

mission_point = mission_points[0]

print("\n=== MISSION MANAGER TEST ===")
print(f"Before: {mission_point['id']} status = {mission_point['status']}")

assigned_uav = assign_mission(uavs, mission_point)

if assigned_uav:
    print(f"Assigned UAV: {assigned_uav['id']}")
    print(f"Current Mission: {assigned_uav['current_mission']}")
    print(f"After: {mission_point['id']} status = {mission_point['status']}")
else:
    print("No UAV available for assignment.")