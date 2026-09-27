import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

uavs_path = BASE_DIR / "config" / "uavs.json"
mission_path = BASE_DIR / "config" / "mission.json"
links_path = BASE_DIR / "config" / "links.json"

with open(uavs_path, "r") as f:
    uavs = json.load(f)

with open(mission_path, "r") as f:
    mission = json.load(f)

with open(links_path, "r") as f:
    links = json.load(f)

print("\n=== UAV STATES ===")
for uav in uavs:
    print(
        f"{uav['id']} | "
        f"Role: {uav['role']} | "
        f"Battery: {uav['battery']}% | "
        f"Status: {uav['status']} | "
        f"Position: {uav['position']}"
    )

print("\n=== MISSION POINTS ===")

if isinstance(mission, dict):
    mission_points = mission.get("pois", [])
else:
    mission_points = mission

for point in mission_points:
    print(
        f"{point['id']} | "
        f"Priority: {point.get('priority', 'N/A')} | "
        f"Status: {point.get('status', 'N/A')} | "
        f"Position: {point.get('position', [])}"
    )

print("\n=== COMMUNICATION LINKS ===")
for link in links:
    print(
        f"{link['from']} -> {link['to']} | "
        f"Connected: {link['connected']} | "
        f"Quality: {link['quality']}"
    )