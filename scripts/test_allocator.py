import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from swarm.task_allocator import choose_uav
uavs_path = BASE_DIR / "config" / "uavs.json"
mission_path = BASE_DIR / "config" / "mission.json"

with open(uavs_path, "r") as f:
    uavs = json.load(f)

with open(mission_path, "r") as f:
    mission_points = json.load(f)

mission_point = mission_points[0]

selected_uav = choose_uav(uavs, mission_point)

print("\n=== TASK ALLOCATION TEST ===")
print(f"Mission Point: {mission_point['id']}")
print(f"Priority: {mission_point['priority']}")

if selected_uav:
    print(f"Selected UAV: {selected_uav['id']}")
    print(f"Battery: {selected_uav['battery']}%")
    print(f"Role: {selected_uav['role']}")
else:
    print("No suitable UAV available.")