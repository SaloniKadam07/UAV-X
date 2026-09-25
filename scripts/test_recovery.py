import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from communication.network_graph import build_graph, is_connected_to_gcs
from communication.recovery import recover_network

uavs_path = BASE_DIR / "config" / "uavs.json"
links_path = BASE_DIR / "config" / "links.json"

with open(uavs_path, "r") as f:
    uavs = json.load(f)

with open(links_path, "r") as f:
    links = json.load(f)

graph = build_graph(links)

disconnected_uavs = []

for uav in uavs:
    if not is_connected_to_gcs(graph, uav["id"]):
        disconnected_uavs.append(uav["id"])

print("\n=== AUTOMATIC RELAY RECOVERY TEST ===")
print("Disconnected UAVs:", disconnected_uavs)

recovered_uav = recover_network(uavs, disconnected_uavs)

if recovered_uav:
    print(f"Recovery UAV: {recovered_uav['id']}")
    print(f"New Role: {recovered_uav['role']}")
else:
    print("Recovery failed: no suitable relay candidate.")