import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from swarm.mission_manager import assign_mission
from swarm.failure_manager import fail_link
from communication.network_graph import build_graph, is_connected_to_gcs
from communication.recovery import recover_network


# Load project data
with open(BASE_DIR / "config" / "uavs.json", "r") as f:
    uavs = json.load(f)

with open(BASE_DIR / "config" / "mission.json", "r") as f:
    mission_points = json.load(f)

with open(BASE_DIR / "config" / "links.json", "r") as f:
    links = json.load(f)


print("\n=== UAV-X INTEGRATION DEMO ===")


# 1. Assign first mission point
mission_point = mission_points[0]

assigned_uav = assign_mission(uavs, mission_point)

if assigned_uav:
    print(
        f"[MISSION] {mission_point['id']} assigned to {assigned_uav['id']}"
    )
else:
    print("[MISSION] No suitable UAV available")


# 2. Check network before failure
graph = build_graph(links)

print("\n[NETWORK] Connectivity before failure:")

for uav in uavs:
    connected = is_connected_to_gcs(graph, uav["id"])
    print(f"{uav['id']} -> GCS: {connected}")


# 3. Simulate communication link failure
failed_link = fail_link(links, "UAV1", "UAV2")

if failed_link:
    print(
        f"\n[FAILURE] Link failed: "
        f"{failed_link['from']} -> {failed_link['to']}"
    )


# 4. Rebuild graph after failure
graph = build_graph(links)

disconnected_uavs = []

for uav in uavs:
    if not is_connected_to_gcs(graph, uav["id"]):
        disconnected_uavs.append(uav["id"])

print("\n[NETWORK] Disconnected UAVs:", disconnected_uavs)


# 5. Trigger relay recovery
recovery_uav = recover_network(uavs, disconnected_uavs)

if recovery_uav:
    print(
        f"[RECOVERY] {recovery_uav['id']} "
        f"reassigned as {recovery_uav['role']}"
    )
else:
    print("[RECOVERY] No suitable relay UAV available")


# 6. Show final state
print("\n=== FINAL UAV STATES ===")

for uav in uavs:
    current_mission = uav.get("current_mission", "NONE")

    print(
        f"{uav['id']} | "
        f"Role: {uav['role']} | "
        f"Status: {uav['status']} | "
        f"Battery: {uav['battery']}% | "
        f"Mission: {current_mission}"
    )